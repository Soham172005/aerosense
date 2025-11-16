# aqi_app/utils/gdelt.py
import logging
from typing import List, Dict, Any
import requests
import csv
import io

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

def fetch_gdelt_articles(
    query: str = "air pollution OR air quality OR wildfire OR smoke OR environment",
    max_items: int = 50,
    timeout: int = 10
) -> List[Dict[str, Any]]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",   # GDELT *should* return JSON, but may return CSV
        "maxrecords": max_items
    }

    try:
        resp = requests.get(GDELT_URL, params=params, timeout=timeout)
    except Exception as e:
        logger.exception("Network error contacting GDELT")
        return []

    content_type = resp.headers.get("Content-Type", "").lower()

    # -------------------------------------------------------
    # CASE 1 — JSON (ideal)
    # -------------------------------------------------------
    if "application/json" in content_type:
        try:
            data = resp.json()
            items = data.get("articles") or data.get("articlesArray") or []
        except Exception:
            logger.exception("Invalid JSON returned by GDELT")
            return []

        return [
            {
                "title": item.get("title", ""),
                "summary": item.get("excerpt", item.get("summary", "")),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "published_at": item.get("seendate") or item.get("date"),
                "raw": item,
            }
            for item in items
        ]

    # -------------------------------------------------------
    # CASE 2 — CSV (very common)
    # -------------------------------------------------------
    if "text/csv" in content_type or resp.text.startswith("url,"):
        csv_file = io.StringIO(resp.text)
        reader = csv.DictReader(csv_file)

        articles = []
        for row in reader:
            articles.append({
                "title": row.get("title", ""),
                "summary": row.get("excerpt", ""),
                "url": row.get("url", ""),
                "source": row.get("domain", ""),
                "published_at": row.get("seendate", ""),
                "raw": row,
            })

        return articles

    # -------------------------------------------------------
    # CASE 3 — HTML or empty (GDELT error)
    # -------------------------------------------------------
    logger.error("GDELT returned non-JSON, non-CSV. First 200 chars:\n%s", resp.text[:200])
    return []
