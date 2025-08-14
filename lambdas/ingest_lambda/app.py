import os
import json
import hashlib
from datetime import datetime, timezone

import boto3
import requests

table_name = os.environ["DDB_TABLE"]
ecfr_base = os.environ.get("ECFR_BASE_URL", "https://www.ecfr.gov/api")

ddb = boto3.resource("dynamodb")
table = ddb.Table(table_name)

# Minimal fetch — you can expand to pull per-agency text; here we fetch a small sample
# and simulate an "agency snapshot" with a word_count + checksum over concatenated titles.

def fetch_sample():
    # Titles endpoint (example); adjust to the real eCFR endpoint you choose
    url = f"{ecfr_base}/versioner/v1/titles.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data


def compute_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def upsert_agency_snapshot(agency: str, payload_text: str):
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    checksum = compute_checksum(payload_text)
    word_count = len(payload_text.split())
    item = {
        "pk": f"AGENCY#{agency}",
        "sk": f"SNAPSHOT#{date_str}",
        "agency": agency,
        "date": date_str,
        "checksum": checksum,
        "word_count": word_count,
    }
    table.put_item(Item=item)
    return item


def handler(event, context):
    sample = fetch_sample()
    # Very naive mapping: pretend title agency code = first token of 'name'
    # In your real implementation, map properly from eCFR data to agencies
    titles = sample.get("titles", []) if isinstance(sample, dict) else []
    if not titles:
        return {"ok": False, "message": "No titles returned"}

    saved = []
    for t in titles[:5]:  # keep it small for demo
        name = t.get("name") or t.get("title") or "UNKNOWN"
        agency = name.split()[0].upper()[:8]
        payload_text = json.dumps(t, separators=(",", ":"))
        saved.append(upsert_agency_snapshot(agency, payload_text))

    return {"ok": True, "count": len(saved)}