#!/usr/bin/env python3
"""
Race Timing System - Command Line Interface
"""
import click
from datetime import datetime
from database import init_db, get_session
from race_manager import RaceManager, ParticipantManager
from race_control import RaceControl
from report_generator import ReportGenerator
from models import RaceType
from tabulate import tabulate


@click.group()
def cli():
    """Race Timing System - Manage multi-sport races"""
    pass


# ============================================================================
# DATABASE COMMANDS
# ============================================================================

@cli.command()
def init():
    """Initialize the database"""
    init_db()
    click.echo("✓ Database initialized successfully")


# ============================================================================
# RACE MANAGEMENT COMMANDS
# ============================================================================

@cli.group()
def race():
    """Manage races"""
    pass


@race.command('create')
@click.option('--name', prompt=True, help='Race name')
@click.option('--type', 'race_type', 
              type=click.Choice(['triathlon', 'duathlon', 'aquathlon', 'running', 'cycling']),
              prompt=True, help='Race type')
@click.option('--date', prompt=True, help='Race date (YYYY-MM-DD)')
@click.option('--location', help='Race location')
@click.option('--description', help='Race description')
def create_race(name, race_type, date, location, description):
    """Create a new race"""
    manager = RaceManager()
    race = manager.create_race(name, race_type, date, location, description)
    click.echo(f"✓ Race created: {race.name} (ID: {race.id})")
    click.echo(f"  Type: {race.race_type.value}")
    click.echo(f"  Date: {race.date.strftime('%Y-%m-%d')}")
    click.echo(f"  Legs created: {len(race.legs)}")
    click.echo(f"  Timing points created: {len(race.timing_points)}")


@race.command('list')
def list_races():
    """List all races"""
    manager = RaceManager()
    races = manager.list_races()
    
    if not races:
        click.echo("No races found.")
        return
    
    table_data = []
    for r in races:
        table_data.append([
            r.id,
            r.name,
            r.race_type.value,
            r.date.strftime('%Y-%m-%d'),
            r.location or '-'
        ])
    
    click.echo(tabulate(
        table_data,
        headers=['ID', 'Name', 'Type', 'Date', 'Location'],
        tablefmt='simple'
    ))


@race.command('show')
@click.argument('race_id', type=int)
def show_race(race_id):
    """Show race details"""
    manager = RaceManager()
    race = manager.get_race(race_id)
    
    if not race:
        click.echo(f"Race {race_id} not found.")
        return
    
    click.echo(f"\nRace: {race.name}")
    click.echo(f"ID: {race.id}")
    click.echo(f"Type: {race.race_type.value}")
    click.echo(f"Date: {race.date.strftime('%Y-%m-%d')}")
    if race.location:
        click.echo(f"Location: {race.location}")
    
    click.echo(f"\nLegs ({len(race.legs)}):")
    for leg in race.legs:
        dist = f"{leg.distance} {leg.distance_unit}" if leg.distance else "N/A"
        click.echo(f"  {leg.order}. {leg.name} ({leg.leg_type.value}) - {dist}")
    
    click.echo(f"\nTiming Points ({len(race.timing_points)}):")
    for tp in sorted(race.timing_points, key=lambda x: x.order):
        flags = []
        if tp.is_start:
            flags.append("START")
        if tp.is_finish:
            flags.append("FINISH")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        click.echo(f"  {tp.order}. {tp.name}{flag_str}")
    
    click.echo(f"\nParticipants: {len(race.participants)}")


# ============================================================================
# PARTICIPANT MANAGEMENT COMMANDS
# ============================================================================

@cli.group()
def participant():
    """Manage participants"""
    pass


@participant.command('create')
@click.option('--first-name', prompt=True, help='First name')
@click.option('--last-name', prompt=True, help='Last name')
@click.option('--email', help='Email address')
@click.option('--phone', help='Phone number')
@click.option('--gender', type=click.Choice(['M', 'F', 'Other']), help='Gender')
@click.option('--age', type=int, help='Age')
@click.option('--rfid', help='RFID tag (EPC)')
def create_participant(first_name, last_name, email, phone, gender, age, rfid):
    """Create a new participant"""
    manager = ParticipantManager()
    participant = manager.create_participant(
        first_name, last_name, email, phone, gender, age, rfid
    )
    click.echo(f"✓ Participant created: {participant.full_name} (ID: {participant.id})")


@participant.command('list')
@click.option('--race-id', type=int, help='Filter by race ID')
def list_participants(race_id):
    """List all participants"""
    manager = ParticipantManager()
    participants = manager.list_participants(race_id)
    
    if not participants:
        click.echo("No participants found.")
        return
    
    table_data = []
    for p in participants:
        table_data.append([
            p.id,
            p.full_name,
            p.gender or '-',
            p.age or '-',
            p.rfid_tag or '-'
        ])
    
    click.echo(tabulate(
        table_data,
        headers=['ID', 'Name', 'Gender', 'Age', 'RFID Tag'],
        tablefmt='simple'
    ))


