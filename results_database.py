"""
Database setup for Results Publishing Site
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from results_models import Base
import os

# Database configuration
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'results_public.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize the database, creating all tables"""
    Base.metadata.create_all(engine)
    print(f"Database initialized at {DATABASE_PATH}")


def get_session():
    """Get a database session"""
    return Session()


if __name__ == '__main__':
    # Initialize database when run directly
    init_db()
    print("Results publishing database created successfully!")
