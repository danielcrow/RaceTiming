"""
LLRP Reader Service - Refactored for Web Control
This module provides a class-based RFID reader that can be controlled programmatically.
"""

import time
import json
import requests
from datetime import datetime
import threading
import random

try:
    from pyllrp.LLRPConnector import LLRPConnector
    from pyllrp.TagInventory import TagInventory
    from pyllrp.pyllrp import *
    PYLLRP_AVAILABLE = True
except ImportError:
    PYLLRP_AVAILABLE = False
    print("Warning: pyllrp not properly installed. Running in simulation mode.")


class RFIDReaderService:
    """
    RFID Reader Service that can be controlled programmatically.
    Supports callbacks for tag events and status updates.
    """
    
    def __init__(self, config):
        """
        Initialize the RFID reader service.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.config = config
        self.station_id = config.get('station_id')
        self.station_name = config.get('station_name', 'Unknown Station')
        self.running = False
        self.connector = None
        self.tag_inventory = None
        self.thread = None
        self.tag_last_read = {}
        self.tag_callback = None
        self.status_callback = None
        
    def set_tag_callback(self, callback):
        """Set callback function for tag events."""
        self.tag_callback = callback
        
    def set_status_callback(self, callback):
        """Set callback function for status updates."""
        self.status_callback = callback
        
    def _emit_status(self, message, level="info"):
        """Emit a status message."""
        if self.status_callback:
            self.status_callback(message, level, self.station_id)
        print(f"[{level.upper()}] {message}")
        
    def _tag_read_handler(self, epc, rssi, timestamp):
        print("entering tag read handler")
        """Internal handler for tag reads"""
        # Check cooldown
        last_read = self.tag_last_read.get(epc, 0)
        print(epc)
        print(time.time() - last_read, self.config.get('cooldown_seconds', 5))
        #if time.time() - last_read < self.config.get('cooldown_seconds', 5):
        #   return
            
        #self.tag_last_read[epc] = time.time()
        
        print("what is in here", self.tag_callback)
        # Call the registered callback
        if self.tag_callback:
            # Pass station_id if available, otherwise None
            print(epc)
            self.tag_callback(epc, rssi, timestamp, self.station_id)
    
    def _tag_report_handler(self, conn, message):
        """
        Handler for RO_ACCESS_REPORT messages from the LLRP reader.
        This is called automatically when tags are detected.
        """
        try:
            # The message object has a Parameters list containing TagReportData_Parameter objects
            if not hasattr(message, 'Parameters') or not message.Parameters:
                return
            
            # Iterate through all parameters in the message
            for param in message.Parameters:
                # Check if this is a TagReportData_Parameter
                if param.__class__.__name__ == 'TagReportData_Parameter':
                    # Extract EPC
                    epc = None
                    rssi = -50  # Default value
                    
                    # Look through the tag report's parameters for EPC and RSSI
                    if hasattr(param, 'Parameters') and param.Parameters:
                        for tag_param in param.Parameters:
                            # Extract EPC
                            if tag_param.__class__.__name__ in ['EPC_96_Parameter', 'EPCData_Parameter']:
                                if hasattr(tag_param, 'EPC'):
                                    # EPC can be either an integer or bytes
                                    epc_data = tag_param.EPC
                                    if isinstance(epc_data, int):
                                        # Convert integer to hex string (96 bits = 24 hex chars)
                                        epc = format(epc_data, '024X')
                                    elif isinstance(epc_data, bytes):
                                        epc = epc_data.hex().upper()
                                    else:
                                        # Try to convert to hex string
                                        epc = str(epc_data).upper()
                            
                            # Extract RSSI
                            elif tag_param.__class__.__name__ == 'PeakRSSI_Parameter':
                                if hasattr(tag_param, 'PeakRSSI'):
                                    rssi = tag_param.PeakRSSI
                    
                    # Process the tag if we got an EPC
                    if epc:
                        current_time = time.time()
                        
                        # Check if this tag was read recently (cooldown)
                        if epc in self.tag_last_read:
                            time_since_last_read = current_time - self.tag_last_read[epc]
                            if time_since_last_read < self.config['cooldown_seconds']:
                                continue
                        
                        # Process the tag
                        self.tag_last_read[epc] = current_time
                        self._emit_status(f"Tag detected - EPC: {epc}, RSSI: {rssi}", "info")
                        self._tag_read_handler(epc, rssi, current_time)
                        
        except Exception as e:
            self._emit_status(f"Error in tag report handler: {str(e)}", "error")
    
    def _setup_rospec(self):
        """
        Set up the ROSpec (Reader Operation Specification) for tag inventory.
        Returns True if successful, False otherwise.
        """
        try:
            rospec_id = 123
            inventory_param_spec_id = 1234
            
            # Delete any existing ROSpec with this ID
            response = self.connector.transact(DELETE_ROSPEC_Message(ROSpecID=rospec_id))
            
            # Create and add new ROSpec
            response = self.connector.transact(
                ADD_ROSPEC_Message(Parameters=[
                    ROSpec_Parameter(
                        ROSpecID=rospec_id,
                        CurrentState=ROSpecState.Disabled,
                        Parameters=[
                            ROBoundarySpec_Parameter(
                                Parameters=[
                                    ROSpecStartTrigger_Parameter(
                                        ROSpecStartTriggerType=ROSpecStartTriggerType.Immediate
                                    ),
                                    ROSpecStopTrigger_Parameter(
                                        ROSpecStopTriggerType=ROSpecStopTriggerType.Null
                                    ),
                                ]
                            ),
                            AISpec_Parameter(
                                AntennaIDs=[0],  # Use all antennas
                                Parameters=[
                                    AISpecStopTrigger_Parameter(
                                        AISpecStopTriggerType=AISpecStopTriggerType.Null
                                    ),
                                    InventoryParameterSpec_Parameter(
                                        InventoryParameterSpecID=inventory_param_spec_id,
                                        ProtocolID=AirProtocols.EPCGlobalClass1Gen2,
                                    ),
                                ]
                            ),
                            ROReportSpec_Parameter(
                                ROReportTrigger=ROReportTriggerType.Upon_N_Tags_Or_End_Of_ROSpec,
                                N=1,  # Report immediately on each tag read
                                Parameters=[
                                    TagReportContentSelector_Parameter(
                                        EnableAntennaID=True,
                                        EnableFirstSeenTimestamp=True,
                                        EnablePeakRSSI=True,
                                    ),
                                ]
                            ),
                        ]
                    ),
                ])
            )
            
            if not response.success():
                self._emit_status("Failed to add ROSpec", "error")
                return False
            
            # Enable the ROSpec
            response = self.connector.transact(ENABLE_ROSPEC_Message(ROSpecID=rospec_id))
            if not response.success():
                self._emit_status("Failed to enable ROSpec", "error")
                return False
            
            return True
            
        except Exception as e:
            self._emit_status(f"Error setting up ROSpec: {str(e)}", "error")
            return False
    
    def _reader_loop_real(self):
        """Main reader loop using real pyllrp library with startListener."""
        try:
            self._emit_status(f"Connecting to LLRP reader at {self.config['reader_ip']}:{self.config['reader_port']}...")
            
            # Create connector and connect to reader
            self.connector = LLRPConnector()
            self.connector.connect(self.config['reader_ip'])
            self._emit_status("Connected successfully!", "success")
            
            # Set up ROSpec for tag inventory
            self._emit_status("Setting up tag inventory ROSpec...")
            if not self._setup_rospec():
                raise Exception("Failed to set up ROSpec")
            
            # Add tag report handler
            self.connector.addHandler(RO_ACCESS_REPORT_Message, self._tag_report_handler)
            
            # Start listener
            self._emit_status("Starting tag inventory listener...", "success")
            self.connector.startListener()
            
            # Keep running until stopped
            while self.running:
                time.sleep(0.1)
        
        except Exception as e:
            self._emit_status(f"Error: {str(e)}", "error")
            
        finally:
            # Stop listener
            if self.connector:
                try:
                    self.connector.stopListener()
                    self._emit_status("Stopped listener.", "info")
                except:
                    pass
            
            # Disconnect from reader
            if self.connector:
                try:
                    self.connector.disconnect()
                    self._emit_status("Disconnected from reader.", "info")
                except:
                    pass
            
            self.running = False
    
    def _reader_loop_simulation(self):
        """Simulated reader loop for testing without hardware."""
        try:
            self._emit_status(f"[SIMULATION MODE] Simulating LLRP reader at {self.config['reader_ip']}:{self.config['reader_port']}...", "warning")
            self._emit_status("Connected successfully! (Simulation)", "success")
            self._emit_status("Starting tag inventory... (Simulation)", "info")
            
            # Simulate some tag EPCs
            simulated_tags = [
                "E2801170000002018835B6F4",
                "E2801170000002018835B6F5",
                "E2801170000002018835B6F6",
                "E2801170000002018835B6F7",
            ]
            
            while self.running:
                try:
                    # Randomly detect a tag every 2-5 seconds
                    time.sleep(random.uniform(2, 5))
                    
                    if not self.running:
                        break
                    
                    # Pick a random tag
                    epc = random.choice(simulated_tags)
                    rssi = random.randint(-60, -30)
                    current_time = time.time()
                    
                    # Check cooldown
                    if epc in self.tag_last_read:
                        time_since_last_read = current_time - self.tag_last_read[epc]
                        if time_since_last_read < self.config['cooldown_seconds']:
                            continue
                    
                    # Process the tag
                    self.tag_last_read[epc] = current_time
                    self._emit_status(f"Tag detected - EPC: {epc}, RSSI: {rssi}", "info")
                    self._tag_read_handler(epc, rssi, current_time)
                    
                except Exception as e:
                    if self.running:
                        self._emit_status(f"Error in simulation: {str(e)}", "error")
                        time.sleep(1)
        
        except KeyboardInterrupt:
            self._emit_status("Stopping simulation...", "info")
            
        except Exception as e:
            self._emit_status(f"Error: {str(e)}", "error")
            
        finally:
            self._emit_status("Disconnected from reader. (Simulation)", "info")
            self.running = False
    
    def _reader_loop(self):
        """Main reader loop - delegates to real or simulated version."""
        if PYLLRP_AVAILABLE:
            self._reader_loop_real()
        else:
            self._reader_loop_simulation()
    
    def start(self):
        """Start the RFID reader service."""
        if self.running:
            self._emit_status("Service is already running", "warning")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Stop the RFID reader service."""
        if not self.running:
            self._emit_status("Service is not running", "warning")
            return False
            
        self._emit_status("Stopping service...", "info")
        self.running = False
        
        # Wait for thread to finish (with timeout)
        if self.thread:
            self.thread.join(timeout=5)
            
        return True
    
    def is_running(self):
        """Check if the service is currently running."""
        return self.running


# Legacy main function for backward compatibility
def main():
    """
    Main function for standalone operation.
    """
    # Default configuration
    config = {
        "reader_ip": "192.168.1.100",
        "reader_port": 5084,
        "cooldown_seconds": 5
    }
    
    # Create and start service
    service = RFIDReaderService(config)
    service.start()
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        service.stop()


if __name__ == "__main__":
    main()
