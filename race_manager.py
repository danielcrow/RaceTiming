"""
Race and Participant Management
"""
from datetime import datetime
from models import Race, RaceLeg, Participant, TimingPoint, RaceType, LegType, race_participants, Event
from database import get_session
from sqlalchemy import and_


class EventManager:
    """Manages event creation and configuration"""
    
    def __init__(self):
        self.session = get_session()
    
    def create_event(self, name, date, location=None, description=None):
        """Create a new event"""
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        
        event = Event(
            name=name,
            date=date,
            location=location,
            description=description
        )
        
        self.session.add(event)
        self.session.commit()
        return event
    
    def get_event(self, event_id):
        """Get an event by ID"""
        return self.session.query(Event).filter(Event.id == event_id).first()
    
    def list_events(self):
        """List all events"""
        return self.session.query(Event).order_by(Event.date.desc()).all()
    
    def delete_event(self, event_id):
        """Delete an event"""
        event = self.get_event(event_id)
        if event:
            self.session.delete(event)
            self.session.commit()
            return True
        return False


class RaceManager:
    """Manages race creation and configuration"""
    
    def __init__(self):
        self.session = get_session()
    
    def create_race(self, name, race_type, date, location=None, description=None, event_id=None, start_mode="mass_start"):
        """Create a new race"""
        if isinstance(race_type, str):
            race_type = RaceType[race_type.upper()]
        
        if isinstance(start_mode, str):
            from models import StartMode
            try:
                start_mode = StartMode(start_mode)
            except ValueError:
                start_mode = StartMode.MASS_START
        
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        
        race = Race(
            name=name,
            race_type=race_type,
            date=date,
            location=location,
            description=description,
            event_id=event_id,
            start_mode=start_mode
        )
        
        self.session.add(race)
        self.session.commit()
        
        # Auto-create standard legs based on race type
        self._create_standard_legs(race)
        
        return race
    
    def _create_standard_legs(self, race):
        """Create standard legs for a race type"""
        legs_config = {
            RaceType.TRIATHLON: [
                ("Swim", LegType.SWIM),
                ("T1", LegType.TRANSITION),
                ("Bike", LegType.BIKE),
                ("T2", LegType.TRANSITION),
                ("Run", LegType.RUN)
            ],
            RaceType.DUATHLON: [
                ("Run 1", LegType.RUN),
                ("T1", LegType.TRANSITION),
                ("Bike", LegType.BIKE),
                ("T2", LegType.TRANSITION),
                ("Run 2", LegType.RUN)
            ],
            RaceType.AQUATHLON: [
                ("Swim", LegType.SWIM),
                ("T1", LegType.TRANSITION),
                ("Run", LegType.RUN)
            ],
            RaceType.RUNNING: [
                ("Run", LegType.RUN)
            ],
            RaceType.CYCLING: [
                ("Bike", LegType.BIKE)
            ]
        }
        
        legs = legs_config.get(race.race_type, [])
        for order, (name, leg_type) in enumerate(legs, 1):
            self.add_leg(race.id, name, leg_type, order)
        
        # Create basic timing points
        self.add_timing_point(race.id, "Start", 1, is_start=True)
        self.add_timing_point(race.id, "Finish", 99, is_finish=True)
    
    def add_leg(self, race_id, name, leg_type, order, distance=None):
        """Add a leg to a race"""
        if isinstance(leg_type, str):
            leg_type = LegType[leg_type.upper()]
        
        leg = RaceLeg(
            race_id=race_id,
            name=name,
            leg_type=leg_type,
            order=order,
            distance=distance
        )
        
        self.session.add(leg)
        self.session.commit()
        return leg
    
    def add_timing_point(self, race_id, name, order, is_start=False, is_finish=False, leg_id=None, llrp_station_id=None):
        """Add a timing point to a race"""
        timing_point = TimingPoint(
            race_id=race_id,
            name=name,
            order=order,
            is_start=is_start,
            is_finish=is_finish,
            leg_id=leg_id,
            llrp_station_id=llrp_station_id
        )
        
        self.session.add(timing_point)
        self.session.commit()
        return timing_point
    
    def get_race(self, race_id):
        """Get a race by ID"""
        return self.session.query(Race).filter(Race.id == race_id).first()
    
    def get_race_by_name(self, name):
        """Get a race by name"""
        return self.session.query(Race).filter(Race.name == name).first()
    
    def list_races(self):
        """List all races"""
        return self.session.query(Race).order_by(Race.date.desc()).all()
    
    def delete_race(self, race_id):
        """Delete a race"""
        race = self.get_race(race_id)
        if race:
            self.session.delete(race)
            self.session.commit()
            return True
        return False

    def delete_timing_point(self, timing_point_id):
        """Delete a timing point"""
        tp = self.session.query(TimingPoint).filter(TimingPoint.id == timing_point_id).first()
        if tp:
            self.session.delete(tp)
            self.session.commit()
            return True
        return False

    def update_race_age_groups(self, race_id, age_groups_json):
        """Update race age groups"""
        race = self.session.query(Race).get(race_id)
        if not race:
            return False
        race.age_groups = age_groups_json
        self.session.commit()
        return True
    
    def update_race_event(self, race_id, event_id):
        """Update a race's event assignment"""
        race = self.session.query(Race).get(race_id)
        if not race:
            return False
        
        # Validate event exists if event_id is provided
        if event_id is not None:
            event = self.session.query(Event).get(event_id)
            if not event:
                raise ValueError(f"Event {event_id} not found")
        
        race.event_id = event_id
        self.session.commit()
        return True


