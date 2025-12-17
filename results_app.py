"""
Results Publishing Site - Public-facing Flask application
Receives and displays race results from the main timing system
"""
from flask import Flask, render_template, jsonify, request
from results_database import get_session, init_db
from results_models import PublishedEvent, PublishedRace, PublishedResult, PublishingLog
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'results-publishing-secret-key'

# Initialize database
init_db()


# ============================================================================
# API ENDPOINTS - Receive results from main system
# ============================================================================

@app.route('/api/receive-results', methods=['POST'])
def receive_results():
    """Receive and store published results from main timing system"""
    session = get_session()
    try:
        data = request.json
        race_data = data.get('race', {})
        results_data = data.get('results', [])
        publish_type = data.get('publish_type', 'manual')
        
        if not race_data or 'source_race_id' not in race_data:
            return jsonify({'error': 'Invalid race data'}), 400
        
        # Find or create race
        race = session.query(PublishedRace).filter_by(
            source_race_id=race_data['source_race_id']
        ).first()
        
        if not race:
            race = PublishedRace(
                source_race_id=race_data['source_race_id'],
                name=race_data.get('name', 'Unknown Race'),
                race_type=race_data.get('race_type'),
                date=datetime.fromisoformat(race_data['date']) if race_data.get('date') else datetime.utcnow(),
                published_at=datetime.utcnow()
            )
            session.add(race)
            session.flush()  # Get race.id
        
        # Update race details
        race.last_updated = datetime.utcnow()
        race.name = race_data.get('name', race.name)
        race.race_type = race_data.get('race_type', race.race_type)
        
        if race_data.get('start_time'):
            race.start_time = datetime.fromisoformat(race_data['start_time'])
        if race_data.get('finish_time'):
            race.finish_time = datetime.fromisoformat(race_data['finish_time'])
        
        # Handle event association
        if race_data.get('event_id'):
            event_data = data.get('event', {})
            if event_data:
                event = session.query(PublishedEvent).filter_by(
                    source_event_id=event_data['source_event_id']
                ).first()
                
                if not event:
                    event = PublishedEvent(
                        source_event_id=event_data['source_event_id'],
                        name=event_data.get('name', 'Unknown Event'),
                        date=datetime.fromisoformat(event_data['date']) if event_data.get('date') else datetime.utcnow(),
                        location=event_data.get('location'),
                        description=event_data.get('description')
                    )
                    session.add(event)
                    session.flush()
                
                race.event_id = event.id
        
        # Delete old results for this race
        session.query(PublishedResult).filter_by(race_id=race.id).delete()
        
        # Add new results
        for result_data in results_data:
            result = PublishedResult(
                race_id=race.id,
                bib_number=result_data.get('bib_number'),
                participant_name=result_data.get('participant_name', 'Unknown'),
                gender=result_data.get('gender'),
                age=result_data.get('age'),
                category=result_data.get('category'),
                status=result_data.get('status', 'registered'),
                overall_rank=result_data.get('overall_rank'),
                category_rank=result_data.get('category_rank'),
                gender_rank=result_data.get('gender_rank'),
                finish_time=datetime.fromisoformat(result_data['finish_time']) if result_data.get('finish_time') else None,
                total_time_seconds=result_data.get('total_time_seconds'),
                split_times=result_data.get('split_times'),
                published_at=datetime.utcnow()
            )
            session.add(result)
        
        # Log the publishing action
        log_entry = PublishingLog(
            race_id=race.id,
            result_count=len(results_data),
            publish_type=publish_type,
            published_by=data.get('published_by', 'system')
        )
        session.add(log_entry)
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Results received successfully',
            'race_id': race.id,
            'result_count': len(results_data)
        })
        
    except Exception as e:
        session.rollback()
        print(f"Error receiving results: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/race/<int:race_id>/results')
def get_race_results_api(race_id):
    """API endpoint for live results (for AJAX updates)"""
    session = get_session()
    try:
        race = session.query(PublishedRace).get(race_id)
        if not race:
            return jsonify({'error': 'Race not found'}), 404
        
        results = session.query(PublishedResult).filter_by(
            race_id=race_id
        ).order_by(PublishedResult.overall_rank).all()
        
        return jsonify({
            'race': {
                'id': race.id,
                'name': race.name,
                'status': 'finished' if race.finish_time else ('active' if race.start_time else 'not_started')
            },
            'results': [
                {
                    'bib': r.bib_number,
                    'name': r.participant_name,
                    'gender': r.gender,
                    'age': r.age,
                    'category': r.category,
                    'status': r.status,
                    'overall_rank': r.overall_rank,
                    'category_rank': r.category_rank,
                    'gender_rank': r.gender_rank,
                    'time_seconds': r.total_time_seconds,
                    'splits': r.split_times if r.split_times else {}
                }
                for r in results
            ],
            'last_updated': race.last_updated.isoformat() if race.last_updated else None,
            'result_count': len(results)
        })
    finally:
        session.close()


# ============================================================================
# PUBLIC PAGES
# ============================================================================

@app.route('/')
def index():
    """Home page with event listings and search"""
    session = get_session()
    try:
        query = request.args.get('q', '').strip()
        
        # Base queries
        events_query = session.query(PublishedEvent).filter_by(is_live=True)
        races_query = session.query(PublishedRace).filter_by(event_id=None)
        
        if query:
            # Filter events by name or location
            search_term = f"%{query}%"
            events_query = events_query.filter(
                (PublishedEvent.name.ilike(search_term)) | 
                (PublishedEvent.location.ilike(search_term))
            )
            
            # Filter races by name
            races_query = races_query.filter(PublishedRace.name.ilike(search_term))
        
        # Execute queries
        events = events_query.order_by(PublishedEvent.date.desc()).limit(20).all()
        standalone_races = races_query.order_by(PublishedRace.date.desc()).limit(10).all()
        
        return render_template('public/index.html', 
                             events=events, 
                             standalone_races=standalone_races,
                             search_query=query)
    finally:
        session.close()


@app.route('/event/<int:event_id>')
def event_results(event_id):
    """Event results page"""
    session = get_session()
    try:
        event = session.query(PublishedEvent).get(event_id)
        if not event:
            return "Event not found", 404
        
        races = session.query(PublishedRace).filter_by(
            event_id=event_id
        ).order_by(PublishedRace.date).all()
        
        return render_template('public/event.html', event=event, races=races)
    finally:
        session.close()


@app.route('/race/<int:race_id>')
def race_results(race_id):
    """Live race results page"""
    session = get_session()
    try:
        race = session.query(PublishedRace).get(race_id)
        if not race:
            return "Race not found", 404
        
        results = session.query(PublishedResult).filter_by(
            race_id=race_id
        ).order_by(PublishedResult.overall_rank).all()
        
        # Determine race status
        if race.finish_time:
            status = 'finished'
        elif race.start_time:
            status = 'active'
        else:
            status = 'not_started'
        
        return render_template('public/race_results.html', 
                             race=race, 
                             results=results,
                             status=status)
    finally:
        session.close()


# ============================================================================
# TEMPLATE FILTERS
# ============================================================================

@app.template_filter('format_time')
def format_time(seconds):
    """Format seconds as HH:MM:SS"""
    if not seconds:
        return '-'
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


@app.template_filter('format_date')
def format_date(dt):
    """Format datetime for display"""
    if not dt:
        return '-'
    return dt.strftime('%B %d, %Y')


@app.template_filter('format_datetime')
def format_datetime(dt):
    """Format datetime with time"""
    if not dt:
        return '-'
    return dt.strftime('%B %d, %Y at %I:%M %p')



if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)