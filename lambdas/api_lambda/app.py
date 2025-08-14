import os
import json
import boto3
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from mangum import Mangum
from datetime import datetime

TABLE_NAME = os.environ.get("DDB_TABLE")
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "")
PROJECT_ENV = os.environ.get("PROJECT_ENV", "dev")

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
app = FastAPI(title="USDS eCFR API", version="0.1.0")

# --- simple, no-JS HTML helpers ---
HTML_PAGE = """
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>eCFR Analytics ({env})</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 900px; }}
 h1, h2 {{ margin: 0 0 0.5rem 0; }}
 table {{ border-collapse: collapse; width: 100%; }}
 th, td {{ border: 1px solid #ddd; padding: 8px; }}
 th {{ background: #f6f6f6; text-align: left; }}
 .muted {{ color: #666; font-size: 0.9rem; }}
 .note {{ background: #ffffe0; padding: .5rem; border: 1px solid #ddd; }}
 .summary {{ background: #f0f8ff; padding: .75rem; margin: 1rem 0; border-left: 4px solid #0066cc; }}
 a {{ color: #0066cc; text-decoration: none; }}
 a:hover {{ text-decoration: underline; }}
</style>
<h1>eCFR Analytics — {env}</h1>
<p class="muted">Server-rendered HTML (no JavaScript). Use the forms below to query metrics.</p>

<h2>Agencies (latest snapshot)</h2>
<form method="get" action="/agencies">
  <label>Limit: <input name="limit" type="number" value="25" min="1" max="200"></label>
  <button type="submit">List</button>
</form>

<h2>History by Agency</h2>
<form method="get" action="/metrics/history">
  <label>Agency: <input name="agency" placeholder="HHS" required></label>
  <label>From (YYYY-MM-DD): <input name="from" placeholder="2025-08-01"></label>
  <button type="submit">Fetch</button>
</form>

<h2>Checksum by Agency</h2>
<form method="get" action="/checksum">
  <label>Agency: <input name="agency" placeholder="HHS" required></label>
  <button type="submit">Fetch</button>
</form>

<p class="note">Tip: trigger an update via CI workflow "Update Data" to pull fresh eCFR and compute metrics.</p>
"""

FOOTER = """
<hr>
<p class="muted">&copy; {year} — USDS eCFR Starter</p>
</html>
"""


def _auth_or_403(request: Request):
    token = request.headers.get("x-api-key", "")
    if not API_AUTH_TOKEN or token != API_AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    _auth_or_403(request)
    return HTML_PAGE.format(env=PROJECT_ENV) + FOOTER.format(year=datetime.utcnow().year)


@app.get("/agencies")
async def agencies(request: Request, limit: int = 25, format: str = "html"):
    _auth_or_403(request)
    # PK: AGENCY#<code>  SK: SNAPSHOT#<date>
    resp = table.scan(Limit=limit)
    items = [i for i in resp.get("Items", []) if i.get("pk", "").startswith("AGENCY#")]
    
    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Agency", "Date", "Word Count", "Checksum"])
        for item in items:
            writer.writerow([item.get('agency',''), item.get('date',''), item.get('word_count',0), item.get('checksum','')])
        return JSONResponse(content=output.getvalue(), headers={"Content-Type": "text/csv"})
    
    # Calculate summary stats
    total_words = sum(i.get('word_count', 0) for i in items)
    avg_words = total_words // len(items) if items else 0
    
    html_rows = [
        f"<tr><td>{i.get('agency','')}</td><td>{i.get('date','')}</td><td>{i.get('word_count',0):,}</td><td>{i.get('checksum','')[:8]}...</td></tr>"
        for i in items
    ]
    
    summary = f"<div class='summary'>Total agencies: {len(items)} | Total words: {total_words:,} | Average: {avg_words:,}</div>"
    export_link = f"<p><a href='/agencies?format=csv&limit={limit}'>📊 Export as CSV</a></p>"
    
    html = (
        HTML_PAGE.format(env=PROJECT_ENV)
        + summary + export_link
        + "<table><tr><th>Agency</th><th>Date</th><th>Word Count</th><th>Checksum</th></tr>"
        + ("".join(html_rows) or "<tr><td colspan=4>No data yet</td></tr>")
        + "</table>"
        + FOOTER.format(year=datetime.utcnow().year)
    )
    return HTMLResponse(content=html)


@app.get("/metrics/history")
async def history(request: Request, agency: str, _from: str | None = None):
    _auth_or_403(request)
    # Minimal example: query by begins_with SK
    # PK: AGENCY#<agency>
    key = f"AGENCY#{agency.upper()}"
    kwargs = {
        "KeyConditionExpression": boto3.dynamodb.conditions.Key("pk").eq(key)
    }
    resp = table.query(**kwargs)
    items = sorted(resp.get("Items", []), key=lambda x: x.get("date", ""))
    html_rows = [
        f"<tr><td>{i.get('date','')}</td><td>{i.get('word_count',0)}</td><td>{i.get('checksum','')}</td></tr>"
        for i in items
    ]
    html = (
        HTML_PAGE.format(env=PROJECT_ENV)
        + f"<h2>History — {agency.upper()}</h2>"
        + "<table><tr><th>Date</th><th>Word Count</th><th>Checksum</th></tr>"
        + ("".join(html_rows) or "<tr><td colspan=3>No data</td></tr>")
        + "</table>"
        + FOOTER.format(year=datetime.utcnow().year)
    )
    return HTMLResponse(content=html)


@app.get("/checksum")
async def checksum(request: Request, agency: str):
    _auth_or_403(request)
    key = f"AGENCY#{agency.upper()}"
    resp = table.query(KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq(key))
    items = sorted(resp.get("Items", []), key=lambda x: x.get("date", ""))
    last = items[-1] if items else None
    if not last:
        return JSONResponse({"agency": agency.upper(), "message": "No data"})
    return JSONResponse({
        "agency": agency.upper(),
        "date": last.get("date"),
        "checksum": last.get("checksum"),
        "word_count": last.get("word_count", 0)
    })


handler = Mangum(app)