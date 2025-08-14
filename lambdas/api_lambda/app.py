import os
import json
import boto3
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from mangum import Mangum
from datetime import datetime
from typing import Optional, List, Dict, Any
from boto3.dynamodb.conditions import Key, Attr

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

<h2>Agencies</h2>
<form method="get" action="/agencies">
  <label>Limit: <input name="limit" type="number" value="25" min="1" max="200"></label>
  <button type="submit">List Agencies</button>
</form>

<h2>CFR Titles</h2>
<form method="get" action="/titles">
  <label>Limit: <input name="limit" type="number" value="10" min="1" max="50"></label>
  <button type="submit">List Titles</button>
</form>

<h2>Title Structure</h2>
<form method="get" action="/title/structure">
  <label>Title Number: <input name="title_num" placeholder="40" required></label>
  <button type="submit">View Structure</button>
</form>

<h2>Agency CFR Coverage</h2>
<form method="get" action="/agency/cfr">
  <label>Agency Slug: <input name="agency_slug" placeholder="environmental-protection-agency" required></label>
  <button type="submit">View CFR Coverage</button>
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
    
    # Scan for agency metadata
    resp = table.scan(
        FilterExpression=Attr('entity_type').eq('agency'),
        Limit=limit
    )
    items = resp.get("Items", [])
    
    if format == "json":
        return JSONResponse(content={"agencies": items, "count": len(items)})
    
    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Short Name", "Slug", "CFR References", "Updated Date"])
        for item in items:
            cfr_refs = "; ".join([f"Title {ref.get('title')} Ch {ref.get('chapter', '')}" for ref in item.get('cfr_references', [])])
            writer.writerow([item.get('name',''), item.get('short_name',''), item.get('slug',''), cfr_refs, item.get('updated_date','')])
        return JSONResponse(content=output.getvalue(), headers={"Content-Type": "text/csv"})
    
    html_rows = []
    for item in items:
        cfr_refs = ", ".join([f"Title {ref.get('title')}" for ref in item.get('cfr_references', [])[:3]])
        if len(item.get('cfr_references', [])) > 3:
            cfr_refs += "..."
        html_rows.append(
            f"<tr><td>{item.get('name','')}</td><td>{item.get('short_name','')}</td><td>{cfr_refs}</td><td>{item.get('updated_date','')}</td></tr>"
        )
    
    summary = f"<div class='summary'>Total agencies: {len(items)}</div>"
    export_links = f"<p><a href='/agencies?format=json&limit={limit}'>📄 JSON</a> | <a href='/agencies?format=csv&limit={limit}'>📊 CSV</a></p>"
    
    html = (
        HTML_PAGE.format(env=PROJECT_ENV)
        + summary + export_links
        + "<table><tr><th>Agency Name</th><th>Short Name</th><th>CFR Titles</th><th>Updated</th></tr>"
        + ("".join(html_rows) or "<tr><td colspan=4>No agencies found</td></tr>")
        + "</table>"
        + FOOTER.format(year=datetime.utcnow().year)
    )
    return HTMLResponse(content=html)


@app.get("/titles")
async def titles(request: Request, limit: int = 10, format: str = "html"):
    _auth_or_403(request)
    
    resp = table.scan(
        FilterExpression=Attr('entity_type').eq('title'),
        Limit=limit
    )
    items = sorted(resp.get("Items", []), key=lambda x: x.get("number", 0))
    
    if format == "json":
        return JSONResponse(content={"titles": items, "count": len(items)})
    
    html_rows = []
    for item in items:
        reserved = "Yes" if item.get('reserved', False) else "No"
        html_rows.append(
            f"<tr><td>{item.get('number','')}</td><td>{item.get('name','')}</td><td>{item.get('latest_amended_on','')}</td><td>{reserved}</td></tr>"
        )
    
    summary = f"<div class='summary'>Total CFR titles: {len(items)}</div>"
    export_link = f"<p><a href='/titles?format=json&limit={limit}'>📄 Export as JSON</a></p>"
    
    html = (
        HTML_PAGE.format(env=PROJECT_ENV)
        + summary + export_link
        + "<table><tr><th>Title #</th><th>Name</th><th>Last Amended</th><th>Reserved</th></tr>"
        + ("".join(html_rows) or "<tr><td colspan=4>No titles found</td></tr>")
        + "</table>"
        + FOOTER.format(year=datetime.utcnow().year)
    )
    return HTMLResponse(content=html)

