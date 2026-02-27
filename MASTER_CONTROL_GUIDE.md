# Master Event Timing Control Guide

## Overview

The Master Event Timing Control is a unified interface for managing all races within an event from a single dashboard. It provides comprehensive control over race timing, manual time recording, and real-time monitoring of all checkpoint reads across multiple races.

## Accessing Master Control

### From Events Page
1. Navigate to **Events** in the main menu
2. Find your event in the list
3. Click the **🎛️ Master Control** button

### From Event Control Page
1. Navigate to your event's control page
2. Click the **🎛️ Master Control** button in the header

### Direct URL
Access directly via: `/event/{event_id}/master-control`

## Features

### 1. Quick Actions

Located at the top of the page for rapid event management:

- **▶️ Start All Races**: Simultaneously start all races in the event that haven't started yet
- **⏹️ Stop All Races**: Stop all currently active races
- **🔄 Refresh All**: Manually refresh all data (auto-refreshes every 3 seconds)

### 2. Unified Manual Timing

Record times for any participant in any race from a single form. **Bib numbers are assumed to be unique within each race**, allowing for rapid sequential entry.

**Fields:**
- **Race**: Select which race to record time for (stays selected for multiple entries)
- **Bib #**: Enter the participant's bib number (auto-focused after each entry)
- **Timing Point**: Select the checkpoint (auto-populated based on selected race)
- **Time**: Optional - leave blank to use current time, or specify a custom time

**Keyboard Shortcut:**
- Press `Ctrl+Enter` (or `Cmd+Enter` on Mac) to quickly record the time

**Optimized Workflow:**
1. Select the race from the dropdown (do this once)
2. The form will show: "📍 Timing for: [Race Name] (Bibs are unique within this race)"
3. Enter bib number (cursor auto-focuses here)
4. Select timing point if needed
5. Click **✓ Record Time** or press Ctrl+Enter
6. Bib field clears and auto-focuses for next entry
7. Race and timing point remain selected for rapid sequential timing

**Quick Entry Tips:**
- Select race once at the start of a wave
- Use Tab key to move between fields
- Press Ctrl+Enter to record without clicking
- Bib field auto-clears and refocuses after each entry
- Race selection persists for multiple participants

### 3. Race Control Cards

Each race displays a control card with:

**Status Indicators:**
- **Not Started** (Gray badge): Race hasn't begun
- **Active** (Green badge, pulsing): Race is currently running
- **Finished** (Blue badge): Race has completed

**Statistics:**
- **Total**: Number of registered participants
- **Started**: Participants who have started
- **Finished**: Participants who have finished

**Control Buttons:**
- **▶️ Start**: Start the race (only shown if not started)
- **⏹️ Stop**: Stop the race (only shown if active)
- **✏️ Edit Start**: Modify the race start time
- **🔄 Reset**: Clear all times and results (requires confirmation)
- **🎛️ Control**: Navigate to individual race control page

### 4. Live Checkpoint Reads

Real-time display of all timing events across all races:

**Features:**
- Shows last 100 reads across all races
- Auto-scrolls to new reads (can be disabled)
- Color-coded by source:
  - **LLRP** (Blue): Automatic RFID reads
  - **MANUAL** (Orange): Manually recorded times
- Race badge shows which race the read belongs to

**Read Information:**
- Race name badge
- Bib number and participant name
- Timing point name
- Exact time of read
- Source (LLRP or MANUAL)
- Edit button (✏️) for time corrections

**Controls:**
- **Auto-scroll checkbox**: Enable/disable automatic scrolling to new reads
- **Clear button**: Clear the display (doesn't delete data)

### 5. Time Editing

Click the **✏️** button on any read to edit:

**Edit Modal Features:**
- View participant and timing point (read-only)
- Modify the timestamp
- **Save**: Update the time record
- **Delete**: Remove the time record entirely
- **Cancel**: Close without changes

**Use Cases:**
- Correct timing errors
- Adjust for clock synchronization issues
- Remove duplicate or erroneous reads

## Best Practices

### Event Setup
1. Create your event and all races
2. Configure timing points for each race
3. Register participants and assign bib numbers
4. Test LLRP stations if using automatic timing

### During Event
1. Open Master Control before event starts
2. Use **Start All Races** if all races begin simultaneously
3. Monitor the live reads panel for activity
4. Use unified manual timing for backup or manual checkpoints
5. Edit times immediately if you notice errors

### Race Management
- **Individual Starts**: Use individual race Start buttons for staggered starts
- **Edit Start Times**: Adjust if races started early/late
- **Stop Races**: Mark races as finished when complete
- **Reset Carefully**: Only reset if you need to completely restart a race

### Manual Timing Tips
1. Pre-select the race at the start of each wave
2. Keep focus on the Bib # field
3. Use Tab to move between fields quickly
4. Press Ctrl+Enter to record without clicking
5. Timing point auto-advances to next expected checkpoint

### Monitoring
- Keep Auto-scroll enabled to see new reads immediately
- Watch for unexpected timing point sequences
- Verify LLRP vs MANUAL source distribution
- Check race statistics regularly

## Troubleshooting

### Times Not Recording
- Verify the race has been started
- Check that timing points are configured
- Ensure participant is registered with correct bib number
- Verify LLRP stations are connected (if using automatic timing)

### Wrong Timing Point
- Use the edit feature (✏️) to modify the time record
- Delete and re-record if necessary
- Check timing point configuration in race setup

### Missing Reads
- Check LLRP station status
- Verify tag assignment to participants
- Use manual timing as backup
- Review all reads panel for any recorded times

### Race Won't Start
- Ensure race has timing points configured
- Check that race isn't already started
- Verify race belongs to the event
- Check browser console for errors

## Technical Details

### Auto-Refresh
- Data refreshes every 3 seconds automatically
- Includes race status, statistics, and reads
- Can be manually triggered with Refresh All button

### Data Limits
- Displays last 100 reads in the live panel
- All data is preserved in database
- Use individual race control for complete history

### Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- JavaScript must be enabled
- Responsive design for tablets and desktops

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` / `Cmd+Enter` | Record manual time |
| `Esc` | Close edit modal |

## Related Features

- **Individual Race Control**: Detailed control for single race
- **Event Control**: Standard event overview
- **Race Results**: View leaderboards and final results
- **LLRP Stations**: Configure automatic timing hardware

## API Endpoints Used

The Master Control interface uses these API endpoints:

- `GET /api/events/{event_id}` - Event details
- `GET /api/races` - All races
- `GET /api/races/{race_id}` - Race details
- `GET /api/races/{race_id}/results` - Race results
- `GET /api/races/{race_id}/time-records` - Timing records
- `POST /api/races/{race_id}/start` - Start race
- `POST /api/races/{race_id}/stop` - Stop race
- `POST /api/races/{race_id}/reset` - Reset race
- `POST /api/races/{race_id}/control/time` - Record manual time
- `PUT /api/races/{race_id}/start-time` - Edit start time
- `PUT /api/time-records/{record_id}` - Edit time record
- `DELETE /api/time-records/{record_id}` - Delete time record

## Security Considerations

- Master Control provides full event management capabilities
- All actions are immediate and affect live race data
- Reset operations cannot be undone
- Time edits are logged but previous values are not preserved
- Ensure only authorized personnel have access

## Support

For issues or questions:
1. Check this guide first
2. Review the main README.md
3. Check browser console for errors
4. Verify API endpoints are responding
5. Test with a single race first

---

**Version**: 1.0  
**Last Updated**: 2026-02-26  
**Related Documentation**: README.md, TAG_DETECTION_MODES.md, CONFIGURATION_GUIDE.md