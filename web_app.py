"""
Flask Web Application for Race Timing System
"""
from flask import Flask, render_template, jsonify, request, Response, redirect
from datetime import datetime
from database import get_session, init_db
from race_manager import RaceManager, ParticipantManager, EventManager
from llrp_station_manager import LLRPStationManager
from race_control import RaceControl
from report_generator import ReportGenerator
from models import RaceType, ParticipantStatus, StartMode
from reader_service import RFIDReaderService
import json
import time
import threading
import queue
import os
import atexit
import signal
from config_manager import get_config_manager
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Global race control instances
active_race_controls = {}

# Global LLRP service instances
# Map station_id -> RFIDReaderService
active_llrp_services = {}
llrp_services_lock = threading.Lock()

# Event queue for Server-Sent Events
llrp_event_queue = queue.Queue()

# Configuration file path
LLRP_CONFIG_FILE = 'llrp_config.json'

# Session teardown - CRITICAL for preventing connection pool exhaustion
@app.teardown_appcontext
def shutdown_session(exception=None):
    """Remove database session at the end of the request"""
    from database import Session
    Session.remove()

# Shutdown handler for LLRP stations
def shutdown_llrp_stations():
    """Stop all active LLRP stations on application shutdown"""
    print("\n" + "=" * 60)
    print("Shutting down LLRP stations...")
    print("=" * 60)
    
    with llrp_services_lock:
        if active_llrp_services:
            station_ids = list(active_llrp_services.keys())
            
            # Create manager and get its session
            manager = LLRPStationManager()
            
            for station_id in station_ids:
                try:
                    service = active_llrp_services[station_id]
                    print(f"Stopping station {station_id}...")
                    
                    # Stop the service
                    service.stop()
                    
                    # Update database status
                    try:
                        manager.update_station_status(station_id, False)
                        # Explicitly flush to ensure write
                        manager.session.flush()
                        print(f"  ✓ Station {station_id} stopped and database updated")
                    except Exception as db_error:
                        print(f"  ⚠ Station {station_id} stopped but database update failed: {db_error}")
                    
                    del active_llrp_services[station_id]
                    
                except Exception as e:
                    print(f"  ✗ Error stopping station {station_id}: {e}")
            
            # Ensure all changes are committed and session is closed
            try:
                manager.session.commit()
                manager.session.close()
                print("Database session committed and closed.")
            except Exception as e:
                print(f"Warning: Error committing database changes: {e}")
            
            print("All LLRP stations stopped.")
        else:
            print("=" * 60)
    print("All LLRP stations stopped")
    print("=" * 60)

def signal_handler(sig, frame):
    """Handle shutdown signals (SIGINT, SIGTERM)"""
    print("\nReceived shutdown signal, cleaning up...")
    shutdown_llrp_stations()
    import sys
    sys.exit(0)

# Register shutdown handlers
atexit.register(shutdown_llrp_stations)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================================
# WEB PAGES
# ============================================================================

@app.route('/')
def index():
    """Dashboard/Home page"""
    return render_template('index.html')

@app.route('/races')
def races_page():
    """Race management page"""
    return render_template('races.html')

@app.route('/events')
def events_page():
    """Events management page"""
    return render_template('events.html')

@app.route('/event/<int:event_id>')
def event_details_page(event_id):
    """Event details page"""
    return render_template('event_details.html', event_id=event_id)

@app.route('/event/<int:event_id>/master-control')
def event_master_control_page(event_id):
    """Master event timing control page"""
    return render_template('event_master_control.html', event_id=event_id)

@app.route('/participants')
def participants_page():
    """Participant management page"""
    return render_template('participants.html')

@app.route('/llrp-stations')
def llrp_stations_page():
    """LLRP Stations management page"""
    return render_template('llrp_stations.html')

@app.route('/llrp')
def llrp_control_page():
    """Redirect old LLRP control page to new stations page"""
    return redirect(url_for('llrp_stations_page'))

@app.route('/race/<int:race_id>/control')
def race_control_page(race_id):
    """Race control page"""
    return render_template('race_control.html', race_id=race_id)

@app.route('/race/<int:race_id>/leaderboard')
def leaderboard_page(race_id):
    """Live leaderboard page"""
    return render_template('leaderboard.html', race_id=race_id)

@app.route('/race/<int:race_id>/results')
def results_page(race_id):
    """Race results page"""
    return render_template('results.html', race_id=race_id)

@app.route('/all-reads')
def all_reads_page():
    """All race reads dashboard"""
    return render_template('all_reads.html')

@app.route('/event/<int:event_id>/control')
def event_control_page(event_id):
    """Event control page - manage multiple races in an event"""
    return render_template('event_control.html', event_id=event_id)


