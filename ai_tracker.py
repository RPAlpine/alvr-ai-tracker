"""
ALVR AI-Overview & Organic Position Tracker
-------------------------------------------
Runs a set of queries via SerpAPI, records:
  • Organic result position for your domain
  • Whether the Google AI Overview cites your domain
  • Position of the citation inside the AI card (if any)

Outputs / appends a CSV called `alvr_ai_tracker.csv`.

Prerequisites
-------------
1. pip install -r requirements.txt   (serpapi, plus gspread/oauth2client if you’ll push to Sheets)
2. Environment variable SERPAPI_KEY must be set (add as GitHub Actions secret).

Optional Google Sheets push:
  • Add secrets GCP_SA_JSON (base-64 service-account JSON) and GSHEET_ID
  • Uncomment the sheet-handling lines below
"""

import os
import csv
import json
import datetime
import time
from serpapi import GoogleSearch

# --------------------------------------------------------------------
# 1. CONFIG – edit as needed
# --------------------------------------------------------------------
KEYWORDS = [
    "Aspen vacation rentals",
    "Aspen rentals",
    "luxury vacation rentals in Aspen",
    "Aspen cabin rentals",
    "Aspen condo rentals",
]

DOMAIN = "aspenluxuryvacationrentals.com"   # match on this domain string
LOCATION = "Aspen, Colorado, United States" # SerpAPI supported location
CSV_NAME = "alvr_ai_tracker.csv"
PAUSE_SECONDS = 4                           # stay inside free-tier QPS

# --------------------------------------------------------------------
def run_query(query: str):
    """Call SerpAPI and return the response dict."""
    params = {
        "engine": "google",
        "q": query,
        "hl": "en",
        "gl": "us",
        "location": LOCATION,
        # Experimental param to include AI Overview JSON
        "ai_overview": "include",
        "api_key": os.getenv("SERPAPI_KEY"),
    }
    return GoogleSearch(params).get_dict()

# --------------------------------------------------------------------
def parse_result(data: dict):
    """
    Extract organic position and AI-Overview citation info.
    Returns (organic_pos:int|None, ai_cited:bool, ai_rank:int|None).
    """
    organic_pos = None
    for i, result in enumerate(data.get("organic_results", []), start=1):
        if DOMAIN in result.get("link", ""):
            organic_pos = i
            break

    ai_data = data.get("answer_box") or data.get("ai_overview")
    ai_cited = False
    ai_rank = None
    if ai_data:
        # SerpAPI structures may vary; fall back to JSON search
        serialized = json.dumps(ai_data)
        if DOMAIN in serialized:
            ai_cited = True
            # Try to grab index in citations array if available
            citations = ai_data.get("citations") or []
            for i, c in enumerate(citations):
                if DOMAIN in json.dumps(c):
                    ai_rank = i + 1
                    break

    return organic_pos, ai_cited, ai_rank

# --------------------------------------------------------------------
# Optional Google Sheets helper
def _sheet_client():
    import base64, gspread
    sa_json = base64.b64decode(os.getenv("GCP_SA_JSON"))
    creds = gspread.service_account_from_dict(json.loads(sa_json))
