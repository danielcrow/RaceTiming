"""
Race and Participant Management
"""
from datetime import datetime
from models import Race, RaceLeg, Participant, TimingPoint, RaceType, LegType, race_participants, Event
from database import get_session
from sqlalchemy import and_


class EventManager:
    """Manages event creation and configuration"""

    def create_event(self, name, date, location=None, description=None):
        """Create a new event"""
        if isinstance(date, str):
            date = datetime.fromisoformat(date)

        session = get_session()
        event = Event(
            name=name,
            date=date,
            location=location,
            description=description
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event

    def get_event(self, event_id):
        """Get an event by ID"""
        return get_session().query(Event).filter(Event.id == event_id).first()

    def list_events(self):
        """List all events"""
        return get_session().query(Event).order_by(Event.date.desc()).all()

    def delete_event(self, event_id):
        """Delete an event"""
        session = get_session()
        event = session.query(Event).filter(Event.id == event_id).first()
        if event:
            session.delete(event)
            session.commit()
            return True
        return False


class RaceManager:
    """Manages race creation and configuration"""

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

        session = get_session()
        race = Race(
            name=name,
            race_type=race_type,
            date=date,
            location=location,
            description=description,
            event_id=event_id,
            start_mode=start_mode
        )

        session.add(race)
        session.commit()
        session.refresh(race)

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

        session = get_session()
        leg = RaceLeg(
            race_id=race_id,
            name=name,
            leg_type=leg_type,
            order=order,
            distance=distance
        )
        session.add(leg)
        session.commit()
        return leg

    def add_timing_point(self, race_id, name, order, is_start=False, is_finish=False, leg_id=None,
                        llrp_station_id=None, detection_mode="first_seen", detection_window_seconds=3):
        """Add a timing point to a race"""
        from models import TagDetectionMode

        # Convert string to enum if needed
        if isinstance(detection_mode, str):
            try:
                detection_mode = TagDetectionMode(detection_mode)
            except ValueError:
                detection_mode = TagDetectionMode.FIRST_SEEN

        session = get_session()
        timing_point = TimingPoint(
            race_id=race_id,
            name=name,
            order=order,
            is_start=is_start,
            is_finish=is_finish,
            leg_id=leg_id,
            llrp_station_id=llrp_station_id,
            detection_mode=detection_mode,
            detection_window_seconds=detection_window_seconds
        )
        session.add(timing_point)
        session.commit()
        return timing_point

    def get_race(self, race_id):
        """Get a race by ID"""
        return get_session().query(Race).filter(Race.id == race_id).first()

    def get_race_by_name(self, name):
        """Get a race by name"""
        return get_session().query(Race).filter(Race.name == name).first()

    def list_races(self):
        """List all races"""
        return get_session().query(Race).order_by(Race.date.desc()).all()

    def delete_race(self, race_id):
        """Delete a race"""
        session = get_session()
        race = session.query(Race).filter(Race.id == race_id).first()
        if race:
            session.delete(race)
            session.commit()
            return True
        return False

    def delete_timing_point(self, timing_point_id):
        """Delete a timing point"""
        session = get_session()
        tp = session.query(TimingPoint).filter(TimingPoint.id == timing_point_id).first()
        if tp:
            session.delete(tp)
            session.commit()
            return True
        return False

    def update_race_age_groups(self, race_id, age_groups_json):
        """Update race age groups"""
        session = get_session()
        race = session.query(Race).filter(Race.id == race_id).first()
        if not race:
            return False
        race.age_groups = age_groups_json
        session.commit()
        return True

    def update_race_event(self, race_id, event_id):
        """Update a race's event assignment"""
        session = get_session()
        race = session.query(Race).filter(Race.id == race_id).first()
        if not race:
            return False

        # Validate event exists if event_id is provided
        if event_id is not None:
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise ValueError(f"Event {event_id} not found")

        race.event_id = event_id
        session.commit()
        return True


class ParticipantManager:
    """Manages participants"""

    def create_participant(self, first_name, last_name, email=None, phone=None,
                          gender=None, age=None, rfid_tag=None):
        """Create a new participant"""
        session = get_session()
        participant = Participant(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            gender=gender,
            age=age,
            rfid_tag=rfid_tag
        )
        session.add(participant)
        session.commit()
        session.refresh(participant)
        return participant

    def register_participant(self, race_id, participant_id, bib_number, category="Open"):
        """Register a participant for a race"""
        session = get_session()
        stmt = race_participants.insert().values(
            race_id=race_id,
            participant_id=participant_id,
            bib_number=bib_number,
            category=category
        )
        session.execute(stmt)
        session.commit()

    def get_participant(self, participant_id):
        """Get a participant by ID"""
        return get_session().query(Participant).filter(Participant.id == participant_id).first()

    def get_participant_by_rfid(self, rfid_tag):
        """Get a participant by RFID tag"""
        return get_session().query(Participant).filter(Participant.rfid_tag == rfid_tag).first()

    def get_participant_by_bib(self, race_id, bib_number):
        """Get a participant by bib number for a specific race"""
        # Convert bib_number to string since the column is VARCHAR
        bib_str = str(bib_number)
        result = get_session().query(Participant).join(
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
        session = get_session()
        if race_id:
            return session.query(Participant).join(
                race_participants,
                Participant.id == race_participants.c.participant_id
            ).filter(race_participants.c.race_id == race_id).all()
        else:
            return session.query(Participant).all()

    def update_rfid_tag(self, participant_id, rfid_tag):
        """Update a participant's RFID tag"""
        session = get_session()
        participant = session.query(Participant).filter(Participant.id == participant_id).first()
        if participant:
            participant.rfid_tag = rfid_tag
            session.commit()
            return True
        return False

    def update_participant(self, participant_id, **kwargs):
        """Update participant information"""
        session = get_session()
        participant = session.query(Participant).filter(Participant.id == participant_id).first()
        if not participant:
            return False

        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'gender', 'age', 'rfid_tag']
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(participant, field, value)

        session.commit()
        return True

    def delete_participant(self, participant_id):
        """Delete a participant"""
        session = get_session()
        participant = session.query(Participant).filter(Participant.id == participant_id).first()
        if participant:
            session.delete(participant)
            session.commit()
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

# Made with Bob