@app.get("/title/structure")
async def title_structure(request: Request, title_num: int, format: str = "html"):
    _auth_or_403(request)
    
    resp = table.query(
        KeyConditionExpression=Key('pk').eq(f'TITLE#{title_num}') & Key('sk').begins_with('CHAPTER#'),
        Limit=50
    )
    chapters = resp.get("Items", [])
    
    # Get parts for each chapter (limit for demo)
    resp = table.query(
        KeyConditionExpression=Key('pk').eq(f'TITLE#{title_num}') & Key('sk').begins_with('PART#'),
        Limit=20
    )
    parts = resp.get("Items", [])
    
    if format == "json":
        return JSONResponse(content={"title": title_num, "chapters": chapters, "parts": parts})
    
    chapter_rows = []
    for chapter in chapters:
        size_mb = chapter.get('size', 0) / 1024 / 1024
        chapter_rows.append(
            f"<tr><td>{chapter.get('identifier','')}</td><td>{chapter.get('label_description','')}</td><td>{size_mb:.1f} MB</td></tr>"
        )
    
    part_rows = []
    for part in parts[:10]:  # Limit display
        size_kb = part.get('size', 0) / 1024
        part_rows.append(
            f"<tr><td>{part.get('identifier','')}</td><td>{part.get('label_description','')}</td><td>{size_kb:.0f} KB</td></tr>"
        )
    
    html = (
        HTML_PAGE.format(env=PROJECT_ENV)
        + f"<h2>CFR Title {title_num} Structure</h2>"
        + f"<h3>Chapters ({len(chapters)})</h3>"
        + "<table><tr><th>Chapter</th><th>Description</th><th>Size</th></tr>"
        + ("".join(chapter_rows) or "<tr><td colspan=3>No chapters found</td></tr>")
        + "</table>"
        + f"<h3>Parts (showing first 10 of {len(parts)})</h3>"
        + "<table><tr><th>Part</th><th>Description</th><th>Size</th></tr>"
        + ("".join(part_rows) or "<tr><td colspan=3>No parts found</td></tr>")
        + "</table>"
        + FOOTER.format(year=datetime.utcnow().year)
    )
    return HTMLResponse(content=html)

@app.get("/agency/cfr")
async def agency_cfr(request: Request, agency_slug: str, format: str = "html"):
    _auth_or_403(request)
    
    # Get agency metadata
    resp = table.query(
        KeyConditionExpression=Key('pk').eq(f'AGENCY#{agency_slug}') & Key('sk').eq('METADATA')
    )
    agency_items = resp.get("Items", [])
    agency = agency_items[0] if agency_items else None
    
    if not agency:
        return JSONResponse({"error": "Agency not found"}, status_code=404)
    
    # Get CFR title mappings
    resp = table.query(
        KeyConditionExpression=Key('pk').eq(f'AGENCY#{agency_slug}') & Key('sk').begins_with('TITLE#')
    )
    mappings = resp.get("Items", [])
    
    if format == "json":
        return JSONResponse(content={"agency": agency, "cfr_coverage": mappings})
    
    mapping_rows = []
    for mapping in mappings:
        mapping_rows.append(
            f"<tr><td>{mapping.get('title_number','')}</td><td>{mapping.get('chapter','')}</td></tr>"
        )
    
    html = (
        HTML_PAGE.format(env=PROJECT_ENV)
        + f"<h2>{agency.get('name', agency_slug)} - CFR Coverage</h2>"
        + f"<p><strong>Short Name:</strong> {agency.get('short_name', '')}</p>"
        + "<table><tr><th>CFR Title</th><th>Chapter</th></tr>"
        + ("".join(mapping_rows) or "<tr><td colspan=2>No CFR coverage found</td></tr>")
        + "</table>"
        + FOOTER.format(year=datetime.utcnow().year)
    )
    return HTMLResponse(content=html)


@app.get("/api/search")
async def search_cfr(request: Request, 
                     entity_type: Optional[str] = None,
                     title_num: Optional[int] = None,
                     agency_slug: Optional[str] = None,
                     limit: int = 25):
    _auth_or_403(request)
    
    filter_conditions = []
    if entity_type:
        filter_conditions.append(Attr('entity_type').eq(entity_type))
    
    scan_kwargs = {'Limit': limit}
    if filter_conditions:
        if len(filter_conditions) == 1:
            scan_kwargs['FilterExpression'] = filter_conditions[0]
        else:
            scan_kwargs['FilterExpression'] = filter_conditions[0]
            for condition in filter_conditions[1:]:
                scan_kwargs['FilterExpression'] = scan_kwargs['FilterExpression'] & condition
    
    if title_num and not agency_slug:
        # Query specific title
        resp = table.query(
            KeyConditionExpression=Key('pk').eq(f'TITLE#{title_num}'),
            Limit=limit
        )
    elif agency_slug and not title_num:
        # Query specific agency
        resp = table.query(
            KeyConditionExpression=Key('pk').eq(f'AGENCY#{agency_slug}'),
            Limit=limit
        )
    else:
        # General scan
        resp = table.scan(**scan_kwargs)
    
    items = resp.get("Items", [])
    return JSONResponse(content={
        "items": items,
        "count": len(items),
        "filters_applied": {
            "entity_type": entity_type,
            "title_num": title_num,
            "agency_slug": agency_slug
        }
    })


# Health check endpoint
@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

handler = Mangum(app)