"""Company job board collectors (public APIs, no key). Companies: config/companies.yml

Greenhouse findings from real responses (Oct 30, 2026):
- Each job has first_published; updated_at is reset in bulk, so date_posted
  uses first_published.
- No remote flag. Location text looks like "Remote, United States" or
  "Remote, Canada; Portland, OR" (parts separated by "; ").
- content is HTML that has been HTML-escaped a second time.
- jamasoftware returned an empty board (total 0), which is valid.

Lever findings from real responses (Nov 6, 2026):
- workplaceType is remote, hybrid, onsite, or unspecified. Remote jobs can be
  anywhere ("Hyderabad", country IN), so remote also requires country US.
- createdAt is in milliseconds. salaryRange is optional, with an interval like
  per-year-salary. lists[].content is HTML, the *Plain fields are plain text.

Ashby findings from real responses (Nov 6, 2026):
- isRemote is true on Hybrid jobs too, so remote comes from workplaceType, which
  is Remote, Hybrid, OnSite, or null. Remote jobs can be outside the US.
- location text varies ("US-WA-Bellevue", "Seattle"), so cities come from
  address.postalAddress when it has them. secondaryLocations has the same shape.
"""
import html
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

COMPANIES_PATH = Path(__file__).parent.parent / "config" / "companies.yml"
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
LEVER_URL = "https://api.lever.co/v0/postings/{slug}"
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
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


def _lever_salary(salary_range):
    lo, hi = (salary_range or {}).get("min"), (salary_range or {}).get("max")
    if lo is None or hi is None:
        return ""
    currency = salary_range.get("currency", "")
    prefix = "$" if currency == "USD" else f"{currency} ".lstrip()
    amount = f"{prefix}{lo:,}" if lo == hi else f"{prefix}{lo:,}-{prefix}{hi:,}"
    # per-year-salary -> per year, per-hour-wage -> per hour
    interval = salary_range.get("interval", "").rsplit("-", 1)[0].replace("-", " ")
    return f"{amount} {interval}".strip()


def _lever_date(created_ms):
    if not created_ms:
        return ""
    return datetime.fromtimestamp(created_ms / 1000, timezone.utc).date().isoformat()


def parse_lever(item, company):
    categories = item.get("categories") or {}
    location = categories.get("location") or ""
    places = categories.get("allLocations") or ([location] if location else [])
    country = item.get("country") or ""
    workplace = item.get("workplaceType")
    if workplace == "remote":
        remote = country == "US"
    elif workplace in ("hybrid", "onsite"):
        remote = False
    else:  # unspecified: fall back to the location text
        remote = is_us_remote(places)
    sections = [item.get("descriptionPlain") or ""]
    for section in item.get("lists") or []:
        sections += [section.get("text") or "", html_to_text(section.get("content"))]
    sections.append(item.get("additionalPlain") or "")
    return {
        "job_id": f"lever:{item['id']}",
        "source": "lever",
        "title": item.get("text", ""),
        "company": company,
        "location": "; ".join(places),
        "cities": places if country in ("", "US") else [],  # keeps out Vancouver, Canada
        "remote": remote,
        "salary": _lever_salary(item.get("salaryRange")),
        "url": item.get("hostedUrl", ""),
        "summary": item.get("descriptionPlain") or "",
        "text": "\n".join(s for s in sections if s),
        "date_posted": _lever_date(item.get("createdAt")),
    }


def fetch_lever(slug, company, session=requests):
    """Lever can return HTML instead of JSON, so check the type and retry once."""
    for attempt in range(2):
        resp = session.get(LEVER_URL.format(slug=slug), params={"mode": "json"}, timeout=60)
        resp.raise_for_status()  # a wrong slug gives 404
        if "json" in resp.headers.get("content-type", "").lower():
            return [parse_lever(item, company) for item in resp.json()]
    raise ValueError("Lever returned a non-JSON response twice")


def parse_ashby(item, company):
    names, cities, countries = [], [], []
    for place in [item] + (item.get("secondaryLocations") or []):
        name = place.get("location") or ""
        address = (place.get("address") or {}).get("postalAddress") or {}
        country = address.get("addressCountry") or ""
        if name:
            names.append(name)
        if country:
            countries.append(country)
        if country and not US_MARKERS.search(country):
            continue  # keeps out Vancouver, Canada
        city, region = address.get("addressLocality"), address.get("addressRegion")
        cities.append(f"{city}, {region}" if city and region else name)
    workplace = item.get("workplaceType")
    if workplace == "Remote":
        remote = any(US_MARKERS.search(c) for c in countries)
    elif workplace is None:  # no flag: fall back to the location text
        remote = is_us_remote(names)
    else:
        remote = False
    compensation = item.get("compensation") or {}
    text = item.get("descriptionPlain") or html_to_text(item.get("descriptionHtml"))
    return {
        "job_id": f"ashby:{item['id']}",
        "source": "ashby",
        "title": item.get("title", ""),
        "company": company,
        "location": "; ".join(names),
        "cities": [c for c in cities if c],
        "remote": remote,
        # The salary summary leaves out equity, but hourly jobs only have the tier summary
        "salary": compensation.get("scrapeableCompensationSalarySummary")
        or compensation.get("compensationTierSummary") or "",
        "url": item.get("jobUrl", ""),
        "summary": text,
        "text": text,
        "date_posted": (item.get("publishedAt") or "")[:10],
    }


def fetch_ashby(slug, company, session=requests):
    resp = session.get(ASHBY_URL.format(slug=slug), params={"includeCompensation": "true"},
                       timeout=60)
    resp.raise_for_status()  # a wrong or wrong-case board name gives 404
    return [parse_ashby(item, company) for item in resp.json().get("jobs", [])
            if item.get("isListed") is not False]


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


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
