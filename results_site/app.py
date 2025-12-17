# app.py
"""Standalone results site.
It reads data from the existing RaceTiming DB and API and provides a live‑results page.
Run with: `flask run --host 0.0.0.0 --port 5002` (or via gunicorn).
"""
from flask import Flask, render_template, jsonify, Response, stream_with_context
import json, time, threading
from api_client import get_results, get_race
from db_shared import engine

app = Flask(__name__)

# ------------------------------------------------------------------
# Helper – fetch latest results directly from DB (fallback if API fails)
# ------------------------------------------------------------------
def fetch_latest_results(race_id):
    try:
        return get_results(race_id)
    except Exception:
        # Direct DB query as a safety net
        with engine.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.full_name, tp.name AS point_name,
                       tr.timestamp AT TIME ZONE 'UTC' AS ts
                FROM time_records tr
                JOIN participants p ON tr.participant_id = p.id
                JOIN timing_points tp ON tr.timing_point_id = tp.id
                WHERE tr.race_id = %s
                ORDER BY tr.timestamp ASC
                """,
                (race_id,)
            ).fetchall()
            return [dict(row) for row in rows]

# ------------------------------------------------------------------
# SSE endpoint – streams new time records as they appear
# ------------------------------------------------------------------
@app.route('/results/stream/<int:race_id>')
def results_stream(race_id):
    def event_stream():
        last_seen = 0
        while True:
            results = fetch_latest_results(race_id)
            if len(results) > last_seen:
                new = results[last_seen:]
                for rec in new:
                    payload = json.dumps(rec)
                    yield f"data: {payload}\n\n"
                last_seen = len(results)
            time.sleep(1)
    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

# ------------------------------------------------------------------
# Main page – shows live results for a race
# ------------------------------------------------------------------
@app.route('/results/<int:race_id>')
def results_page(race_id):
    race = get_race(race_id)
    initial = fetch_latest_results(race_id)
    return render_template('results.html', race=race, results=initial, race_id=race_id)

# ------------------------------------------------------------------
# Simple health check
# ------------------------------------------------------------------
@app.route('/ping')
def ping():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Run on a different port so it can coexist with the main app
    app.run(host='0.0.0.0', port=5002, debug=True)
