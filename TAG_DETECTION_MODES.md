# LLRP Tag Detection Modes

## Overview

The RaceTiming system supports three different tag detection modes for LLRP RFID timing points. Each mode processes tag reads differently to determine the most accurate timestamp for a participant crossing a timing point.

## Detection Modes

### 1. First Seen Tag (Default)
**Mode:** `first_seen`

**Description:** Records the timestamp of the first time a tag is detected within the cooldown window.

**Use Cases:**
- Start lines where you want to capture the exact moment a participant begins
- Situations where the first detection is most accurate
- High-speed passages where participants move quickly through the read zone

**Advantages:**
- Immediate response - no buffering delay
- Simple and predictable
- Lowest latency

**Disadvantages:**
- May capture early/premature reads if tag is detected before actual crossing
- Sensitive to read zone configuration

### 2. Last Seen Tag
**Mode:** `last_seen`

**Description:** Buffers tag reads for a configurable time window and uses the timestamp of the last detection.

**Use Cases:**
- Finish lines where you want the final crossing time
- Situations where participants may slow down or stop near the timing point
- Areas where tags might be read after the actual crossing

**Advantages:**
- Captures the final moment of passage
- Good for finish lines and checkpoints where participants may linger
- Reduces false early detections

**Disadvantages:**
- Introduces delay equal to the detection window
- May miss the actual crossing if participant moves through quickly

### 3. Peak RSSI (Quadratic Regression)
**Mode:** `peak_rssi`

**Description:** Buffers tag reads and uses quadratic regression to calculate when the signal strength (RSSI) was at its peak, indicating the tag was closest to the antenna.

**Use Cases:**
- High-precision timing requirements
- Situations where participants pass through at varying speeds
- Timing mats or gates where the strongest signal indicates the exact crossing point
- Professional races requiring maximum accuracy

**Advantages:**
- Most accurate representation of when tag was closest to antenna
- Compensates for varying participant speeds
- Mathematically determines the optimal timestamp
- Works well with participants who slow down or speed up through the zone

**Disadvantages:**
- Requires multiple reads for accuracy (minimum 3)
- Introduces delay equal to the detection window
- More computationally intensive
- Requires good RSSI data from the reader

**How It Works:**
1. Collects all tag reads within the detection window
2. Fits a quadratic polynomial to the RSSI values over time
3. Calculates the vertex (peak) of the parabola
4. Uses the timestamp at the peak RSSI as the crossing time

## Configuration Guide

### Setting Detection Mode for a Timing Point

```python
from race_manager import RaceManager
from models import TagDetectionMode

race_manager = RaceManager()

timing_point = race_manager.add_timing_point(
    race_id=1,
    name="Finish Line",
    order=3,
    is_finish=True,
    llrp_station_id=1,
    detection_mode="peak_rssi",
    detection_window_seconds=3
)
```

### Detection Window Recommendations

| Scenario | Window | Mode |
|----------|--------|------|
| Sprint Start | N/A | first_seen |
| Marathon Start | N/A | first_seen |
| Mid-race Checkpoint | 2-3s | peak_rssi |
| Finish Line (Fast) | 2-3s | peak_rssi |
| Finish Line (Slow) | 3-5s | last_seen |
| Transition Entry | 2-3s | first_seen |
| Transition Exit | 2-3s | last_seen |

## Implementation Details

The system uses a `TagDetectionManager` that coordinates detection across multiple timing points with different modes. Each timing point has its own buffer and processes reads independently.

For more technical details, see `tag_detection.py`.