class ParticipantManager:
    """Manages participants"""
    
    def __init__(self):
        self.session = get_session()
    
    def create_participant(self, first_name, last_name, email=None, phone=None, 
                          gender=None, age=None, rfid_tag=None):
        """Create a new participant"""
        participant = Participant(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            gender=gender,
            age=age,
            rfid_tag=rfid_tag
        )
        
        self.session.add(participant)
        self.session.commit()
        return participant
    
    def register_participant(self, race_id, participant_id, bib_number, category="Open"):
        """Register a participant for a race"""
        # Insert into association table
        stmt = race_participants.insert().values(
            race_id=race_id,
            participant_id=participant_id,
            bib_number=bib_number,
            category=category
        )
        self.session.execute(stmt)
        self.session.commit()
    
    def get_participant(self, participant_id):
        """Get a participant by ID"""
        return self.session.query(Participant).filter(Participant.id == participant_id).first()
    
    def get_participant_by_rfid(self, rfid_tag):
        """Get a participant by RFID tag"""
        return self.session.query(Participant).filter(Participant.rfid_tag == rfid_tag).first()
    
    def get_participant_by_bib(self, race_id, bib_number):
        """Get a participant by bib number for a specific race"""
        # Convert bib_number to string since the column is VARCHAR
        bib_str = str(bib_number)
        result = self.session.query(Participant).join(
            race_participants,
            Participant.id == race_participants.c.participant_id
        ).filter(
            and_(
                race_participants.c.race_id == race_id,
                race_participants.c.bib_number == bib_str
            )
        ).first()
        return result
    
    def list_participants(self, race_id=None):
        """List all participants, optionally filtered by race"""
        if race_id:
            return self.session.query(Participant).join(
                race_participants,
                Participant.id == race_participants.c.participant_id
            ).filter(race_participants.c.race_id == race_id).all()
        else:
            return self.session.query(Participant).all()
    
    def update_rfid_tag(self, participant_id, rfid_tag):
        """Update a participant's RFID tag"""
        participant = self.get_participant(participant_id)
        if participant:
            participant.rfid_tag = rfid_tag
            self.session.commit()
            return True
        return False
    
    def update_participant(self, participant_id, **kwargs):
        """Update participant information"""
        participant = self.get_participant(participant_id)
        if not participant:
            return False
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'gender', 'age', 'rfid_tag']
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(participant, field, value)
        
        self.session.commit()
        return True
    
    def delete_participant(self, participant_id):
        """Delete a participant"""
        participant = self.get_participant(participant_id)
        if participant:
            self.session.delete(participant)
            self.session.commit()
            return True
        return False


def get_age_group(age, gender=None):
    """
    Get age group category for a participant
    
    Args:
        age: Participant's age
        gender: Participant's gender ('M' or 'F')
    
    Returns:
        Age group string (e.g., "Male 30-39", "Female 20-29", "Under 20")
    """
    if age is None:
        return "Unknown"
    
    # Determine age bracket
    if age < 20:
        bracket = "Under 20"
    elif age < 30:
        bracket = "20-29"
    elif age < 40:
        bracket = "30-39"
    elif age < 50:
        bracket = "40-49"
    elif age < 60:
        bracket = "50-59"
    else:
        bracket = "60+"
    
    # Add gender prefix if provided
    if gender:
        gender_prefix = "Male" if gender.upper() == 'M' else "Female" if gender.upper() == 'F' else ""
        if gender_prefix:
            return f"{gender_prefix} {bracket}"
    
    return bracket
