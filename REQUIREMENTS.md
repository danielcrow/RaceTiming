# Requirements Files

This project has two separate requirements files for different components:

## Main Application (`requirements.txt`)

Dependencies for the main Race Timing system including:
- Flask web application
- SQLAlchemy database ORM
- LLRP RFID reader support
- PostgreSQL database support
- CLI tools and utilities

**Used by:**
- `web_app.py` - Main web application
- `cli.py` - Command-line interface
- `race_control.py` - Race timing control
- All core timing system modules

**Install:**
```bash
pip install -r requirements.txt
```

## Results Site (`results_site/requirements.txt`)

Minimal dependencies for the standalone public results website:
- Flask (web framework)
- SQLAlchemy (database)
- Requests (for API calls if needed)

**Used by:**
- `results_site/app.py` - Public results website
- Deployed separately (e.g., on Vercel)

**Install:**
```bash
cd results_site
pip install -r requirements.txt
```

## Why Separate Files?

The results site is designed to be deployed independently from the main timing system:
- **Lighter dependencies** - Only needs Flask and SQLAlchemy
- **Separate deployment** - Can be hosted on different platforms
- **Security** - Public site doesn't need RFID reader or database admin tools
- **Scalability** - Results site can scale independently

## Development Setup

For local development of both systems:

```bash
# Main system
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Results site (in separate terminal/environment)
cd results_site
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt