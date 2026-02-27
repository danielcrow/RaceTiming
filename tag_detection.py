"""
Tag Detection Module - Implements different LLRP tag detection modes
"""
import time
from collections import defaultdict
from datetime import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable


class TagRead:
    """Represents a single tag read event"""
    def __init__(self, epc: str, rssi: float, timestamp: float):
        self.epc = epc
        self.rssi = rssi
        self.timestamp = timestamp
    
    def __repr__(self):
        return f"TagRead(epc={self.epc}, rssi={self.rssi}, timestamp={self.timestamp})"


class TagBuffer:
    """
    Buffers tag reads for a detection window to enable different detection modes.
    Manages multiple tags simultaneously with independent buffers.
    """
    
    def __init__(self, window_seconds: float = 3.0, callback: Optional[Callable] = None):
        """
        Initialize tag buffer.
        
        Args:
            window_seconds: Time window for collecting reads (seconds)
            callback: Function to call when a tag detection is finalized
                     Signature: callback(epc, timestamp, rssi, detection_mode)
        """
        self.window_seconds = window_seconds
        self.callback = callback
        
        # Buffer structure: {epc: [TagRead, TagRead, ...]}
        self.buffers: Dict[str, List[TagRead]] = defaultdict(list)
        
        # Track when each tag's window started
        self.window_start_times: Dict[str, float] = {}
        
        # Track last processed time for each tag to prevent duplicates
        self.last_processed: Dict[str, float] = {}
    
    def add_read(self, epc: str, rssi: float, timestamp: float, detection_mode: str) -> Optional[Tuple[str, float, float]]:
        """
        Add a tag read to the buffer.
        
        Args:
            epc: Tag EPC code
            rssi: Signal strength
            timestamp: Read timestamp
            detection_mode: Detection mode (first_seen, last_seen, peak_rssi)
        
        Returns:
            Tuple of (epc, final_timestamp, rssi) if detection is finalized, None otherwise
        """
        current_time = time.time()
        
        # For FIRST_SEEN mode, process immediately
        if detection_mode == "first_seen":
            # Check if we've already processed this tag recently
            if epc in self.last_processed:
                if current_time - self.last_processed[epc] < self.window_seconds:
                    return None
            
            self.last_processed[epc] = current_time
            if self.callback:
                self.callback(epc, timestamp, rssi, detection_mode)
            return (epc, timestamp, rssi)
        
        # For LAST_SEEN and PEAK_RSSI modes, buffer the reads
        tag_read = TagRead(epc, rssi, timestamp)
        
        # Initialize window if this is the first read for this tag
        if epc not in self.window_start_times:
            self.window_start_times[epc] = current_time
            self.buffers[epc] = [tag_read]
            return None
        
        # Add read to buffer
        self.buffers[epc].append(tag_read)
        
        # Check if window has expired
        if current_time - self.window_start_times[epc] >= self.window_seconds:
            return self._finalize_detection(epc, detection_mode)
        
        return None
    
    def _finalize_detection(self, epc: str, detection_mode: str) -> Optional[Tuple[str, float, float]]:
        """
        Finalize detection for a tag based on the detection mode.
        
        Args:
            epc: Tag EPC code
            detection_mode: Detection mode (last_seen or peak_rssi)
        
        Returns:
            Tuple of (epc, final_timestamp, rssi) or None
        """
        if epc not in self.buffers or not self.buffers[epc]:
            return None
        
        reads = self.buffers[epc]
        result = None
        
        if detection_mode == "last_seen":
            # Use the last read in the buffer
            last_read = max(reads, key=lambda r: r.timestamp)
            result = (epc, last_read.timestamp, last_read.rssi)
        
        elif detection_mode == "peak_rssi":
            # Use quadratic regression to find peak RSSI timestamp
            result = self._calculate_peak_rssi(epc, reads)
        
        # Clean up
        del self.buffers[epc]
        del self.window_start_times[epc]
        self.last_processed[epc] = time.time()
        
        # Call callback if provided
        if result and self.callback:
            self.callback(result[0], result[1], result[2], detection_mode)
        
        return result
    
    def _calculate_peak_rssi(self, epc: str, reads: List[TagRead]) -> Optional[Tuple[str, float, float]]:
        """
        Calculate the timestamp when RSSI was at its peak using quadratic regression.
        
        Args:
            epc: Tag EPC code
            reads: List of TagRead objects
        
        Returns:
            Tuple of (epc, peak_timestamp, peak_rssi) or None
        """
        if len(reads) < 3:
            # Not enough points for quadratic regression, use max RSSI
            max_read = max(reads, key=lambda r: r.rssi)
            return (epc, max_read.timestamp, max_read.rssi)
        
        try:
            # Extract timestamps and RSSI values
            timestamps = np.array([r.timestamp for r in reads])
            rssi_values = np.array([r.rssi for r in reads])
            
            # Normalize timestamps to start from 0 for numerical stability
            t_min = timestamps.min()
            t_normalized = timestamps - t_min
            
            # Fit quadratic polynomial: rssi = a*t^2 + b*t + c
            coefficients = np.polyfit(t_normalized, rssi_values, 2)
            a, b, c = coefficients
            
            # Find the peak (vertex of parabola)
            # For a parabola y = ax^2 + bx + c, the vertex is at x = -b/(2a)
            if a >= 0:
                # Parabola opens upward, no maximum - use actual max RSSI
                max_read = max(reads, key=lambda r: r.rssi)
                return (epc, max_read.timestamp, max_read.rssi)
            
            # Calculate peak timestamp
            t_peak_normalized = -b / (2 * a)
            t_peak = t_peak_normalized + t_min
            
            # Ensure peak is within the observed time range
            t_peak = max(timestamps.min(), min(t_peak, timestamps.max()))
            
            # Calculate RSSI at peak
            rssi_peak = a * t_peak_normalized**2 + b * t_peak_normalized + c
            
            return (epc, t_peak, rssi_peak)
        
        except Exception as e:
            # Fallback to max RSSI if regression fails
            print(f"Quadratic regression failed for {epc}: {e}")
            max_read = max(reads, key=lambda r: r.rssi)
            return (epc, max_read.timestamp, max_read.rssi)
    
    def check_expired_windows(self, detection_mode: str) -> List[Tuple[str, float, float]]:
        """
        Check for and finalize any expired detection windows.
        
        Args:
            detection_mode: Detection mode to use for finalization
        
        Returns:
            List of finalized detections as (epc, timestamp, rssi) tuples
        """
        current_time = time.time()
        expired_tags = []
        results = []
        
        # Find expired windows
        for epc, start_time in self.window_start_times.items():
            if current_time - start_time >= self.window_seconds:
                expired_tags.append(epc)
        
        # Finalize expired windows
        for epc in expired_tags:
            result = self._finalize_detection(epc, detection_mode)
            if result:
                results.append(result)
        
        return results
    
    def clear(self):
        """Clear all buffers and reset state."""
        self.buffers.clear()
        self.window_start_times.clear()
        self.last_processed.clear()


