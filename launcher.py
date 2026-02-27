"""
Race Timing System — Desktop Launcher
Starts the Flask server and opens the browser automatically.
Run this file directly or use the PyInstaller-built executable.
"""
import sys
import os
import threading
import time
import webbrowser
import signal
import logging

# ---------------------------------------------------------------------------
# Path bootstrap — needed when running as a PyInstaller frozen bundle
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # Running inside a PyInstaller bundle
    BASE_DIR = sys._MEIPASS  # noqa: SLF001  (PyInstaller temp dir)
    # Put the bundle root on sys.path so all modules are importable
    sys.path.insert(0, BASE_DIR)
    # Store user-writable data next to the executable
    DATA_DIR = os.path.join(os.path.dirname(sys.executable), 'data')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')

os.makedirs(DATA_DIR, exist_ok=True)

# Point SQLite database into the writable data directory (used by database.py
# when no DATABASE_URL / DB_NAME env var is set).
if not os.environ.get('DATABASE_URL') and not os.environ.get('DB_NAME'):
    db_path = os.path.join(DATA_DIR, 'race_timing.db')
    os.environ.setdefault('DATABASE_URL', f'sqlite:///{db_path}')

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_path = os.path.join(DATA_DIR, 'race_timing.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger('launcher')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HOST = '127.0.0.1'
PORT = 5001
APP_URL = f'http://{HOST}:{PORT}'


def _open_browser():
    """Wait for the server to be ready, then open the default browser."""
    import urllib.request
    for _ in range(30):          # up to ~6 s
        try:
            urllib.request.urlopen(APP_URL, timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    webbrowser.open(APP_URL)


def _run_server():
    """Initialise the database and start the Flask development server."""
    from database import init_db
    from web_app import app

    logger.info('Initialising database …')
    init_db()

    logger.info('Starting Race Timing System on %s', APP_URL)
    # use_reloader=False is required — reloader forks the process which breaks
    # the frozen bundle and the single-instance guarantee.
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def main():
    logger.info('Race Timing System launcher starting')
    logger.info('Data directory: %s', DATA_DIR)

    # Start browser opener in background
    browser_thread = threading.Thread(target=_open_browser, daemon=True)
    browser_thread.start()

    # Graceful Ctrl-C handling
    def _sigint(sig, frame):  # noqa: ANN001
        logger.info('Shutting down …')
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)
    signal.signal(signal.SIGTERM, _sigint)

    _run_server()


if __name__ == '__main__':
    main()

# Made with Bob
