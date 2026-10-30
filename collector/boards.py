"""Company job board collectors (public APIs, no key). Companies: config/companies.yml

Greenhouse findings from real responses (Oct 30, 2026):
- Each job has first_published; updated_at is reset in bulk, so date_posted
  uses first_published.
- No remote flag. Location text looks like "Remote, United States" or
  "Remote, Canada; Portland, OR" (parts separated by "; ").
- content is HTML that has been HTML-escaped a second time.
- jamasoftware returned an empty board (total 0), which is valid.
"""
import html
import logging
import re
from pathlib import Path

import requests
import yaml

COMPANIES_PATH = Path(__file__).parent.parent / "config" / "companies.yml"
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
US_MARKERS = re.compile(r"\b(united states|usa|us|u\.s\.?)\b", re.I)

log = logging.getLogger(__name__)


def html_to_text(raw):
    text = html.unescape(raw or "")  # undo the extra escaping first
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def location_parts(location):
    return [p.strip() for p in (location or "").split(";") if p.strip()]


def is_us_remote(parts):
    """Remote if a part says remote and names the US or no country at all."""
    for part in parts:
        if "remote" not in part.lower():
            continue
        rest = re.sub(r"remote", "", part, flags=re.I).strip(" ,-()/")
        if not rest or US_MARKERS.search(rest):
            return True
    return False


def parse_greenhouse(item, company):
    location = (item.get("location") or {}).get("name", "")
    parts = location_parts(location)
    text = html_to_text(item.get("content", ""))
    return {
        "job_id": f"greenhouse:{item['id']}",
        "source": "greenhouse",
        "title": item.get("title", ""),
        "company": item.get("company_name") or company,
        "location": location,
        "cities": parts,
        "remote": is_us_remote(parts),
        "salary": "",  # Greenhouse's board API lists no salary
        "url": item.get("absolute_url", ""),
        "summary": text,
        "text": text,
        "date_posted": (item.get("first_published") or "")[:10],
    }


def fetch_greenhouse(slug, company, session=requests):
    resp = session.get(GREENHOUSE_URL.format(slug=slug), params={"content": "true"}, timeout=60)
    resp.raise_for_status()  # a wrong slug gives 404
    return [parse_greenhouse(item, company) for item in resp.json().get("jobs", [])]


FETCHERS = {"greenhouse": fetch_greenhouse}


def load_companies(path=COMPANIES_PATH):
    return yaml.safe_load(Path(path).read_text()) or []


def fetch_all(companies, session=requests):
    """Fetch every company board. Returns (jobs, number_of_failed_boards)."""
    jobs, failed = [], 0
    for c in companies:
        try:
            found = FETCHERS[c["source"]](c["slug"], c["name"], session)
            log.info("%s %s: %d jobs", c["source"], c["slug"], len(found))
            jobs.extend(found)
        except Exception as exc:  # log and keep going with the other boards
            failed += 1
            log.error("%s %s failed: %s", c["source"], c["slug"], type(exc).__name__)
    return jobs, failed