class TagDetectionManager:
    """
    Manages tag detection across multiple timing points with different detection modes.
    """
    
    def __init__(self):
        """Initialize the tag detection manager."""
        # Map timing_point_id to TagBuffer
        self.buffers: Dict[int, TagBuffer] = {}
        
        # Map timing_point_id to detection mode
        self.detection_modes: Dict[int, str] = {}
        
        # Map timing_point_id to window seconds
        self.window_seconds: Dict[int, float] = {}
    
    def configure_timing_point(self, timing_point_id: int, detection_mode: str, 
                              window_seconds: float = 3.0, callback: Optional[Callable] = None):
        """
        Configure detection settings for a timing point.
        
        Args:
            timing_point_id: ID of the timing point
            detection_mode: Detection mode (first_seen, last_seen, peak_rssi)
            window_seconds: Detection window in seconds
            callback: Callback function for finalized detections
        """
        self.detection_modes[timing_point_id] = detection_mode
        self.window_seconds[timing_point_id] = window_seconds
        self.buffers[timing_point_id] = TagBuffer(window_seconds, callback)
    
    def process_tag_read(self, timing_point_id: int, epc: str, rssi: float, 
                        timestamp: float) -> Optional[Tuple[str, float, float]]:
        """
        Process a tag read for a specific timing point.
        
        Args:
            timing_point_id: ID of the timing point
            epc: Tag EPC code
            rssi: Signal strength
            timestamp: Read timestamp
        
        Returns:
            Tuple of (epc, final_timestamp, rssi) if detection is finalized, None otherwise
        """
        if timing_point_id not in self.buffers:
            # Default configuration if not set
            self.configure_timing_point(timing_point_id, "first_seen", 3.0)
        
        detection_mode = self.detection_modes[timing_point_id]
        buffer = self.buffers[timing_point_id]
        
        return buffer.add_read(epc, rssi, timestamp, detection_mode)
    
    def check_all_expired_windows(self):
        """Check and finalize expired windows for all timing points."""
        results = []
        for timing_point_id, buffer in self.buffers.items():
            detection_mode = self.detection_modes[timing_point_id]
            expired = buffer.check_expired_windows(detection_mode)
            results.extend([(timing_point_id, *result) for result in expired])
        return results
    
    def clear_timing_point(self, timing_point_id: int):
        """Clear buffer for a specific timing point."""
        if timing_point_id in self.buffers:
            self.buffers[timing_point_id].clear()
    
    def clear_all(self):
        """Clear all buffers."""
        for buffer in self.buffers.values():
            buffer.clear()

# Made with Bob
