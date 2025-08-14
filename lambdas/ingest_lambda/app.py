import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any

import boto3
import requests

table_name = os.environ["DDB_TABLE"]
ecfr_base = os.environ.get("ECFR_BASE_URL", "https://www.ecfr.gov/api")

ddb = boto3.resource("dynamodb")
table = ddb.Table(table_name)

def fetch_agencies() -> Dict[str, Any]:
    url = f"{ecfr_base}/admin/v1/agencies.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_titles() -> Dict[str, Any]:
    url = f"{ecfr_base}/versioner/v1/titles.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_title_structure(title_num: int, date: str = "2024-01-01") -> Dict[str, Any]:
    url = f"{ecfr_base}/versioner/v1/structure/{date}/title-{title_num}.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def compute_checksum(data: Any) -> str:
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def store_agency_data(agency: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    
    item = {
        "pk": f"AGENCY#{agency['slug']}",
        "sk": "METADATA",
        "entity_type": "agency",
        "name": agency["name"],
        "short_name": agency.get("short_name", ""),
        "display_name": agency["display_name"],
        "slug": agency["slug"],
        "cfr_references": agency.get("cfr_references", []),
        "updated_date": date_str,
        "checksum": compute_checksum(agency)
    }
    table.put_item(Item=item)
    return item

def store_title_data(title: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    
    item = {
        "pk": f"TITLE#{title['number']}",
        "sk": "METADATA",
        "entity_type": "title",
        "number": title["number"],
        "name": title["name"],
        "latest_amended_on": title.get("latest_amended_on"),
        "latest_issue_date": title.get("latest_issue_date"),
        "up_to_date_as_of": title.get("up_to_date_as_of"),
        "reserved": title.get("reserved", False),
        "updated_date": date_str,
        "checksum": compute_checksum(title)
    }
    table.put_item(Item=item)
    return item

def store_title_structure(title_num: int, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    stored_items = []
    
    def process_node(node: Dict[str, Any], parent_path: str = ""):
        current_path = f"{parent_path}/{node['identifier']}" if parent_path else node['identifier']
        
        item = {
            "pk": f"TITLE#{title_num}",
            "sk": f"{node['type'].upper()}#{current_path}",
            "entity_type": node['type'],
            "identifier": node['identifier'],
            "label": node['label'],
            "label_level": node.get('label_level', ''),
            "label_description": node.get('label_description', ''),
            "reserved": node.get('reserved', False),
            "size": node.get('size', 0),
            "volumes": node.get('volumes', []),
            "path": current_path,
            "updated_date": date_str,
            "checksum": compute_checksum(node)
        }
        
        table.put_item(Item=item)
        stored_items.append(item)
        
        for child in node.get('children', []):
            process_node(child, current_path)
    
    process_node(structure)
    return stored_items

def create_agency_title_mapping(agency: Dict[str, Any]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    mappings = []
    
    for cfr_ref in agency.get('cfr_references', []):
        title_num = cfr_ref.get('title')
        if title_num:
            item = {
                "pk": f"AGENCY#{agency['slug']}",
                "sk": f"TITLE#{title_num}",
                "entity_type": "agency_title_mapping",
                "agency_slug": agency['slug'],
                "agency_name": agency['name'],
                "title_number": title_num,
                "chapter": cfr_ref.get('chapter', ''),
                "updated_date": date_str
            }
            table.put_item(Item=item)
            mappings.append(item)
    
    return mappings


def handler(event, context):
    try:
        ingested_counts = {
            "agencies": 0,
            "titles": 0,
            "structures": 0,
            "mappings": 0
        }
        
        # Fetch and store agency data
        agencies_data = fetch_agencies()
        agencies = agencies_data.get("agencies", [])
        
        for agency in agencies[:10]:  # Limit for demo
            store_agency_data(agency)
            mappings = create_agency_title_mapping(agency)
            ingested_counts["agencies"] += 1
            ingested_counts["mappings"] += len(mappings)
        
        # Fetch and store title metadata
        titles_data = fetch_titles()
        titles = titles_data.get("titles", [])
        
        for title in titles[:5]:  # Limit for demo
            store_title_data(title)
            ingested_counts["titles"] += 1
            
            # Fetch and store structure for major titles
            if title["number"] in [40, 21, 29, 7]:  # EPA, FDA, Labor, Agriculture
                try:
                    structure = fetch_title_structure(title["number"])
                    stored_structures = store_title_structure(title["number"], structure)
                    ingested_counts["structures"] += len(stored_structures)
                except Exception as e:
                    print(f"Failed to fetch structure for title {title['number']}: {e}")
        
        return {
            "ok": True,
            "message": "Successfully ingested eCFR data",
            "counts": ingested_counts
        }
        
    except Exception as e:
        return {
            "ok": False,
            "message": f"Ingestion failed: {str(e)}",
            "error": str(e)
        }