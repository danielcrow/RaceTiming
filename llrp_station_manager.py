"""
LLRP Station Manager
Manages LLRP RFID reader stations
"""
from database import get_session
from models import LLRPStation
from datetime import datetime


class LLRPStationManager:
    """Manages LLRP station creation and configuration"""
    
    def __init__(self):
        self.session = get_session()
    
    def create_station(self, name, reader_ip, reader_port=5084, cooldown_seconds=5):
        """Create a new LLRP station"""
        station = LLRPStation(
            name=name,
            reader_ip=reader_ip,
            reader_port=reader_port,
            cooldown_seconds=cooldown_seconds
        )
        
        self.session.add(station)
        self.session.commit()
        return station
    
    def get_station(self, station_id):
        """Get a station by ID"""
        return self.session.query(LLRPStation).filter(LLRPStation.id == station_id).first()
    
    def get_station_by_name(self, name):
        """Get a station by name"""
        return self.session.query(LLRPStation).filter(LLRPStation.name == name).first()
    
    def list_stations(self):
        """List all stations"""
        return self.session.query(LLRPStation).order_by(LLRPStation.name).all()
    
    def update_station(self, station_id, **kwargs):
        """Update a station's configuration"""
        station = self.get_station(station_id)
        if not station:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'name', 'reader_ip', 'reader_port', 'cooldown_seconds'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(station, field, value)
        
        self.session.commit()
        return station
    
    def delete_station(self, station_id):
        """Delete a station"""
        station = self.get_station(station_id)
        if station:
            self.session.delete(station)
            self.session.commit()
            return True
        return False
    
    def get_station_config(self, station_id):
        """Get station configuration as a dictionary for reader service"""
        station = self.get_station(station_id)
        if not station:
            return None
        
        return {
            'station_id': station.id,
            'station_name': station.name,
            'reader_ip': station.reader_ip,
            'reader_port': station.reader_port,
            'cooldown_seconds': station.cooldown_seconds
        }
    
    def update_station_status(self, station_id, is_active, last_connected=None):
        """Update station status"""
        station = self.get_station(station_id)
        if station:
            station.is_active = is_active
            if last_connected:
                station.last_connected = last_connected
            elif is_active:
                station.last_connected = datetime.utcnow()
            self.session.commit()
            return True
        return False