# ============================================================================
# API - EVENTS
# ============================================================================

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events"""
    try:
        manager = EventManager()
        events = manager.list_events()
        return jsonify([{
            'id': e.id,
            'name': e.name,
            'date': e.date.isoformat() if e.date else None,
            'location': e.location,
            'description': e.description,
            'race_count': len(e.races)
        } for e in events])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def create_event():
    """Create a new event"""
    data = request.json
    if not data or not data.get('name') or not data.get('date'):
        return jsonify({'error': 'name and date are required'}), 400
    try:
        manager = EventManager()
        event = manager.create_event(
            name=data['name'],
            date=data['date'],
            location=data.get('location'),
            description=data.get('description')
        )
        return jsonify({
            'id': event.id,
            'name': event.name,
            'date': event.date.isoformat(),
            'message': 'Event created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get event details"""
    manager = EventManager()
    event = manager.get_event(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    return jsonify({
        'id': event.id,
        'name': event.name,
        'date': event.date.isoformat(),
        'location': event.location,
        'description': event.description,
        'races': [{
            'id': r.id,
            'name': r.name,
            'race_type': r.race_type.value,
            'date': r.date.isoformat(),
            'participant_count': len(r.participants)
        } for r in event.races]
    })

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete an event"""
    manager = EventManager()
    if manager.delete_event(event_id):
        return jsonify({'message': 'Event deleted successfully'})
    return jsonify({'error': 'Event not found'}), 404


# ============================================================================
# API - LLRP STATIONS
# ============================================================================

@app.route('/api/llrp-stations', methods=['GET'])
def get_llrp_stations():
    """Get all LLRP stations"""
    manager = LLRPStationManager()
    stations = manager.list_stations()
    
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'reader_ip': s.reader_ip,
        'reader_port': s.reader_port,
        'cooldown_seconds': s.cooldown_seconds,
        'is_active': s.is_active,
        'last_connected': s.last_connected.isoformat() if s.last_connected else None,
        'created_at': s.created_at.isoformat()
    } for s in stations])

@app.route('/api/llrp-stations', methods=['POST'])
def create_llrp_station():
    """Create a new LLRP station"""
    data = request.json
    manager = LLRPStationManager()
    
    try:
        station = manager.create_station(
            name=data['name'],
            reader_ip=data['reader_ip'],
            reader_port=data.get('reader_port', 5084),
            cooldown_seconds=data.get('cooldown_seconds', 5)
        )
        
        return jsonify({
            'id': station.id,
            'name': station.name,
            'message': 'Station created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/llrp-stations/<int:station_id>', methods=['GET'])
def get_llrp_station(station_id):
    """Get a specific LLRP station"""
    manager = LLRPStationManager()
    station = manager.get_station(station_id)
    
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    return jsonify({
        'id': station.id,
        'name': station.name,
        'reader_ip': station.reader_ip,
        'reader_port': station.reader_port,
        'cooldown_seconds': station.cooldown_seconds,
        'is_active': station.is_active,
        'last_connected': station.last_connected.isoformat() if station.last_connected else None,
        'timing_points': [{
            'id': tp.id,
            'name': tp.name,
            'race_id': tp.race_id
        } for tp in station.timing_points]
    })

@app.route('/api/llrp-stations/<int:station_id>', methods=['PUT'])
def update_llrp_station(station_id):
    """Update an LLRP station"""
    data = request.json
    manager = LLRPStationManager()
    
    station = manager.update_station(station_id, **data)
    if not station:
        return jsonify({'error': 'Station not found'}), 404
    
    return jsonify({
        'id': station.id,
        'name': station.name,
        'message': 'Station updated successfully'
    })

@app.route('/api/llrp-stations/<int:station_id>', methods=['DELETE'])
def delete_llrp_station(station_id):
    """Delete an LLRP station"""
    manager = LLRPStationManager()
    if manager.delete_station(station_id):
        return jsonify({'message': 'Station deleted successfully'})
    return jsonify({'error': 'Station not found'}), 404


# ============================================================================
# API - RACES
# ============================================================================

@app.route('/api/races', methods=['GET'])
def get_races():
    """Get all races"""
    manager = RaceManager()
    races = manager.list_races()
    
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'race_type': r.race_type.value,
        'date': r.date.isoformat(),
        'start_time': r.start_time.isoformat() if r.start_time else None,
        'finish_time': r.finish_time.isoformat() if r.finish_time else None,
        'location': r.location,
        'description': r.description,
        'participant_count': len(r.participants),
        'leg_count': len(r.legs),
        'event_name': r.event.name if r.event else None,
        'event_id': r.event_id
    } for r in races])

@app.route('/api/races', methods=['POST'])
def create_race():
    """Create a new race"""
    data = request.json
    manager = RaceManager()
    
    race = manager.create_race(
        name=data['name'],
        race_type=data['race_type'],
        date=data['date'],
        location=data.get('location'),
        description=data.get('description'),
        event_id=data.get('event_id'),
        start_mode=data.get('start_mode', 'mass_start')
    )
    
    return jsonify({
        'id': race.id,
        'name': race.name,
        'race_type': race.race_type.value,
        'date': race.date.isoformat(),
        'message': 'Race created successfully'
    }), 201

@app.route('/api/race-templates', methods=['GET'])
def get_race_templates():
    """Get all available race templates"""
    from race_templates import get_all_templates
    templates = get_all_templates()
    
    # Convert to list format for easier frontend consumption
    template_list = []
    for template_id, template_data in templates.items():
        template_list.append({
            'id': template_id,
            'name': template_data['name'],
            'race_type': template_data['race_type'],
            'description': template_data['description']
        })
    
    return jsonify(template_list)

@app.route('/api/race-templates/<template_id>', methods=['GET'])
def get_race_template(template_id):
    """Get a specific race template"""
    from race_templates import get_template
    template = get_template(template_id)
    
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    return jsonify(template)

@app.route('/api/races/from-template', methods=['POST'])
def create_race_from_template():
    """Create a race from a template"""
    data = request.json
    from race_templates import get_template
    from models import Race, RaceLeg, TimingPoint, RaceType, LegType
    
    template = get_template(data['template_id'])
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    session = get_session()
    
    # Create the race
    race = Race(
        name=data['name'],
        race_type=RaceType(template['race_type']),
        date=datetime.fromisoformat(data['date']),
        location=data.get('location'),
        description=data.get('description', template['description']),
        age_groups=template.get('age_groups', []),
        event_id=data.get('event_id')
    )
    session.add(race)
    session.flush()  # Get race.id
    
    # Create legs from template
    for leg_data in template['legs']:
        leg = RaceLeg(
            race_id=race.id,
            name=leg_data['name'],
            leg_type=LegType(leg_data['leg_type']),
            distance=leg_data['distance'],
            distance_unit=leg_data['distance_unit'],
            order=leg_data['order']
        )
        session.add(leg)
    
    # Create timing points from template
    for tp_data in template['timing_points']:
        timing_point = TimingPoint(
            race_id=race.id,
            name=tp_data['name'],
            order=tp_data['order'],
            is_start=tp_data['is_start'],
            is_finish=tp_data['is_finish']
        )
        session.add(timing_point)
    
    session.commit()
    
    return jsonify({
        'id': race.id,
        'name': race.name,
        'race_type': race.race_type.value,
        'date': race.date.isoformat(),
        'message': 'Race created from template successfully'
    }), 201

@app.route('/api/races/<int:race_id>', methods=['GET'])
def get_race(race_id):
    """Get race details"""
    try:
        race_manager = RaceManager()
        race = race_manager.get_race(race_id)
        
        if not race:
            return jsonify({'error': 'Race not found'}), 404
        
        # Get timing points with LLRP station info
        timing_points = []
        for tp in race.timing_points:
            tp_data = {
                'id': tp.id,
                'name': tp.name,
                'order': tp.order,
                'is_start': tp.is_start,
                'is_finish': tp.is_finish,
                'llrp_station_id': tp.llrp_station_id,
                'llrp_station': None
            }
            
            # Add LLRP station info if assigned
            if tp.llrp_station_id and tp.llrp_station:
                tp_data['llrp_station'] = {
                    'id': tp.llrp_station.id,
                    'name': tp.llrp_station.name
                }
            
            timing_points.append(tp_data)
        
        return jsonify({
            'id': race.id,
            'name': race.name,
            'race_type': race.race_type.value if race.race_type else None,
            'date': race.date.isoformat() if race.date else None,
            'location': race.location,
            'description': race.description,
            'start_time': race.start_time.isoformat() if race.start_time else None,
            'finish_time': race.finish_time.isoformat() if race.finish_time else None,
            'start_mode': race.start_mode.value if race.start_mode else 'mass_start',
            'llrp_enabled': race.llrp_enabled,
            'event_id': race.event_id,
            'event_name': race.event.name if race.event else None,
            'participant_count': len(race.participants),
            'timing_points': timing_points,
            'age_groups': race.age_groups or [],
            'participants': [{
                'id': p.id,
                'name': p.full_name,
                'rfid_tag': p.rfid_tag
            } for p in race.participants]
        })
    except Exception as e:
        print(f"Error getting race {race_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/races/<int:race_id>/start', methods=['POST'])
def start_race(race_id):
    """Start the race (set start time to now)"""
    try:
        print(f"=== Starting race {race_id} ===")
        session = get_session()
        from models import Race, TimingPoint, TimeRecord, TimingSource
        race = session.query(Race).get(race_id)
        
        if not race:
            print(f"Race {race_id} not found")
            return jsonify({'error': 'Race not found'}), 404
        
        print(f"Race found: {race.name}, current start_time: {race.start_time}")
        race.start_time = datetime.utcnow()
        print(f"Set new start_time: {race.start_time}")
        
        # For Mass Start, create start records for all participants
        if race.start_mode == StartMode.MASS_START:
            print(f"Race is MASS_START mode, creating start records...")
            # Get Start timing point
            start_tp = session.query(TimingPoint).filter(
                TimingPoint.race_id == race_id,
                TimingPoint.is_start == True
            ).first()
            
            if start_tp:
                print(f"Found start timing point: {start_tp.name}")
                # Get all participants
                participant_count = 0
                for participant in race.participants:
                    # Check if start record already exists
                    existing = session.query(TimeRecord).filter(
                        TimeRecord.race_id == race_id,
                        TimeRecord.participant_id == participant.id,
                        TimeRecord.timing_point_id == start_tp.id
                    ).first()
                    
                    if not existing:
                        # Create start record
                        record = TimeRecord(
                            race_id=race_id,
                            participant_id=participant.id,
                            timing_point_id=start_tp.id,
                            timestamp=race.start_time,
                            source=TimingSource.SYSTEM
                        )
                        session.add(record)
                        participant_count += 1
                print(f"Created {participant_count} start records")
            else:
                print("No start timing point found")
        else:
            print(f"Race is CHIP_START mode, no start records needed")
        
        print("Committing changes to database...")
        session.commit()
        print("Database commit successful")
        
        # Trigger recalculation to update all participants to STARTED
        print("Triggering result calculation...")
        if race_id not in active_race_controls:
            active_race_controls[race_id] = RaceControl(race_id)
        
        # Activate timing to process LLRP tag reads
        active_race_controls[race_id].start_timing()
        print("Race timing activated for LLRP tag processing")
        
        active_race_controls[race_id].calculate_results()
        print("Result calculation complete")
        
        return jsonify({
            'message': 'Race started',
            'start_time': race.start_time.isoformat()
        })
    except Exception as e:
        print(f"Error starting race: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/races/<int:race_id>/start-time', methods=['PUT'])
def update_race_start_time(race_id):
    """Update race start time manually"""
    data = request.json
    session = get_session()
    from models import Race
    race = session.query(Race).get(race_id)
    
    if not race:
        return jsonify({'error': 'Race not found'}), 404
        
    try:
        # Expect ISO format string
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        race.start_time = start_time
        session.commit()
        
        return jsonify({
            'message': 'Start time updated',
            'start_time': race.start_time.isoformat()
        })
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

@app.route('/api/races/<int:race_id>/stop', methods=['POST'])
def stop_race(race_id):
    """Stop the race (set finish time to now)"""
    session = get_session()
    from models import Race
    race = session.query(Race).get(race_id)
    
    if not race:
        return jsonify({'error': 'Race not found'}), 404
        
    race.finish_time = datetime.utcnow()
    session.commit()
    
    # Stop LLRP if running
    try:
        if race_id in active_race_controls:
            active_race_controls[race_id].stop_timing()
            
        # Also stop physical stations via manager if needed
        # But RaceControl.stop_timing just sets a flag.
        # We might want to explicitly stop LLRP stations associated with this race?
        # For now, let's just rely on the UI calling stopLLRP or the user doing it manually if they want to free up readers.
        # But strictly speaking, "Stop Race" implies stopping timing.
        pass
    except Exception as e:
        print(f"Error stopping timing: {e}")
    
    return jsonify({
        'message': 'Race stopped',
        'finish_time': race.finish_time.isoformat()
    })

@app.route('/api/races/<int:race_id>/reset', methods=['POST'])
def reset_race(race_id):
    """Reset the race (clear times and results)"""
    session = get_session()
    from models import (
    Race, RaceType, Participant, RaceResult, TimeRecord, 
    TimingPoint, ParticipantStatus, RaceLeg, LegType, 
    TimingSource, LLRPStation, Event, StartMode
)
    race = session.query(Race).get(race_id)
    if not race:
        return jsonify({'error': 'Race not found'}), 404
        
    # Clear race times
    race.start_time = None
    race.finish_time = None
    
    # Delete all time records
    session.query(TimeRecord).filter(TimeRecord.race_id == race_id).delete()
    
    # Reset all race results
    results = session.query(RaceResult).filter(RaceResult.race_id == race_id).all()
    for result in results:
        result.status = ParticipantStatus.REGISTERED
        result.start_time = None
        result.finish_time = None
        result.total_time = None
        result.split_times = None
        result.overall_rank = None
        result.category_rank = None
        result.gender_rank = None
        
    session.commit()
    
    # Stop timing if active
    if race_id in active_race_controls:
        active_race_controls[race_id].stop_timing()
        del active_race_controls[race_id]
        
    return jsonify({'message': 'Race reset successfully'})

@app.route('/api/races/<int:race_id>/timing-points', methods=['POST'])
def add_timing_point(race_id):
    """Add a timing point to a race"""
    data = request.json
    manager = RaceManager()
    try:
        tp = manager.add_timing_point(
            race_id=race_id,
            name=data['name'],
            order=int(data['order']),
            is_start=data.get('is_start', False),
            is_finish=data.get('is_finish', False),
            llrp_station_id=data.get('llrp_station_id')
        )
        return jsonify({
            'id': tp.id,
            'name': tp.name,
            'order': tp.order,
            'is_start': tp.is_start,
            'is_finish': tp.is_finish,
            'llrp_station_id': tp.llrp_station_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/races/<int:race_id>/timing-points/<int:tp_id>', methods=['PUT'])
def update_timing_point(race_id, tp_id):
    """Update a timing point (e.g., assign LLRP station)"""
    data = request.json
    session = get_session()
    
    from models import TimingPoint
    tp = session.query(TimingPoint).filter(TimingPoint.id == tp_id).first()
    
    if not tp:
        return jsonify({'error': 'Timing point not found'}), 404
    
    # Update allowed fields
    if 'llrp_station_id' in data:
        tp.llrp_station_id = data['llrp_station_id']
    if 'name' in data:
        tp.name = data['name']
    if 'order' in data:
        tp.order = data['order']
    
    session.commit()
    
    return jsonify({
        'id': tp.id,
        'name': tp.name,
        'llrp_station_id': tp.llrp_station_id,
        'message': 'Timing point updated'
    })

@app.route('/api/races/<int:race_id>/timing-points/<int:tp_id>', methods=['DELETE'])
def delete_timing_point(race_id, tp_id):
    """Delete a timing point"""
    manager = RaceManager()
    if manager.delete_timing_point(tp_id):
        return jsonify({'message': 'Timing point deleted'})
    return jsonify({'error': 'Timing point not found'}), 404

@app.route('/api/races/<int:race_id>/age-groups', methods=['PUT'])
def update_age_groups(race_id):
    """Update race age groups"""
    data = request.json
    manager = RaceManager()
    
    try:
        age_groups = data.get('age_groups', [])
        age_groups_json = json.dumps(age_groups)
        
        if manager.update_race_age_groups(race_id, age_groups_json):
            return jsonify({'message': 'Age groups updated'})
        return jsonify({'error': 'Race not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races/<int:race_id>', methods=['DELETE'])
def delete_race(race_id):
    """Delete a race"""
    manager = RaceManager()
    if manager.delete_race(race_id):
        return jsonify({'message': 'Race deleted successfully'})
    return jsonify({'error': 'Race not found'}), 404

@app.route('/api/races/<int:race_id>/event', methods=['PUT'])
def update_race_event(race_id):
    """Update a race's event assignment"""
    data = request.json
    event_id = data.get('event_id')  # Can be None to unassign
    
    manager = RaceManager()
    try:
        if manager.update_race_event(race_id, event_id):
            return jsonify({'message': 'Race event updated successfully'})
        return jsonify({'error': 'Race not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API - RACE PARTICIPANTS (with times/splits)
# ============================================================================

@app.route('/api/races/<int:race_id>/participants', methods=['GET'])
def get_race_participants(race_id):
    """Get all participants in a race with their bib, category, status, and time records"""
    try:
        session = get_session()
        from models import Race, RaceResult, TimeRecord, race_participants as rp_table
        from sqlalchemy import text

        race = session.query(Race).get(race_id)
        if not race:
            return jsonify({'error': 'Race not found'}), 404

        # Build participant list from race_participants association table
        rows = session.execute(
            text("SELECT participant_id, bib_number, category FROM race_participants WHERE race_id = :rid"),
            {'rid': race_id}
        ).fetchall()

        # Build a lookup of results keyed by participant_id
        results_map = {}
        for r in session.query(RaceResult).filter(RaceResult.race_id == race_id).all():
            results_map[r.participant_id] = r

        # Build a lookup of time records keyed by participant_id
        time_records_map = {}
        for tr in (session.query(TimeRecord)
                   .filter(TimeRecord.race_id == race_id)
                   .order_by(TimeRecord.timestamp)
                   .all()):
            time_records_map.setdefault(tr.participant_id, []).append(tr)

        # Get timing points ordered
        timing_points = sorted(race.timing_points, key=lambda tp: tp.order)

        participants_out = []
        for row in rows:
            from models import Participant
            p = session.query(Participant).get(row.participant_id)
            if not p:
                continue

            result = results_map.get(p.id)
            records = time_records_map.get(p.id, [])

            # Build splits: timing_point_name -> {timestamp, elapsed_seconds}
            splits = []
            race_start = race.start_time
            for tp in timing_points:
                # Find the time record for this timing point
                tr = next((r for r in records if r.timing_point_id == tp.id), None)
                split_entry = {
                    'timing_point_id': tp.id,
                    'timing_point_name': tp.name,
                    'is_start': tp.is_start,
                    'is_finish': tp.is_finish,
                    'order': tp.order,
                    'timestamp': tr.timestamp.isoformat() if tr else None,
                    'source': tr.source.value if tr else None,
                    'time_record_id': tr.id if tr else None,
                    'elapsed_seconds': None,
                    'split_seconds': None,
                }
                if tr and race_start:
                    split_entry['elapsed_seconds'] = (tr.timestamp - race_start).total_seconds()
                # Calculate split from previous checkpoint
                if tr and splits:
                    prev = next((s for s in reversed(splits) if s['timestamp']), None)
                    if prev:
                        from datetime import datetime as dt
                        prev_ts = dt.fromisoformat(prev['timestamp'])
                        split_entry['split_seconds'] = (tr.timestamp - prev_ts).total_seconds()
                splits.append(split_entry)

            participants_out.append({
                'id': p.id,
                'first_name': p.first_name,
                'last_name': p.last_name,
                'full_name': p.full_name,
                'email': p.email,
                'phone': p.phone,
                'gender': p.gender,
                'age': p.age,
                'rfid_tag': p.rfid_tag,
                'bib_number': row.bib_number,
                'category': row.category,
                'status': result.status.value if result and result.status else 'registered',
                'total_time': result.total_time if result else None,
                'overall_rank': result.overall_rank if result else None,
                'splits': splits,
            })

        # Sort by bib number
        participants_out.sort(key=lambda x: (x['bib_number'] or '').zfill(10))

        return jsonify(participants_out)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/races/<int:race_id>/participants/<int:participant_id>/registration', methods=['PUT'])
def update_race_registration(race_id, participant_id):
    """Update a participant's race registration (bib number, category)"""
    try:
        data = request.json
        session = get_session()
        from sqlalchemy import text

        # Update the race_participants association table
        updates = []
        params = {'race_id': race_id, 'participant_id': participant_id}

        if 'bib_number' in data:
            updates.append('bib_number = :bib_number')
            params['bib_number'] = data['bib_number']
        if 'category' in data:
            updates.append('category = :category')
            params['category'] = data['category']

        if updates:
            session.execute(
                text(f"UPDATE race_participants SET {', '.join(updates)} WHERE race_id = :race_id AND participant_id = :participant_id"),
                params
            )
            session.commit()

        return jsonify({'message': 'Registration updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API - PARTICIPANTS
# ============================================================================

@app.route('/api/participants', methods=['GET'])
def get_participants():
    """Get all participants"""
    manager = ParticipantManager()
    race_id = request.args.get('race_id', type=int)
    participants = manager.list_participants(race_id)
    
    return jsonify([{
        'id': p.id,
        'first_name': p.first_name,
        'last_name': p.last_name,
        'full_name': p.full_name,
        'email': p.email,
        'phone': p.phone,
        'gender': p.gender,
        'age': p.age,
        'rfid_tag': p.rfid_tag
    } for p in participants])

@app.route('/api/participants', methods=['POST'])
def create_participant():
    """Create a new participant"""
    data = request.json
    manager = ParticipantManager()
    
    participant = manager.create_participant(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data.get('email'),
        phone=data.get('phone'),
        gender=data.get('gender'),
        age=data.get('age'),
        rfid_tag=data.get('rfid_tag')
    )
    
    return jsonify({
        'id': participant.id,
        'name': participant.full_name,
        'message': 'Participant created successfully'
    }), 201

@app.route('/api/participants/<int:participant_id>/register', methods=['POST'])
def register_participant(participant_id):
    """Register participant for a race"""
    data = request.json
    manager = ParticipantManager()
    
    manager.register_participant(
        race_id=data['race_id'],
        participant_id=participant_id,
        bib_number=data['bib_number'],
        category=data.get('category', 'Open')
    )
    
    return jsonify({'message': 'Participant registered successfully'})

@app.route('/api/participants/<int:participant_id>', methods=['PUT', 'DELETE'])
def update_participant(participant_id):
    """Update or delete participant information"""
    if request.method == 'DELETE':
        manager = ParticipantManager()
        if manager.delete_participant(participant_id):
            return jsonify({'message': 'Participant deleted successfully'})
        return jsonify({'error': 'Participant not found'}), 404
    
    # PUT method
    data = request.json
    manager = ParticipantManager()
    
    if manager.update_participant(participant_id, **data):
        return jsonify({'message': 'Participant updated successfully'})
    return jsonify({'error': 'Participant not found'}), 404

@app.route('/api/participants/<int:participant_id>/rfid', methods=['PUT'])
def update_rfid(participant_id):
    """Update participant RFID tag"""
    data = request.json
    manager = ParticipantManager()
    
    if manager.update_rfid_tag(participant_id, data['rfid_tag']):
        return jsonify({'message': 'RFID tag updated successfully'})
    return jsonify({'error': 'Participant not found'}), 404

@app.route('/api/participants/import', methods=['POST'])
def import_participants():
    """Import participants from Excel file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'}), 400
    
    # Get optional race_id for registration
    race_id = request.form.get('race_id', type=int)
    
    # Save file temporarily
    import os
    import tempfile
    from import_utils import import_participants_from_excel
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)
    
    try:
        result = import_participants_from_excel(temp_path, race_id)
        os.remove(temp_path)  # Clean up
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

@app.route('/api/age-groups', methods=['GET'])
def get_age_groups():
    """Get list of available age groups"""
    from race_manager import get_age_group
    
    # Generate all standard age groups
    age_groups = []
    brackets = ["Under 20", "20-29", "30-39", "40-49", "50-59", "60+"]
    genders = [("M", "Male"), ("F", "Female")]
    
    for gender_code, gender_name in genders:
        for bracket in brackets:
            age_groups.append({
                'value': f"{gender_name} {bracket}",
                'label': f"{gender_name} {bracket}"
            })
    
    # Add non-gendered options
    for bracket in brackets:
        age_groups.append({
            'value': bracket,
            'label': bracket
        })
    
    return jsonify(age_groups)


# ============================================================================
# API - LLRP SERVICE
# ============================================================================

def load_llrp_config():
    """Load LLRP configuration from file or return defaults."""
    default_config = {
        "reader_ip": "192.168.1.100",
        "reader_port": 5084,
        "cooldown_seconds": 5
    }
    
    if os.path.exists(LLRP_CONFIG_FILE):
        try:
            with open(LLRP_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                default_config.update(config)
                return default_config
        except Exception as e:
            print(f"Error loading LLRP config: {e}")
            return default_config
    
    return default_config


def save_llrp_config(config):
    """Save LLRP configuration to file."""
    try:
        with open(LLRP_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving LLRP config: {e}")
        return False


def emit_llrp_event(event_type, data):
    """Emit an LLRP event to all SSE clients."""
    event = {
        'type': event_type,
        'data': data,
        'timestamp': time.time()
    }
    llrp_event_queue.put(event)


def llrp_status_callback(message, level="info", station_id=None):
    """Callback for LLRP status updates"""
    emit_llrp_event('status', {
        'message': message,
        'level': level,
        'station_id': station_id,
        'timestamp': datetime.now().isoformat()
    })


def llrp_tag_callback(epc, rssi, timestamp, station_id=None):
    """Callback for LLRP tag reads"""
    # Emit SSE event
    event_data = {
        'epc': epc,
        'rssi': rssi,
        'timestamp': timestamp,
        'station_id': station_id
    }
    llrp_event_queue.put(('tag', event_data))
    
    # Pass to active race controls
    # We iterate over a copy of values to avoid thread safety issues
    for race_control in list(active_race_controls.values()):
        try:
            print("entering", epc, timestamp, station_id)
            # Pass station_id to race control
            race_control.process_tag_read(epc, timestamp, station_id)
        except Exception as e:
            print(f"Error processing tag in race control: {e}")


@app.route('/api/llrp/config', methods=['GET'])
def get_llrp_config():
    """Get current LLRP configuration."""
    config = load_llrp_config()
    # Don't send sensitive data to frontend
    safe_config = config.copy()

    return jsonify(safe_config)


@app.route('/api/llrp/config', methods=['POST'])
def update_llrp_config():
    """Update LLRP configuration."""
    global llrp_service
    
    try:
        new_config = request.json
        
        # Validate required fields
        required_fields = ['reader_ip', 'reader_port', 'cooldown_seconds']
        for field in required_fields:
            if field not in new_config:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # If service is running, don't allow config changes
        with llrp_service_lock:
            if llrp_service and llrp_service.is_running():
                return jsonify({'error': 'Cannot update configuration while service is running'}), 400
        
        # Save configuration
        if save_llrp_config(new_config):
            emit_llrp_event('config_updated', {'message': 'Configuration updated successfully'})
            return jsonify({'success': True, 'message': 'Configuration updated'})
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/llrp-stations/<int:station_id>/start', methods=['POST'])
def start_station_service(station_id):
    """Start a specific LLRP station service"""
    manager = LLRPStationManager()
    station_config = manager.get_station_config(station_id)
    
    if not station_config:
        return jsonify({'error': 'Station not found'}), 404
        
    with llrp_services_lock:
        if station_id in active_llrp_services and active_llrp_services[station_id].is_running():
            return jsonify({'error': 'Station service is already running'}), 400
            
        try:
            # Initialize service with station config
            service = RFIDReaderService(station_config)
            service.set_status_callback(llrp_status_callback)
            service.set_tag_callback(llrp_tag_callback)
            
            if service.start():
                active_llrp_services[station_id] = service
                # Update DB status
                manager.update_station_status(station_id, True)
                
                emit_llrp_event('service_started', {
                    'message': f"Station '{station_config['station_name']}' started",
                    'station_id': station_id
                })
                return jsonify({'success': True, 'message': 'Station service started'})
            else:
                return jsonify({'error': 'Failed to start station service'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/llrp-stations/<int:station_id>/stop', methods=['POST'])
def stop_station_service(station_id):
    """Stop a specific LLRP station service"""
    with llrp_services_lock:
        service = active_llrp_services.get(station_id)
        if not service:
            return jsonify({'error': 'Station service is not running'}), 400
            
        try:
            if service.stop():
                del active_llrp_services[station_id]
                
                # Update DB status
                manager = LLRPStationManager()
                manager.update_station_status(station_id, False)
                
                emit_llrp_event('service_stopped', {
                    'message': 'Station service stopped',
                    'station_id': station_id
                })
                return jsonify({'success': True, 'message': 'Station service stopped'})
            else:
                return jsonify({'error': 'Failed to stop station service'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/llrp-stations/<int:station_id>/status', methods=['GET'])
def get_station_status(station_id):
    """Get status of a specific station service"""
    with llrp_services_lock:
        service = active_llrp_services.get(station_id)
        is_running = service.is_running() if service else False
        
    return jsonify({
        'station_id': station_id,
        'running': is_running,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/llrp/events')
def llrp_events():
    """Server-Sent Events endpoint for real-time LLRP updates."""
    def generate():
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': time.time()})}\n\n"
        
        # Stream events from the queue
        while True:
            try:
                # Wait for an event with timeout
                event = llrp_event_queue.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send keepalive
                yield f": keepalive\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


# ============================================================================
# API - RACE CONTROL
# ============================================================================

@app.route('/api/races/<int:race_id>/results', methods=['GET'])
def get_results(race_id):
    """Get race results"""
    # Verify race exists before creating control
    manager = RaceManager()
    if not manager.get_race(race_id):
        return jsonify({'error': f'Race {race_id} not found'}), 404
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    race_control = active_race_controls[race_id]
    results = race_control.get_live_results()
    return jsonify([{
        'id': r.id,
        'rank': r.overall_rank,
        'bib_number': r.bib_number,
        'participant': {
            'id': r.participant.id,
            'name': r.participant.full_name,
            'gender': r.participant.gender,
            'age': r.participant.age,
            'category': r.category if hasattr(r, 'category') else None,
            'status': r.status.value if hasattr(r, 'status') and r.status else None
        },
        'status': r.status.value if hasattr(r, 'status') and r.status else None,
        'total_time': r.total_time,
        'finish_time': r.finish_time.isoformat() if r.finish_time else None
    } for r in results])
@app.route('/api/races/<int:race_id>/control/start-llrp', methods=['POST'])
def start_llrp(race_id):
    """Start LLRP timing for a race"""
    manager = RaceManager()
    race = manager.get_race(race_id)
    if not race:
        return jsonify({'error': f'Race {race_id} not found'}), 404
    try:
        if race_id in active_race_controls:
            active_race_controls[race_id].start_timing()
        else:
            race_control = RaceControl(race_id)
            race_control.start_timing()
            active_race_controls[race_id] = race_control
        
        # Persist LLRP enabled state
        session = get_session()
        race.llrp_enabled = True
        session.commit()
        
        return jsonify({'message': 'Race timing enabled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/races/<int:race_id>/control/stop-llrp', methods=['POST'])
def stop_llrp(race_id):
    """Stop LLRP timing for a race"""
    manager = RaceManager()
    race = manager.get_race(race_id)
    if not race:
        return jsonify({'error': f'Race {race_id} not found'}), 404
    
    if race_id in active_race_controls:
        active_race_controls[race_id].stop_timing()
        del active_race_controls[race_id]
    
    # Persist LLRP disabled state
    session = get_session()
    race.llrp_enabled = False
    session.commit()
    
    return jsonify({'message': 'Race timing disabled'})

@app.route('/api/races/<int:race_id>/control/time', methods=['POST'])
def record_time(race_id):
    """Record a manual time"""
    data = request.json
    
    # Get or create race control
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    race_control = active_race_controls[race_id]
    
    timestamp = datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else None
    
    result = race_control.record_manual_time(
        bib_number=data['bib_number'],
        timing_point_name=data['timing_point'],
        timestamp=timestamp,
        notes=data.get('notes')
    )
    
    if result:
        return jsonify({'message': 'Time recorded successfully'})
    return jsonify({'error': 'Failed to record time'}), 400

@app.route('/api/races/<int:race_id>/control/time-auto', methods=['POST'])
def record_time_auto(race_id):
    """Record a manual time automatically at next timing point"""
    data = request.json
    
    # Get or create race control
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    race_control = active_race_controls[race_id]
    
    timestamp = datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else None
    
    result = race_control.record_manual_time_auto(
        bib_number=data['bib_number'],
        timestamp=timestamp,
        notes=data.get('notes')
    )
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400

@app.route('/api/races/<int:race_id>/control/dnf', methods=['POST'])
def mark_dnf(race_id):
    """Mark participant as DNF"""
    data = request.json
    
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    race_control = active_race_controls[race_id]
    participant = race_control.participant_manager.get_participant_by_bib(race_id, data['bib_number'])
    
    if participant:
        race_control.mark_dnf(participant.id, data.get('notes'))
        return jsonify({'message': 'Participant marked as DNF'})
    return jsonify({'error': 'Participant not found'}), 404

@app.route('/api/races/<int:race_id>/control/dns', methods=['POST'])
def mark_dns(race_id):
    """Mark participant as DNS"""
    data = request.json
    
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    race_control = active_race_controls[race_id]
    participant = race_control.participant_manager.get_participant_by_bib(race_id, data['bib_number'])
    
    if participant:
        race_control.mark_dns(participant.id, data.get('notes'))
        return jsonify({'message': 'Participant marked as DNS'})
    return jsonify({'error': 'Participant not found'}), 404


# ============================================================================
# API - RESULTS
# ============================================================================



@app.route('/api/results/<int:result_id>', methods=['PUT'])
def update_result(result_id):
    """Update a race result"""
    data = request.json
    session = get_session()
    from models import RaceResult, ParticipantStatus
    
    result = session.query(RaceResult).get(result_id)
    if not result:
        return jsonify({'error': 'Result not found'}), 404
    
    # Update status if provided
    if 'status' in data:
        result.status = ParticipantStatus(data['status'])
    
    session.commit()
    return jsonify({'message': 'Result updated successfully'})

@app.route('/api/results/<int:result_id>', methods=['DELETE'])
def delete_result(result_id):
    """Delete a race result"""
    session = get_session()
    from models import RaceResult
    
    result = session.query(RaceResult).get(result_id)
    if not result:
        return jsonify({'error': 'Result not found'}), 404
    
    session.delete(result)
    session.commit()
    return jsonify({'message': 'Result deleted successfully'})

@app.route('/api/races/<int:race_id>/time-records', methods=['GET'])
def get_time_records(race_id):
    """Get all time records for a race"""
    session = get_session()
    from models import TimeRecord, Participant, TimingPoint
    
    records = session.query(TimeRecord).filter(
        TimeRecord.race_id == race_id
    ).order_by(TimeRecord.timestamp.desc()).all()
    
    return jsonify([{
        'id': r.id,
        'participant': {
            'id': r.participant.id,
            'name': r.participant.full_name,
            'rfid_tag': r.participant.rfid_tag
        },
        'timing_point': {
            'id': r.timing_point.id,
            'name': r.timing_point.name,
            'order': r.timing_point.order
        },
        'timestamp': r.timestamp.isoformat(),
        'source': r.source.value,
        'notes': r.notes
    } for r in records])

@app.route('/api/races/<int:race_id>/time-records', methods=['POST'])
def create_time_record(race_id):
    """Create a new time record"""
    data = request.json
    session = get_session()
    from models import TimeRecord, TimingSource
    
    try:
        record = TimeRecord(
            race_id=race_id,
            participant_id=data['participant_id'],
            timing_point_id=data['timing_point_id'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            source=TimingSource(data.get('source', 'manual')),
            notes=data.get('notes')
        )
        session.add(record)
        session.commit()
        
        # Trigger recalculation
        if race_id not in active_race_controls:
            active_race_controls[race_id] = RaceControl(race_id)
        
        active_race_controls[race_id].calculate_results()
        
        return jsonify({
            'id': record.id,
            'message': 'Time record created successfully'
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/time-records/<int:record_id>', methods=['PUT'])
def update_time_record(record_id):
    """Update a time record"""
    data = request.json
    session = get_session()
    from models import TimeRecord
    
    record = session.query(TimeRecord).get(record_id)
    if not record:
        return jsonify({'error': 'Time record not found'}), 404
    
    try:
        if 'timestamp' in data:
            record.timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        if 'timing_point_id' in data:
            record.timing_point_id = data['timing_point_id']
        if 'notes' in data:
            record.notes = data['notes']
        
        session.commit()
        
        # Trigger recalculation
        if record.race_id not in active_race_controls:
            active_race_controls[record.race_id] = RaceControl(record.race_id)
        
        active_race_controls[record.race_id].calculate_results()
        
        return jsonify({'message': 'Time record updated successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/time-records/<int:record_id>', methods=['DELETE'])
def delete_time_record(record_id):
    """Delete a time record"""
    session = get_session()
    from models import TimeRecord
    
    record = session.query(TimeRecord).get(record_id)
    if not record:
        return jsonify({'error': 'Time record not found'}), 404
    
    race_id = record.race_id
    session.delete(record)
    session.commit()
    
    # Trigger recalculation
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    active_race_controls[race_id].calculate_results()
    
    return jsonify({'message': 'Time record deleted successfully'})

@app.route('/api/races/<int:race_id>/recalculate', methods=['POST'])
def recalculate_results(race_id):
    """Manually trigger result recalculation"""
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    active_race_controls[race_id].calculate_results()
    return jsonify({'message': 'Results recalculated successfully'})


@app.route('/api/races/<int:race_id>/leaderboard', methods=['GET'])
def get_leaderboard(race_id):
    """Get live leaderboard with optional filters"""
    limit = request.args.get('limit', 50, type=int)
    gender = request.args.get('gender', None)
    age_group = request.args.get('age_group', None)
    
    if race_id not in active_race_controls:
        active_race_controls[race_id] = RaceControl(race_id)
    
    race_control = active_race_controls[race_id]
    results = race_control.get_live_results(limit=None)  # Get all, we'll filter
    
    # Filter to finished and started participants (those with ranks)
    active_results = [r for r in results if r.status in [ParticipantStatus.FINISHED, ParticipantStatus.STARTED]]
    
    # Apply gender filter
    if gender:
        active_results = [r for r in active_results if r.participant.gender == gender]
    
    # Apply age group filter
    if age_group:
        active_results = [r for r in active_results if r.category == age_group]
    
    # Sort by overall rank
    active_results.sort(key=lambda r: r.overall_rank if r.overall_rank else float('inf'))
    
    # Apply limit
    if limit:
        active_results = active_results[:limit]
    
    # Get current time for elapsed time calculation
    current_time = datetime.utcnow()
    
    # Build response with checkpoint data
    response_data = []
    for r in active_results:
        # Parse split times to find last checkpoint
        last_checkpoint_name = None
        last_checkpoint_time = None
        
        if r.split_times:
            try:
                splits = json.loads(r.split_times)
                if splits:
                    # Get the last checkpoint (most recent)
                    last_checkpoint_name = list(splits.keys())[-1]
                    last_checkpoint_time = splits[last_checkpoint_name]
            except:
                pass
        
        # Calculate current elapsed time for active racers
        current_elapsed = None
        if r.status == ParticipantStatus.STARTED and r.start_time:
            current_elapsed = (current_time - r.start_time).total_seconds()
        
        response_data.append({
            'rank': r.overall_rank,
            'bib_number': r.bib_number,
            'name': r.participant.full_name,
            'gender': r.participant.gender,
            'age': r.participant.age,
            'category': r.category,
            'status': r.status.value,
            'total_time': r.total_time,
            'total_time_formatted': format_time(r.total_time) if r.total_time else None,
            'current_elapsed': current_elapsed,
            'current_elapsed_formatted': format_time(current_elapsed) if current_elapsed else None,
            'last_checkpoint_name': last_checkpoint_name,
            'last_checkpoint_time': last_checkpoint_time
        })
    
    return jsonify(response_data)

@app.route('/api/races/<int:race_id>/stream')
def stream_updates(race_id):
    """Server-Sent Events stream for live updates"""
    def generate():
        while True:
            # Get latest results
            if race_id in active_race_controls:
                race_control = active_race_controls[race_id]
                results = race_control.get_live_results(limit=10)
                
                data = [{
                    'rank': r.overall_rank,
                    'bib': r.bib_number,
                    'name': r.participant.full_name,
                    'time': format_time(r.total_time) if r.total_time else '-',
                    'status': r.status.value
                } for r in results]
                
                yield f"data: {json.dumps(data)}\n\n"
            
            time.sleep(5)  # Update every 5 seconds
    
    return Response(generate(), mimetype='text/event-stream')


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


# ============================================================================
# RESULTS PUBLISHING ENDPOINTS
# ============================================================================

@app.route('/api/races/<int:race_id>/publish', methods=['POST'])
def publish_race_results(race_id):
    """Publish race results to the public results site"""
    from results_publisher import ResultsPublisher
    
    manager = RaceManager()
    race = manager.get_race(race_id)
    if not race:
        return jsonify({'error': f'Race {race_id} not found'}), 404
    
    try:
        publisher = ResultsPublisher()
        # Test connection first
        if not publisher.test_connection():
            return jsonify({
                'error': 'Cannot connect to results publishing site',
                'url': publisher.results_site_url
            }), 503
        
        # Publish the results
        success = publisher.publish_results(
            race_id,
            publish_type='manual',
            published_by=request.json.get('published_by', 'admin') if request.json else 'admin'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Results published successfully for race: {race.name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to publish results'
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<int:event_id>/publish', methods=['POST'])
def publish_event_results(event_id):
    """Publish all races in an event"""
    from results_publisher import ResultsPublisher
    session = get_session()
    try:
        from models import Event
        
        event = session.query(Event).get(event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        published_count = 0
        errors = []
        race_count = len(event.races)
        publisher = ResultsPublisher()
        
        for race in event.races:
            try:
                if publisher.publish_results(race.id, publish_type='manual', published_by='admin'):
                    published_count += 1
                else:
                    errors.append(f"Race {race.name}: publish_results returned False")
            except Exception as e:
                errors.append(f"Race {race.name}: {str(e)}")
        
        if published_count == 0 and errors:
            return jsonify({
                'success': False,
                'message': f'Published {published_count} of {race_count} races',
                'races_published': published_count,
                'errors': errors
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Published {published_count} of {race_count} races',
            'races_published': published_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/races/<int:race_id>/qrcode')
def race_qrcode(race_id):
    """Generate QR code for race results page"""
    try:
        import qrcode
        from io import BytesIO
        
        # Get race to verify it exists
        race_manager = RaceManager()
        race = race_manager.get_race(race_id)
        if not race:
            return jsonify({'error': 'Race not found'}), 404
        
        # Generate URL for public results
        public_url = f"{get_config_manager().get('results_publish_url', 'http://localhost:5002')}/race/{race_id}"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(public_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return Response(img_io.getvalue(), mimetype='image/png')
        
    except ImportError:
        return jsonify({'error': 'QR code library not installed. Run: pip install qrcode[pil]'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<int:event_id>/qrcode')
def event_qrcode(event_id):
    """Generate QR code for event results page"""
    try:
        import qrcode
        from io import BytesIO
        
        # Get event to verify it exists
        event_manager = EventManager()
        event = event_manager.get_event(event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Generate URL for public results
        public_url = f"{get_config_manager().get('results_publish_url', 'http://localhost:5002')}/event/{event_id}"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(public_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return Response(img_io.getvalue(), mimetype='image/png')
        
    except ImportError:
        return jsonify({'error': 'QR code library not installed. Run: pip install qrcode[pil]'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

@app.route('/system-config')
def system_config_page():
    """System configuration page"""
    return render_template('system_config.html')


@app.route('/api/system-config', methods=['GET'])
def get_system_config():
    """Get all system configuration"""
    try:
        config_mgr = get_config_manager()
        configs = config_mgr.get_all()
        
        # Convert to simple key-value dict for frontend
        config_dict = {}
        for config in configs:
            # Don't send actual sensitive values, frontend will show masked
            config_dict[config['key']] = config['value']
        
        return jsonify(config_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system-config', methods=['POST'])
def update_system_config():
    """Update system configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        config_mgr = get_config_manager()
        result = config_mgr.update_multiple(data, updated_by='admin')
        
        if result['errors']:
            return jsonify({
                'success': False,
                'message': f"Updated {result['success']} of {result['total']} settings",
                'errors': result['errors']
            }), 400
        
        return jsonify({
            'success': True,
            'message': f"Successfully updated {result['success']} settings"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system-config/test-database', methods=['POST'])
def test_database_connection():
    """Test database connection with current settings"""
    try:
        config_mgr = get_config_manager()
        
        # Get database settings
        db_host = config_mgr.get('db_host', 'localhost')
        db_port = config_mgr.get_int('db_port', 5432)
        db_name = config_mgr.get('db_name', 'race_timing')
        db_user = config_mgr.get('db_user', 'postgres')
        db_password = config_mgr.get('db_password', '')
        
        # Try to connect
        import psycopg2
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=5
        )
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Database connection successful'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/system-config/test-webhook', methods=['POST'])
def test_webhook_connection():
    """Test webhook connection to results site"""
    try:
        config_mgr = get_config_manager()
        
        # Get webhook settings
        webhook_url = config_mgr.get('results_publish_url', 'http://localhost:5002')
        webhook_secret = config_mgr.get('webhook_secret', '')
        timeout = config_mgr.get_int('webhook_timeout', 10)
        
        # Test ping endpoint
        ping_url = f"{webhook_url}/ping"
        response = requests.get(ping_url, timeout=timeout)
        response.raise_for_status()
        
        return jsonify({
            'success': True,
            'message': 'Webhook connection successful',
            'response': response.json()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/system-config/reset/<category>', methods=['POST'])
def reset_config_category(category):
    """Reset configuration category to defaults"""
    try:
        config_mgr = get_config_manager()
        count = config_mgr.reset_to_defaults(category)
        
        return jsonify({
            'success': True,
            'message': f'Reset {count} settings to defaults'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SETUP WIZARD
# ============================================================================

def check_database_configured():
    """Check if database is properly configured and accessible"""
    try:
        config_mgr = get_config_manager()
        
        # Check if we have database configuration
        db_host = config_mgr.get('db_host')
        db_name = config_mgr.get('db_name')
        db_user = config_mgr.get('db_user')
        
        if not all([db_host, db_name, db_user]):
            return False
        
        # Try to connect to database
        import psycopg2
        db_port = config_mgr.get_int('db_port', 5432)
        db_password = config_mgr.get('db_password', '')
        
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=3
        )
        conn.close()
        return True
    except Exception:
        return False


@app.before_request
def check_setup():
    """Redirect to setup wizard if database is not configured"""
    # Skip check for setup wizard, static files, and API endpoints
    if (request.path.startswith('/setup') or
        request.path.startswith('/static') or
        request.path.startswith('/api/')):
        return None
    
    # Check if database is configured
    if not check_database_configured():
        # Check if this is already the setup page
        if request.path != '/setup':
            return redirect('/setup')
    
    return None


@app.route('/setup')
def setup_wizard():
    """Setup wizard page"""
    return render_template('setup_wizard.html')


@app.route('/api/setup/database', methods=['POST'])
def setup_database():
    """Save database configuration during setup"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required = ['db_host', 'db_port', 'db_name', 'db_user', 'db_password']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        config_mgr = get_config_manager()
        
        # Save database configuration
        config_mgr.set('db_host', data['db_host'], 'setup_wizard')
        config_mgr.set('db_port', data['db_port'], 'setup_wizard')
        config_mgr.set('db_name', data['db_name'], 'setup_wizard')
        config_mgr.set('db_user', data['db_user'], 'setup_wizard')
        config_mgr.set('db_password', data['db_password'], 'setup_wizard')
        
        return jsonify({
            'success': True,
            'message': 'Database configuration saved'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/setup/webhook', methods=['POST'])
def setup_webhook():
    """Save webhook configuration during setup"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        config_mgr = get_config_manager()
        
        # Save webhook configuration
        if 'results_publish_url' in data:
            config_mgr.set('results_publish_url', data['results_publish_url'], 'setup_wizard')
        if 'webhook_secret' in data:
            config_mgr.set('webhook_secret', data['webhook_secret'], 'setup_wizard')
        if 'webhook_timeout' in data:
            config_mgr.set('webhook_timeout', data['webhook_timeout'], 'setup_wizard')
        if 'webhook_retry_attempts' in data:
            config_mgr.set('webhook_retry_attempts', data['webhook_retry_attempts'], 'setup_wizard')
        
        return jsonify({
            'success': True,
            'message': 'Webhook configuration saved'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/setup/status', methods=['GET'])
def setup_status():
    """Check setup status"""
    try:
        db_configured = check_database_configured()
        
        return jsonify({
            'database_configured': db_configured,
            'setup_required': not db_configured
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Register shutdown handlers
    atexit.register(shutdown_llrp_stations)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("Race Timing System Starting")
    print("="*60)
    print(f"Main timing system: http://localhost:5001")
    print(f"Results publishing site: {RESULTS_PUBLISH_URL}")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
