# api_client.py
"""Thin wrapper around the existing RaceTiming REST API.
Adjust BASE_API if the main app runs on a different host/port.
"""
import requests
from urllib.parse import urljoin

# Assuming the main app is reachable at localhost:5001
BASE_API = "http://localhost:5001/api/"


def get_race(race_id):
    return requests.get(urljoin(BASE_API, f"races/{race_id}")).json()


def get_results(race_id):
    """Return the list of time records for a race (latest first)."""
    return requests.get(urljoin(BASE_API, f"races/{race_id}/results")).json()


def get_timing_points(race_id):
    return requests.get(urljoin(BASE_API, f"races/{race_id}/timing-points")).json()
