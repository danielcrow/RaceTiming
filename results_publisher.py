"""
Results Publisher - Publishes race results to the public results site via webhooks
"""
import requests
import os
from datetime import datetime
from database import get_session
from models import Race, Event
from race_control import RaceControl


class ResultsPublisher:
    """Publishes race results to the public results site"""
    
    def __init__(self):
        self.results_site_url = os.getenv('RESULTS_PUBLISH_URL', 'http://localhost:5002')
        self.webhook_secret = os.getenv('WEBHOOK_SECRET', 'change-this-secret-key')
    
    def _make_webhook_request(self, endpoint, data):
        """Make an authenticated webhook request"""
        url = f"{self.results_site_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Secret': self.webhook_secret
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error publishing to {endpoint}: {e}")
            return None
    
    def publish_event(self, event_id):
        """Publish an event to the results site"""
        session = get_session()
        try:
            event = session.query(Event).filter_by(id=event_id).first()
            if not event:
                print(f"Event {event_id} not found")
                return False
            
            data = {
                'event_id': event.id,
                'name': event.name,
                'date': event.date.isoformat() if event.date else None,
                'location': event.location,
                'description': event.description
            }
           
            result = self._make_webhook_request('/webhook/publish-event', data)
            if result and result.get('success'):
                print(f"✓ Published event: {event.name}")
                return True
            return False
        finally:
            session.close()
    
    def publish_race(self, race_id):
        """Publish a race to the results site"""
        session = get_session()
        try:
            race = session.query(Race).filter_by(id=race_id).first()
            if not race:
                print(f"Race {race_id} not found")
                return False
            
            data = {
                'race_id': race.id,
                'event_id': race.event_id,
                'name': race.name,
                'race_type': race.race_type.value if race.race_type else None,
                'date': race.date.isoformat() if race.date else None,
                'start_time': race.start_time.isoformat() if race.start_time else None,
                'finish_time': race.finish_time.isoformat() if race.finish_time else None
            }
            
            # Publish event first if it exists
            if race.event_id:
                self.publish_event(race.event_id)
            
            result = self._make_webhook_request('/webhook/publish-race', data)
            if result and result.get('success'):
                print(f"✓ Published race: {race.name}")
                return True
            return False
        finally:
            session.close()
    
    def publish_results(self, race_id, publish_type='manual', published_by='admin'):
        """Publish race results to the results site"""
        session = get_session()
        try:
            race = session.query(Race).filter_by(id=race_id).first()
            if not race:
                print(f"Race {race_id} not found")
                return False
            
            # Ensure race is published first
            self.publish_race(race_id)
            
            # Get live results using RaceControl
            race_control = RaceControl(race_id)
            results = race_control.get_live_results()
            
            # Format results for publishing
            formatted_results = []
            for result in results:
                # Handle both dict and object results
                if hasattr(result, 'bib_number'):
                    # It's an object
                    formatted_results.append({
                        'bib_number': result.bib_number,
                        'participant_name': result.participant.full_name if result.participant else 'Unknown',
                        'gender': result.participant.gender if result.participant else None,
                        'age': result.participant.age if result.participant else None,
                        'category': result.category if hasattr(result, 'category') else None,
                        'status': result.status.value if hasattr(result, 'status') and hasattr(result.status, 'value') else str(result.status) if hasattr(result, 'status') else None,
                        'overall_rank': result.overall_rank if hasattr(result, 'overall_rank') else None,
                        'category_rank': result.category_rank if hasattr(result, 'category_rank') else None,
                        'gender_rank': result.gender_rank if hasattr(result, 'gender_rank') else None,
                        'finish_time': result.finish_time.isoformat() if hasattr(result, 'finish_time') and result.finish_time else None,
                        'total_time_seconds': result.total_time if hasattr(result, 'total_time') else None,
                        'split_times': result.split_times if hasattr(result, 'split_times') else []
                    })
                else:
                    # It's a dict
                    formatted_results.append({
                        'bib_number': result.get('bib_number'),
                        'participant_name': result.get('participant_name'),
                        'gender': result.get('gender'),
                        'age': result.get('age'),
                        'category': result.get('category'),
                        'status': result.get('status'),
                        'overall_rank': result.get('overall_rank'),
                        'category_rank': result.get('category_rank'),
                        'gender_rank': result.get('gender_rank'),
                        'finish_time': result.get('finish_time'),
                        'total_time_seconds': result.get('total_time_seconds'),
                        'split_times': result.get('split_times', [])
                    })
            
            data = {
                'race_id': race_id,
                'results': formatted_results,
                'publish_type': publish_type,
                'published_by': published_by
            }
            
            result = self._make_webhook_request('/webhook/publish-results', data)
            if result and result.get('success'):
                print(f"✓ Published {len(formatted_results)} results for race: {race.name}")
                return True
            return False
        finally:
            session.close()
    
    def test_connection(self):
        """Test connection to the results site"""
        try:
            response = requests.get(f"{self.results_site_url}/ping", timeout=5)
            if response.status_code == 200:
                print(f"✓ Results site is reachable at {self.results_site_url}")
                return True
            else:
                print(f"✗ Results site returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Cannot reach results site: {e}")
            return False


if __name__ == '__main__':
    # Test the publisher
    publisher = ResultsPublisher()
    
    print("Testing connection to results site...")
    if publisher.test_connection():
        print("\nPublisher is ready to use!")
        print(f"Results site URL: {publisher.results_site_url}")
    else:
        print("\nPublisher cannot connect to results site.")
        print("Make sure the results site is running and RESULTS_PUBLISH_URL is set correctly.")

# Made with Bob
