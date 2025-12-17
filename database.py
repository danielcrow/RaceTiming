"""
Database initialization and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database configuration from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    # Build DATABASE_URL from individual components
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'race_timing')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Check if we should use PostgreSQL (DB_NAME is set and not empty)
    # Empty password is OK for local PostgreSQL (e.g., Postgres.app)
    if DB_NAME and DB_NAME != 'race_timing.db':
        if DB_PASSWORD:
            DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        else:
            # No password (common for Postgres.app on macOS)
            DATABASE_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    else:
        # Fallback to SQLite
        DB_PATH = os.path.join(os.path.dirname(__file__), 'race_timing.db')
        DATABASE_URL = f'sqlite:///{DB_PATH}'
        print(f"Warning: Using SQLite fallback at: {DB_PATH}")


# Create engine with appropriate settings
if DATABASE_URL.startswith('postgresql'):
    # PostgreSQL-specific settings
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,  # Verify connections before using them
        pool_size=10,
        max_overflow=20
    )
    print(f"Using PostgreSQL database")
else:
    # SQLite settings
    engine = create_engine(DATABASE_URL, echo=False)
    print(f"Using SQLite database")

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize the database, creating all tables"""
    Base.metadata.create_all(engine)
    print(f"Database initialized: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")


def get_session():
    """Get a new database session"""
    return Session()


def close_session():
    """Close the current session"""
    Session.remove()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
