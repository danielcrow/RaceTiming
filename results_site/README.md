# Race Timing Results Site

A standalone results publishing site that displays live race results. This site receives published results from the main Race Timing system via webhooks and stores them in a local database for fast public access.

## Features

- Live race results with automatic polling (updates every 10 seconds)
- Webhook-based result publishing from the main timing system
- Local database storage for fast access
- Search functionality for races and events
- Responsive design with dark-mode glass-morphism style
- Vercel-compatible (serverless, no persistent connections required)

## Architecture

This site operates independently from the main timing system:

```
Main Timing System  ──webhook POST──►  Results Site (Vercel)
                                            │
                                            ▼
                                       SQLite / PostgreSQL
                                            │
                                            ▼
                                    Public Users (polling)
```

- **Main Timing System** pushes results via authenticated webhook POSTs
- **Results Site** receives, validates, and stores results in its own database
- **Public Users** view results; the page polls `/api/results/<id>` every 10 seconds for live updates

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (create a `.env` file or export):
```bash
export WEBHOOK_SECRET=your-secret-key-here
```

3. Run the application:
```bash
python app.py
```

The site will be available at http://localhost:5002

4. Configure the main timing system to publish to this site:
   - Set `RESULTS_PUBLISH_URL=http://localhost:5002` in the main system's `.env`
   - Set `WEBHOOK_SECRET` to match the value above

## Deployment to Vercel

### Prerequisites

- Install Vercel CLI: `npm install -g vercel`
- Have a Vercel account

### Deploy Steps

1. Navigate to the results_site directory:
```bash
cd results_site
```

2. Login to Vercel (first time only):
```bash
vercel login
```

3. Deploy:
```bash
vercel --prod
```

### Environment Variables

Set the following in your Vercel project settings (Settings → Environment Variables):

| Variable | Required | Description |
|---|---|---|
| `WEBHOOK_SECRET` | **Yes** | Auth secret for webhook requests — must match the main timing system |
| `DATABASE_URL` | No | PostgreSQL/MySQL URL for persistent storage. If unset, uses SQLite in `/tmp` (ephemeral) |

> **Note on SQLite on Vercel:** Vercel's filesystem is ephemeral — data in `/tmp` is lost on cold starts. For production use, set `DATABASE_URL` to a persistent database (e.g. Supabase, PlanetScale, Railway Postgres).

## File Structure

```
results_site/
├── app.py                  # Main Flask application
├── index.py                # Vercel entry point
├── results_database.py     # Database setup (SQLite / PostgreSQL)
├── results_models.py       # SQLAlchemy models
├── requirements.txt        # Python dependencies
├── vercel.json             # Vercel deployment configuration
├── templates/
│   ├── index.html          # Home page (race list + search)
│   └── results.html        # Race results page (polling)
└── static/
    └── css/
        └── style.css       # Dark-mode glass-morphism styles
```

## API Endpoints

### Public Pages
- `GET /` — Home page with race list and search
- `GET /results/<race_id>` — Results page for a specific race

### JSON API
- `GET /api/results/<race_id>` — JSON results for a race (used by polling)
- `GET /ping` — Health check; returns DB connection status

### Webhooks (authenticated via `X-Webhook-Secret` header)
- `POST /webhook/publish-event` — Receive/update an event
- `POST /webhook/publish-race` — Receive/update a race
- `POST /webhook/publish-results` — Receive/replace results for a race