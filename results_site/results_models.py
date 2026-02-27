"""
Database models for Results Publishing Site
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class PublishedEvent(Base):  # type: ignore[misc]
    """Published event for public viewing"""
    __tablename__ = 'published_events'
    
    id = Column(Integer, primary_key=True)
    source_event_id = Column(Integer, nullable=False, unique=True)  # ID from main system
    name = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False)
    location = Column(String(200))
    description = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_live = Column(Boolean, default=True)
    
    # Relationships
    races = relationship("PublishedRace", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PublishedEvent(id={self.id}, name='{self.name}')>"


class PublishedRace(Base):  # type: ignore[misc]
    """Published race for public viewing"""
    __tablename__ = 'published_races'
    
    id = Column(Integer, primary_key=True)
    source_race_id = Column(Integer, nullable=False, unique=True)  # ID from main system
    event_id = Column(Integer, ForeignKey('published_events.id'))
    name = Column(String(200), nullable=False)
    race_type = Column(String(50))
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime)
    finish_time = Column(DateTime)
    published_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    auto_publish = Column(Boolean, default=False)
    publish_interval_seconds = Column(Integer, default=30)
    
    # Relationships
    event = relationship("PublishedEvent", back_populates="races")
    results = relationship("PublishedResult", back_populates="race", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PublishedRace(id={self.id}, name='{self.name}')>"


class PublishedResult(Base):  # type: ignore[misc]
    """Published race result for public viewing"""
    __tablename__ = 'published_results'
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('published_races.id'), nullable=False)
    bib_number = Column(String(20))
    participant_name = Column(String(200), nullable=False)
    gender = Column(String(10))
    age = Column(Integer)
    category = Column(String(50))
    status = Column(String(20))
    overall_rank = Column(Integer)
    category_rank = Column(Integer)
    gender_rank = Column(Integer)
    finish_time = Column(DateTime)
    total_time_seconds = Column(Float)
    split_times = Column(Text)  # JSON string
    published_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    race = relationship("PublishedRace", back_populates="results")
    
    def __repr__(self):
        return f"<PublishedResult(id={self.id}, name='{self.participant_name}', rank={self.overall_rank})>"


class PublishingLog(Base):  # type: ignore[misc]
    """Log of publishing actions"""
    __tablename__ = 'publishing_log'
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey('published_races.id'))
    published_at = Column(DateTime, default=datetime.utcnow)
    result_count = Column(Integer)
    publish_type = Column(String(20))  # 'manual' or 'auto'
    published_by = Column(String(100))  # username or 'system'
    
    def __repr__(self):
        return f"<PublishingLog(id={self.id}, race_id={self.race_id}, type={self.publish_type})>"
