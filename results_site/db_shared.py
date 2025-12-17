import sys
import os

# Add the parent RaceTiming directory to PYTHONPATH
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from database import engine  # the same SQLAlchemy engine used by RaceTiming