@participant.command('register')
@click.option('--race-id', type=int, prompt=True, help='Race ID')
@click.option('--participant-id', type=int, prompt=True, help='Participant ID')
@click.option('--bib', prompt=True, help='Bib number')
@click.option('--category', default='Open', help='Category (default: Open)')
def register_participant(race_id, participant_id, bib, category):
    """Register a participant for a race"""
    manager = ParticipantManager()
    manager.register_participant(race_id, participant_id, bib, category)
    click.echo(f"✓ Participant {participant_id} registered for race {race_id} with bib {bib}")


@participant.command('set-rfid')
@click.option('--participant-id', type=int, prompt=True, help='Participant ID')
@click.option('--rfid', prompt=True, help='RFID tag (EPC)')
def set_rfid(participant_id, rfid):
    """Set RFID tag for a participant"""
    manager = ParticipantManager()
    if manager.update_rfid_tag(participant_id, rfid):
        click.echo(f"✓ RFID tag updated for participant {participant_id}")
    else:
        click.echo(f"Participant {participant_id} not found")


# ============================================================================
# RACE CONTROL COMMANDS
# ============================================================================

@cli.group()
def control():
    """Race control and timing"""
    pass


@control.command('start')
@click.argument('race_id', type=int)
@click.option('--llrp-host', help='LLRP reader IP address')
@click.option('--llrp-port', default=5084, help='LLRP reader port (default: 5084)')
def start_race_control(race_id, llrp_host, llrp_port):
    """Start race control (interactive timing)"""
    race_control = RaceControl(race_id)
    
    click.echo(f"Race Control: {race_control.race.name}")
    click.echo(f"Date: {race_control.race.date.strftime('%Y-%m-%d')}")
    click.echo("")
    
    # Start LLRP if requested
    if llrp_host:
        race_control.start_llrp_timing(llrp_host, llrp_port)
        click.echo("LLRP timing active")
    
    click.echo("\nCommands:")
    click.echo("  time <bib> <point>  - Record time for bib at timing point")
    click.echo("  dnf <bib>           - Mark participant as DNF")
    click.echo("  dns <bib>           - Mark participant as DNS")
    click.echo("  results [n]         - Show top n results (default: 10)")
    click.echo("  quit                - Exit race control")
    click.echo("")
    
    try:
        while True:
            cmd = click.prompt('>', type=str, default='').strip()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            
            if command == 'quit':
                break
            
            elif command == 'time' and len(parts) >= 3:
                bib = parts[1]
                point_name = ' '.join(parts[2:])
                result = race_control.record_manual_time(bib, point_name)
                if result:
                    click.echo(f"✓ Time recorded for bib {bib} at {point_name}")
            
            elif command == 'dnf' and len(parts) >= 2:
                bib = parts[1]
                participant = race_control.participant_manager.get_participant_by_bib(race_id, bib)
                if participant:
                    race_control.mark_dnf(participant.id)
                    click.echo(f"✓ Bib {bib} marked as DNF")
            
            elif command == 'dns' and len(parts) >= 2:
                bib = parts[1]
                participant = race_control.participant_manager.get_participant_by_bib(race_id, bib)
                if participant:
                    race_control.mark_dns(participant.id)
                    click.echo(f"✓ Bib {bib} marked as DNS")
            
            elif command == 'results':
                limit = int(parts[1]) if len(parts) > 1 else 10
                results = race_control.get_live_results(limit)
                
                if results:
                    table_data = []
                    for r in results:
                        time_str = format_time(r.total_time) if r.total_time else "-"
                        table_data.append([
                            r.overall_rank or "-",
                            r.bib_number,
                            r.participant.full_name,
                            r.status.value,
                            time_str
                        ])
                    
                    click.echo(tabulate(
                        table_data,
                        headers=['Rank', 'Bib', 'Name', 'Status', 'Time'],
                        tablefmt='simple'
                    ))
                else:
                    click.echo("No results yet")
            
            else:
                click.echo("Unknown command")
    
    except KeyboardInterrupt:
        click.echo("\nExiting...")
    finally:
        if llrp_host:
            race_control.stop_llrp_timing()


# ============================================================================
# REPORT COMMANDS
# ============================================================================

@cli.group()
def report():
    """Generate race reports"""
    pass


@report.command('text')
@click.argument('race_id', type=int)
def text_report(race_id):
    """Generate text report"""
    generator = ReportGenerator(race_id)
    report = generator.generate_text_report()
    click.echo(report)


@report.command('csv')
@click.argument('race_id', type=int)
@click.option('--output', default='race_results.csv', help='Output filename')
def csv_report(race_id, output):
    """Generate CSV report"""
    generator = ReportGenerator(race_id)
    generator.generate_csv_report(output)


@report.command('html')
@click.argument('race_id', type=int)
@click.option('--output', default='race_results.html', help='Output filename')
def html_report(race_id, output):
    """Generate HTML report"""
    generator = ReportGenerator(race_id)
    generator.generate_html_report(output)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_time(seconds):
    """Format seconds as HH:MM:SS or MM:SS"""
    if seconds is None:
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


if __name__ == '__main__':
    cli()
