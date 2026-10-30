"""USAJOBS collector. Docs: https://developer.usajobs.gov/

Findings from real responses (Oct 30, 2026):
- LocationName=Remote resolves to the town of Remote, Oregon, so the remote
  search uses RemoteIndicator=True instead.
- City searches also return nationwide remote jobs, so remote/metro must come
  from each job's own fields, not from which search found it.
"""
import logging
import os

import requests

API_URL = "https://data.usajobs.gov/api/search"
PAGE_SIZE = 500  # API maximum
MAX_PAGES = 3

SEARCHES = {
    "Portland": {"LocationName": "Portland, Oregon"},
    "Seattle": {"LocationName": "Seattle, Washington"},
    "Remote": {"RemoteIndicator": "True"},
}

# Detail fields joined into the text used for skill matching
TEXT_FIELDS = ["JobSummary", "MajorDuties", "QualificationSummary",
               "Requirements", "Education", "KeyRequirements"]

log = logging.getLogger(__name__)


def _headers():
    # Values come from the environment only; never log them.
    return {
        "Host": "data.usajobs.gov",
        "User-Agent": os.environ["USAJOBS_USER_AGENT_EMAIL"],
        "Authorization-Key": os.environ["USAJOBS_API_KEY"],
    }


def _salary(remuneration):
    if not remuneration:
        return ""
    pay = remuneration[0]
    lo, hi = pay.get("MinimumRange", ""), pay.get("MaximumRange", "")
    if not lo and not hi:
        return ""
    rng = f"${lo}-${hi}" if lo != hi else f"${lo}"
    return f"{rng} {pay.get('Description', '')}".strip()


def _text(details):
    parts = []
    for field in TEXT_FIELDS:
        value = details.get(field) or ""
        parts.extend(value if isinstance(value, list) else [value])
    return "\n".join(p for p in parts if p)


def parse_item(item):
    """Turn one SearchResultItem into a flat job dict (see schema.py)."""
    m = item["MatchedObjectDescriptor"]
    details = m.get("UserArea", {}).get("Details", {})
    return {
        "job_id": f"usajobs:{item['MatchedObjectId']}",
        "source": "usajobs",
        "title": m.get("PositionTitle", ""),
        "company": m.get("OrganizationName", ""),
        "location": m.get("PositionLocationDisplay", ""),
        "cities": [loc.get("CityName", "") for loc in m.get("PositionLocation", [])],
        "remote": details.get("RemoteIndicator") is True,
        "salary": _salary(m.get("PositionRemuneration")),
        "url": m.get("PositionURI", ""),
        "summary": details.get("JobSummary", ""),
        "text": _text(details),
        "date_posted": (m.get("PublicationStartDate") or "")[:10],
    }


def search(params, session=requests):
    """Page through one search, newest first. Returns parsed jobs."""
    jobs = []
    for page in range(1, MAX_PAGES + 1):
        query = {**params, "ResultsPerPage": PAGE_SIZE, "Page": page,
                 "SortField": "opendate", "SortDirection": "Desc"}
        resp = session.get(API_URL, params=query, headers=_headers(), timeout=60)
        resp.raise_for_status()
        result = resp.json()["SearchResult"]
        items = result.get("SearchResultItems", [])
        jobs.extend(parse_item(i) for i in items)
        if len(items) < PAGE_SIZE:
            break
    return jobs


def fetch_all(session=requests):
    """Run every search. Returns (jobs, number_of_failed_searches)."""
    jobs, failed = [], 0
    for name, params in SEARCHES.items():
        try:
            found = search(params, session)
            log.info("usajobs %s: %d jobs", name, len(found))
            jobs.extend(found)
        except Exception as exc:  # log and keep going with the other searches
            failed += 1
            log.error("usajobs %s failed: %s", name, type(exc).__name__)
    return jobs, failed
