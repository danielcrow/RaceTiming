"""
Standalone results site with local database storage and webhook support.
Receives published results from the main Race Timing system via webhooks.
"""
from flask import Flask, render_template, jsonify, request, abort
import json
import os
from datetime import datetime
from results_database import get_session, init_db
from results_models import PublishedEvent, PublishedRace, PublishedResult, PublishingLog

app = Flask(__name__)

# Webhook authentication token (set via environment variable)
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'change-this-secret-key')

# Initialize database on startup
init_db()

# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def verify_webhook_secret(request):
    """Verify webhook request is authenticated"""
    auth_header = request.headers.get('X-Webhook-Secret')
    return auth_header == WEBHOOK_SECRET


def get_published_races():
    """Get all published races with event info"""
    session = get_session()
    try:
        races = session.query(PublishedRace).all()
        return [{
            'id': r.source_race_id,
            'name': r.name,
            'race_type': r.race_type,
            'date': r.date.isoformat() if r.date else None,  # type: ignore[union-attr]
            'start_time': r.start_time.isoformat() if r.start_time else None,  # type: ignore[union-attr]
            'finish_time': r.finish_time.isoformat() if r.finish_time else None,  # type: ignore[union-attr]
            'event_id': r.event.source_event_id if r.event else None,
            'event_name': r.event.name if r.event else None,
            'location': r.event.location if r.event else '',
            'participant_count': len(r.results),
            'last_updated': r.last_updated.isoformat() if r.last_updated else None  # type: ignore[union-attr]
        } for r in races]
    finally:
        session.close()


def get_published_events():
    """Get all published events"""
    session = get_session()
    try:
        events = session.query(PublishedEvent).all()
        return [{
            'id': e.source_event_id,
            'name': e.name,
            'date': e.date.isoformat() if e.date else None,  # type: ignore[union-attr]
            'location': e.location,
            'description': e.description,
            'race_count': len(e.races),
            'is_live': e.is_live
        } for e in events]
    finally:
        session.close()


def get_race_results(race_id):
    """Get results for a specific race"""
    session = get_session()
    try:
        race = session.query(PublishedRace).filter_by(source_race_id=race_id).first()
        if not race:
            return []
        
        results = session.query(PublishedResult).filter_by(race_id=race.id).all()
        return [{
            'bib_number': r.bib_number,
            'participant_name': r.participant_name,
            'gender': r.gender,
            'age': r.age,
            'category': r.category,
            'status': r.status,
            'overall_rank': r.overall_rank,
            'category_rank': r.category_rank,
            'gender_rank': r.gender_rank,
            'finish_time': r.finish_time.isoformat() if r.finish_time else None,  # type: ignore[union-attr]
            'total_time_seconds': r.total_time_seconds,
            'split_times': json.loads(str(r.split_times)) if r.split_times is not None else []
        } for r in results]
    finally:
        session.close()


# ------------------------------------------------------------------
# Public Pages
# ------------------------------------------------------------------

@app.route('/')
def index():
    """Home page with race list and search"""
    try:
        races = get_published_races()
        events = get_published_events()
        
        # Get search query if provided
        search_query = request.args.get('q', '').lower()
        
        # Filter races if search query exists
        if search_query:
            races = [r for r in races if
                    search_query in r.get('name', '').lower() or
                    search_query in r.get('event_name', '').lower() or
                    search_query in r.get('location', '').lower()]
        
        return render_template('index.html', races=races, events=events, search_query=search_query)
    except Exception as e:
        print(f"Error fetching races: {e}")
        return render_template('index.html', races=[], events=[], search_query='', error=str(e))


@app.route('/results/<int:race_id>')
def results_page(race_id):
    """Results page for a specific race"""
    session = get_session()
    try:
        race = session.query(PublishedRace).filter_by(source_race_id=race_id).first()
        if not race:
            abort(404)
        
        race_data = {
            'id': race.source_race_id,
            'name': race.name,
            'race_type': race.race_type,
            'date': race.date.isoformat() if race.date else None,  # type: ignore[union-attr]
            'start_time': race.start_time.isoformat() if race.start_time else None,  # type: ignore[union-attr]
            'event_name': race.event.name if race.event else None
        }
        
        initial_results = get_race_results(race_id)
        return render_template('results.html', race=race_data, results=initial_results, race_id=race_id)
    finally:
        session.close()


@app.route('/api/results/<int:race_id>')
def api_results(race_id):
    """JSON endpoint for polling race results (used by results.html)"""
    results = get_race_results(race_id)
    return jsonify(results)


# ------------------------------------------------------------------
# Webhook Endpoints (for receiving published results)
# ------------------------------------------------------------------

