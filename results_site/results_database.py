"""
Database setup for Results Publishing Site

Supports:
  - Local development: SQLite file in the project directory
  - Vercel / serverless: SQLite in /tmp (ephemeral, re-populated via webhooks)
  - Production DB: Set DATABASE_URL env var to a PostgreSQL/MySQL connection string
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from results_models import Base
import os

# Database configuration
# Priority: DATABASE_URL env var > /tmp on Vercel > local file
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    # Detect Vercel serverless environment (read-only filesystem except /tmp)
    if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        DATABASE_PATH = '/tmp/results_public.db'
    else:
        DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_public.db')
    DATABASE_URL = f'sqlite:///{DATABASE_PATH}'
else:
    DATABASE_PATH = None
    # Handle postgres:// -> postgresql:// for SQLAlchemy 1.4+
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create engine with appropriate settings
connect_args = {}
if DATABASE_URL.startswith('sqlite'):
    connect_args = {'check_same_thread': False}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args
)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize the database, creating all tables"""
    Base.metadata.create_all(engine)
    if DATABASE_PATH:
        print(f"Database initialized at {DATABASE_PATH}")
    else:
        print("Database initialized (external URL)")


def get_session():
    """Get a database session"""
    return Session()


if __name__ == '__main__':
    # Initialize database when run directly
    init_db()
    print("Results publishing database created successfully!")
