"""
Database models for Race Timing System
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Enum, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

# Association table for many-to-many relationship between Race and Participant
race_participants = Table('race_participants', Base.metadata,
    Column('race_id', Integer, ForeignKey('races.id')),
    Column('participant_id', Integer, ForeignKey('participants.id')),
    Column('bib_number', String(20)),
    Column('category', String(50)),
    Column('registered_at', DateTime, default=datetime.utcnow)
)


class RaceType(enum.Enum):
    """Supported race types"""
    TRIATHLON = "triathlon"
    DUATHLON = "duathlon"
    AQUATHLON = "aquathlon"
    RUNNING = "running"
    CYCLING = "cycling"


class LegType(enum.Enum):
    """Types of race legs/segments"""
    SWIM = "swim"
    BIKE = "bike"
    RUN = "run"
    TRANSITION = "transition"


class TimingSource(enum.Enum):
    """Source of timing data"""
    LLRP = "llrp"
    MANUAL = "manual"
    SYSTEM = "system"


class ParticipantStatus(enum.Enum):
    """Participant race status"""
    REGISTERED = "registered"
    STARTED = "started"
    FINISHED = "finished"
    DNF = "dnf"  # Did Not Finish
    DNS = "dns"  # Did Not Start
    DSQ = "dsq"  # Disqualified


class StartMode(enum.Enum):
    """Race start timing mode"""
    MASS_START = "mass_start"  # All participants start at race start time
    CHIP_START = "chip_start"  # Each participant starts on first tag read


class LLRPStation(Base):
    """LLRP RFID Reader Station"""
    __tablename__ = 'llrp_stations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    reader_ip = Column(String(50), nullable=False)
    reader_port = Column(Integer, default=5084)
    cooldown_seconds = Column(Integer, default=5)
    
    # Status
    is_active = Column(Boolean, default=False)
    last_connected = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    timing_points = relationship("TimingPoint", back_populates="llrp_station")
    
    def __repr__(self):
        return f"<LLRPStation(id={self.id}, name='{self.name}', ip='{self.reader_ip}')>"


class Event(Base):
    """Event definition (container for races)"""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False)
    location = Column(String(200))
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    races = relationship("Race", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}')>"


class Race(Base):
    """Race definition"""
    __tablename__ = 'races'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)  # Nullable for existing races or standalone races
    name = Column(String(200), nullable=False)
    race_type = Column(Enum(RaceType), nullable=False)
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=True)
    finish_time = Column(DateTime, nullable=True)
    location = Column(String(200))
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    age_groups = Column(String(1000))  # JSON string of age group definitions
    llrp_enabled = Column(Boolean, default=False)  # Track if LLRP timing is enabled for this race
    start_mode = Column(Enum(StartMode), default=StartMode.MASS_START)  # Start timing mode
    
    # Relationships
    event = relationship("Event", back_populates="races")
    legs = relationship("RaceLeg", back_populates="race", cascade="all, delete-orphan", order_by="RaceLeg.order")
    timing_points = relationship("TimingPoint", back_populates="race", cascade="all, delete-orphan")
    participants = relationship("Participant", secondary=race_participants, back_populates="races")
    results = relationship("RaceResult", back_populates="race", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Race(id={self.id}, name='{self.name}', type={self.race_type.value})>"


class RaceLeg(Base):
    """Individual leg/segment of a race"""
    __tablename__ = 'race_legs'
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('races.id'), nullable=False)
    name = Column(String(100), nullable=False)
    leg_type = Column(Enum(LegType), nullable=False)
    order = Column(Integer, nullable=False)  # Order in the race (1, 2, 3...)
    distance = Column(Float)  # Distance in km
    distance_unit = Column(String(10), default="km")
    
    # Relationships
    race = relationship("Race", back_populates="legs")
    
    def __repr__(self):
        return f"<RaceLeg(id={self.id}, name='{self.name}', type={self.leg_type.value}, order={self.order})>"


class Participant(Base):
    """Race participant"""
    __tablename__ = 'participants'
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(200))
    phone = Column(String(20))
    gender = Column(String(10))
    age = Column(Integer)
    date_of_birth = Column(Date, nullable=True)  # Optional: for British Triathlon age calculation
    rfid_tag = Column(String(50), unique=True)  # RFID tag EPC
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    races = relationship("Race", secondary=race_participants, back_populates="participants")
    time_records = relationship("TimeRecord", back_populates="participant", cascade="all, delete-orphan")
    results = relationship("RaceResult", back_populates="participant", cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<Participant(id={self.id}, name='{self.full_name}', rfid='{self.rfid_tag}')>"


class TimingPoint(Base):
    """Timing checkpoint in a race"""
    __tablename__ = 'timing_points'
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('races.id'), nullable=False)
    name = Column(String(100), nullable=False)
    order = Column(Integer, nullable=False)
    is_start = Column(Boolean, default=False)
    is_finish = Column(Boolean, default=False)
    leg_id = Column(Integer, ForeignKey('race_legs.id'))  # Optional: associated leg
    llrp_station_id = Column(Integer, ForeignKey('llrp_stations.id'), nullable=True)  # Optional: assigned LLRP station
    
    # Relationships
    race = relationship("Race", back_populates="timing_points")
    time_records = relationship("TimeRecord", back_populates="timing_point", cascade="all, delete-orphan")
    llrp_station = relationship("LLRPStation", back_populates="timing_points")
    
    def __repr__(self):
        return f"<TimingPoint(id={self.id}, name='{self.name}', order={self.order})>"


class TimeRecord(Base):
    """Individual timing record"""
    __tablename__ = 'time_records'
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('races.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=False)
    timing_point_id = Column(Integer, ForeignKey('timing_points.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    source = Column(Enum(TimingSource), nullable=False)
    notes = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    participant = relationship("Participant", back_populates="time_records")
    timing_point = relationship("TimingPoint", back_populates="time_records")
    
    def __repr__(self):
        return f"<TimeRecord(participant_id={self.participant_id}, point_id={self.timing_point_id}, time={self.timestamp})>"


class RaceResult(Base):
    """Calculated race result for a participant"""
    __tablename__ = 'race_results'
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('races.id'), nullable=False)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=False)
    bib_number = Column(String(20))
    category = Column(String(50))
    status = Column(Enum(ParticipantStatus), default=ParticipantStatus.REGISTERED)
    
    # Times (in seconds)
    start_time = Column(DateTime)
    finish_time = Column(DateTime)
    total_time = Column(Float)  # Total time in seconds
    
    # Rankings
    overall_rank = Column(Integer)
    category_rank = Column(Integer)
    gender_rank = Column(Integer)
    
    # Additional data
    split_times = Column(String(1000))  # JSON string of split times
    notes = Column(String(500))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    race = relationship("Race", back_populates="results")
    participant = relationship("Participant", back_populates="results")
    
    def __repr__(self):
        return f"<RaceResult(race_id={self.race_id}, participant_id={self.participant_id}, status={self.status.value})>"