@app.route('/webhook/publish-event', methods=['POST'])
def webhook_publish_event():
    """Receive published event data"""
    if not verify_webhook_secret(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    if 'event_id' not in data or 'name' not in data:
        return jsonify({'error': 'Missing required fields: event_id, name'}), 400
    
    session = get_session()
    try:
        # Check if event already exists
        event = session.query(PublishedEvent).filter_by(
            source_event_id=data['event_id']
        ).first()
        
        if event:
            # Update existing event
            event.name = data['name']
            if data.get('date'):
                event.date = datetime.fromisoformat(data['date'])  # type: ignore[assignment]
            event.location = data.get('location')
            event.description = data.get('description')
            event.last_updated = datetime.utcnow()  # type: ignore[assignment]
        else:
            # Create new event - date is required
            if not data.get('date'):
                return jsonify({'error': 'Event date is required'}), 400
            
            event = PublishedEvent(
                source_event_id=data['event_id'],
                name=data['name'],
                date=datetime.fromisoformat(data['date']),
                location=data.get('location'),
                description=data.get('description')
            )
            session.add(event)
        
        session.commit()
        return jsonify({'success': True, 'message': 'Event published successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@app.route('/webhook/publish-race', methods=['POST'])
def webhook_publish_race():
    """Receive published race data"""
    if not verify_webhook_secret(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    if 'race_id' not in data or 'name' not in data:
        return jsonify({'error': 'Missing required fields: race_id, name'}), 400
    
    session = get_session()
    try:
        # Check if race already exists
        race = session.query(PublishedRace).filter_by(
            source_race_id=data['race_id']
        ).first()
        
        # Get event if provided
        event = None
        if data.get('event_id'):
            event = session.query(PublishedEvent).filter_by(
                source_event_id=data['event_id']
            ).first()
        
        if race:
            # Update existing race
            race.name = data['name']
            race.race_type = data.get('race_type')
            race.date = datetime.fromisoformat(data['date']) if data.get('date') else None  # type: ignore[assignment]
            race.start_time = datetime.fromisoformat(data['start_time']) if data.get('start_time') else None  # type: ignore[assignment]
            race.finish_time = datetime.fromisoformat(data['finish_time']) if data.get('finish_time') else None  # type: ignore[assignment]
            race.event_id = event.id if event else None  # type: ignore[assignment]
            race.last_updated = datetime.utcnow()  # type: ignore[assignment]
        else:
            # Create new race
            race = PublishedRace(
                source_race_id=data['race_id'],
                event_id=event.id if event else None,
                name=data['name'],
                race_type=data.get('race_type'),
                date=datetime.fromisoformat(data['date']) if data.get('date') else None,
                start_time=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None,
                finish_time=datetime.fromisoformat(data['finish_time']) if data.get('finish_time') else None
            )
            session.add(race)
        
        session.commit()
        return jsonify({'success': True, 'message': 'Race published successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@app.route('/webhook/publish-results', methods=['POST'])
def webhook_publish_results():
    """Receive published race results"""
    if not verify_webhook_secret(request):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    if 'race_id' not in data or 'results' not in data:
        return jsonify({'error': 'Missing required fields: race_id, results'}), 400
    
    race_id = data['race_id']
    results_data = data['results']
    
    if not isinstance(results_data, list):
        return jsonify({'error': 'Results must be a list'}), 400
    
    session = get_session()
    try:
        # Find the race
        race = session.query(PublishedRace).filter_by(source_race_id=race_id).first()
        if not race:
            return jsonify({'success': False, 'error': 'Race not found'}), 404
        
        # Clear existing results for this race
        session.query(PublishedResult).filter_by(race_id=race.id).delete()
        
        # Add new results
        for result_data in results_data:
            result = PublishedResult(
                race_id=race.id,
                bib_number=result_data.get('bib_number'),
                participant_name=result_data['participant_name'],
                gender=result_data.get('gender'),
                age=result_data.get('age'),
                category=result_data.get('category'),
                status=result_data.get('status'),
                overall_rank=result_data.get('overall_rank'),
                category_rank=result_data.get('category_rank'),
                gender_rank=result_data.get('gender_rank'),
                finish_time=datetime.fromisoformat(result_data['finish_time']) if result_data.get('finish_time') else None,
                total_time_seconds=result_data.get('total_time_seconds'),
                split_times=json.dumps(result_data.get('split_times', []))
            )
            session.add(result)
        
        # Update race last_updated timestamp
        # Mark the race as modified to trigger onupdate
        race.last_updated = datetime.utcnow()  # type: ignore[assignment]
        
        # Log the publishing action
        log = PublishingLog(
            race_id=race.id,
            result_count=len(results_data),
            publish_type=data.get('publish_type', 'webhook'),
            published_by=data.get('published_by', 'system')
        )
        session.add(log)
        
        session.commit()
        return jsonify({
            'success': True,
            'message': f'Published {len(results_data)} results successfully'
        })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------

@app.route('/ping')
def ping():
    """Health check endpoint"""
    session = get_session()
    try:
        # Test database connection
        race_count = session.query(PublishedRace).count()
        event_count = session.query(PublishedEvent).count()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'stats': {
                'races': race_count,
                'events': event_count
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('index.html',
                         races=[],
                         events=[],
                         search_query='',
                         error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('index.html',
                         races=[],
                         events=[],
                         search_query='',
                         error='Internal server error. Please try again later.'), 500


if __name__ == '__main__':
    # Run on a different port so it can coexist with the main app
    app.run(host='0.0.0.0', port=5002, debug=True)
