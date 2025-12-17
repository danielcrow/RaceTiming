# Race Timing System

A comprehensive race management and timing system for multi-sport events including Triathlon, Duathlon, Aquathlon, Running, and Cycling races.

## Features

- **Multiple Race Types**: Support for Triathlon, Duathlon, Aquathlon, Running, and Cycling
- **Participant Management**: Register and manage participants with RFID tag support
- **Dual Timing Methods**: 
  - Automatic timing via LLRP RFID readers
  - Manual time entry
- **Real-time Results**: Live race standings and rankings
- **Comprehensive Reporting**: Generate results in Text, CSV, and HTML formats
- **Database Persistence**: All data stored in SQLite database

## Installation

1. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**:
   ```bash
   python cli.py init
   ```

## Quick Start

### 1. Create a Race

```bash
python cli.py race create \
  --name "City Triathlon 2024" \
  --type triathlon \
  --date 2024-06-15 \
  --location "City Beach"
```

### 2. Create and Register Participants

```bash
# Create a participant
python cli.py participant create \
  --first-name John \
  --last-name Doe \
  --email john@example.com \
  --gender M \
  --age 35 \
  --rfid E2001234567890123456789A

# Register participant for race
python cli.py participant register \
  --race-id 1 \
  --participant-id 1 \
  --bib 101 \
  --category "Age 30-39"
```

### 3. Run Race Control

```bash
# With LLRP reader
python cli.py control start 1 --llrp-host 192.168.1.130

# Without LLRP (manual timing only)
python cli.py control start 1
```

**Race Control Commands**:
- `time <bib> <point>` - Record time (e.g., `time 101 Finish`)
- `dnf <bib>` - Mark as Did Not Finish
- `dns <bib>` - Mark as Did Not Start
- `results [n]` - Show top n results
- `quit` - Exit race control

### 4. Generate Reports

```bash
# Text report (console output)
python cli.py report text 1

# CSV export
python cli.py report csv 1 --output results.csv

# HTML report
python cli.py report html 1 --output results.html
```

## Command Reference

### Database Commands

```bash
python cli.py init                    # Initialize database
```

### Race Management

```bash
python cli.py race create             # Create new race (interactive)
python cli.py race list               # List all races
python cli.py race show <race-id>     # Show race details
```

### Participant Management

```bash
python cli.py participant create                    # Create participant (interactive)
python cli.py participant list                      # List all participants
python cli.py participant list --race-id <id>       # List participants in a race
python cli.py participant register                  # Register participant for race
python cli.py participant set-rfid                  # Assign RFID tag to participant
```

### Race Control

```bash
python cli.py control start <race-id>                          # Start race control
python cli.py control start <race-id> --llrp-host <ip>         # With LLRP reader
python cli.py control start <race-id> --llrp-host <ip> --llrp-port <port>
```

### Reports

```bash
python cli.py report text <race-id>                  # Text report
python cli.py report csv <race-id> --output <file>   # CSV export
python cli.py report html <race-id> --output <file>  # HTML report
```

## Race Types and Structure

### Triathlon
- Swim → T1 (Transition) → Bike → T2 (Transition) → Run

### Duathlon
- Run 1 → T1 → Bike → T2 → Run 2

### Aquathlon
- Swim → T1 → Run

### Running
- Single run leg

### Cycling
- Single bike leg

## LLRP RFID Integration

The system supports automatic timing via LLRP RFID readers. When a participant with an assigned RFID tag crosses a timing mat, their time is automatically recorded.

**Setup**:
1. Assign RFID tags to participants using `participant set-rfid`
2. Connect LLRP reader to your network
3. Start race control with `--llrp-host <reader-ip>`

**Supported Readers**: Any LLRP-compliant RFID reader (tested with Impinj readers)

## Database Schema

The system uses SQLite with the following main tables:
- `races` - Race definitions
- `race_legs` - Individual legs/segments
- `participants` - Participant information
- `timing_points` - Timing checkpoints
- `time_records` - Individual timing records
- `race_results` - Calculated results and rankings

Database file: `race_timing.db`

## Example Workflow

```bash
# 1. Initialize
python cli.py init

# 2. Create a triathlon
python cli.py race create --name "Sprint Tri" --type triathlon --date 2024-07-01

# 3. Add participants
python cli.py participant create --first-name Alice --last-name Smith --rfid ABC123
python cli.py participant create --first-name Bob --last-name Jones --rfid DEF456

# 4. Register participants
python cli.py participant register --race-id 1 --participant-id 1 --bib 1
python cli.py participant register --race-id 1 --participant-id 2 --bib 2

# 5. Run the race with LLRP timing
python cli.py control start 1 --llrp-host 192.168.1.130

# 6. Generate reports
python cli.py report text 1
python cli.py report html 1 --output sprint_tri_results.html
```

## Development

### Project Structure

```
RaceTiming/
├── cli.py                  # Command-line interface
├── models.py               # Database models
├── database.py             # Database initialization
├── race_manager.py         # Race and participant management
├── race_control.py         # Live timing control
├── report_generator.py     # Report generation
├── reader.py               # LLRP reader client
├── requirements.txt        # Python dependencies
└── race_timing.db          # SQLite database (created on init)
```

### Running Tests

The system can be tested without an LLRP reader using manual timing:

```bash
# Start race control without LLRP
python cli.py control start 1

# Manually record times
> time 1 Start
> time 1 Finish
> results
```

## Troubleshooting

**Database locked error**: Close any other connections to the database

**LLRP connection failed**: 
- Check reader IP address
- Ensure reader is on the same network
- Verify port 5084 is accessible

**No tags detected**:
- Verify RFID tags are assigned to participants
- Check reader antenna configuration
- Ensure tags are in reader range

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open an issue on the project repository.
