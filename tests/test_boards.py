import pytest

from collector import boards


def gh_item(job_id=1, location="Portland, OR"):
    return {
        "id": job_id, "title": "Software Engineer", "company_name": "Jama Software",
        "location": {"name": location},
        "absolute_url": f"https://job-boards.greenhouse.io/jamasoftware/jobs/{job_id}",
        "updated_at": "2026-10-28T12:23:39-04:00",
        "first_published": "2026-09-15T10:00:00-04:00",
        "content": "&lt;p&gt;Build &amp;amp; ship &lt;strong&gt;Python&lt;/strong&gt; services.&lt;/p&gt;",
    }


class FakeResp:
    def __init__(self, status, jobs):
        self.status, self.jobs = status, jobs

    def raise_for_status(self):
        if self.status != 200:
            raise RuntimeError(self.status)

    def json(self):
        return {"jobs": self.jobs, "meta": {"total": len(self.jobs)}}


class FakeSession:
    def get(self, url, params, timeout):
        if "badslug" in url:
            return FakeResp(404, [])
        if "empty" in url:
            return FakeResp(200, [])
        return FakeResp(200, [gh_item(1), gh_item(2, "Remote, United States")])


def test_parse_uses_first_published_and_strips_html():
    job = boards.parse_greenhouse(gh_item(), "Jama Software")
    assert job["job_id"] == "greenhouse:1"
    assert job["date_posted"] == "2026-09-15"  # not updated_at
    assert job["text"] == "Build & ship Python services."
    assert job["salary"] == "" and job["remote"] is False
    assert job["cities"] == ["Portland, OR"]


@pytest.mark.parametrize("location,expected", [
    ("Remote, United States", True), ("Remote", True), ("Remote - US", True),
    ("Remote, Canada; Remote, United States", True), ("Remote, Poland", False),
    ("Remote, Canada", False), ("Portland, OR", False), ("Portland, OR; Remote, USA", True),
])
def test_is_us_remote(location, expected):
    assert boards.is_us_remote(boards.location_parts(location)) is expected


def test_fetch_all_skips_bad_slug_and_accepts_empty_board():
    companies = [{"name": "A", "source": "greenhouse", "slug": "good"},
                 {"name": "B", "source": "greenhouse", "slug": "badslug"},
                 {"name": "C", "source": "greenhouse", "slug": "empty"}]
    jobs, failed = boards.fetch_all(companies, FakeSession())
    assert failed == 1 and len(jobs) == 2


def lever_item(**overrides):
    item = {
        "id": "abc-123", "text": "Forward Deployed Engineer", "country": "US",
        "workplaceType": "hybrid", "createdAt": 1786469891368,
        "categories": {"location": "Seattle, WA", "allLocations": ["Seattle, WA", "New York, NY"]},
        "descriptionPlain": "Build Python services.\n",
        "lists": [{"text": "Requirements", "content": "<li>Kubernetes &amp; SQL</li>"}],
        "additionalPlain": "Benefits.",
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "salaryRange": {"min": 80000, "max": 165000, "currency": "USD",
                        "interval": "per-year-salary"},
    }
    return {**item, **overrides}


def test_parse_lever_maps_fields():
    job = boards.parse_lever(lever_item(), "Acme")
    assert job["job_id"] == "lever:abc-123" and job["source"] == "lever"
    assert job["title"] == "Forward Deployed Engineer" and job["company"] == "Acme"
    assert job["location"] == "Seattle, WA; New York, NY"
    assert job["cities"] == ["Seattle, WA", "New York, NY"]
    assert job["date_posted"] == "2026-08-11"
    assert job["salary"] == "$80,000-$165,000 per year"
    assert job["url"] == "https://jobs.lever.co/acme/abc-123"
    assert job["summary"] == "Build Python services.\n"
    assert "Kubernetes & SQL" in job["text"] and "Benefits." in job["text"]


@pytest.mark.parametrize("workplace,country,place,expected", [
    ("remote", "US", "Seattle, WA", True), ("remote", "IN", "Hyderabad", False),
    ("hybrid", "US", "Seattle, WA", False), ("onsite", "US", "Seattle, WA", False),
    ("unspecified", "US", "Remote, United States", True),
    ("unspecified", "US", "Baltimore, MD", False),
])
def test_lever_remote(workplace, country, place, expected):
    item = lever_item(workplaceType=workplace, country=country,
                      categories={"location": place, "allLocations": [place]})
    assert boards.parse_lever(item, "Acme")["remote"] is expected


def test_lever_leaves_foreign_cities_out_of_metro_matching():
    item = lever_item(country="CA", categories={"location": "Vancouver"})
    job = boards.parse_lever(item, "Acme")
    assert job["cities"] == [] and job["location"] == "Vancouver"


@pytest.mark.parametrize("salary,expected", [
    (None, ""), ({"min": 40, "max": 40, "currency": "USD", "interval": "per-hour-wage"},
                 "$40 per hour"),
    ({"min": 50000, "max": 60000, "currency": "GBP", "interval": "per-year-salary"},
     "GBP 50,000-GBP 60,000 per year"),
    ({"currency": "USD"}, ""),
])
def test_lever_salary(salary, expected):
    assert boards._lever_salary(salary) == expected


def test_lever_missing_fields_stay_blank():
    job = boards.parse_lever({"id": "x"}, "Acme")
    assert job["salary"] == job["date_posted"] == job["url"] == job["location"] == ""
    assert job["remote"] is False


class HeaderResp:
    def __init__(self, content_type, body):
        self.headers, self.body = {"content-type": content_type}, body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class ScriptedSession:
    """Returns the given responses in order and records the calls."""

    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        return self.responses.pop(0)


def test_fetch_lever_retries_once_after_html():
    session = ScriptedSession(HeaderResp("text/html", None),
                              HeaderResp("application/json; charset=utf-8", [lever_item()]))
    jobs = boards.fetch_lever("acme", "Acme", session)
    assert len(jobs) == 1 and len(session.calls) == 2
    assert session.calls[0] == ("https://api.lever.co/v0/postings/acme", {"mode": "json"})


def test_fetch_lever_html_twice_counts_as_a_failed_board():
    session = ScriptedSession(HeaderResp("text/html", None), HeaderResp("text/html", None))
    jobs, failed = boards.fetch_all([{"name": "A", "source": "lever", "slug": "a"}], session)
    assert jobs == [] and failed == 1


def ashby_address(city, region, country):
    return {"postalAddress": {"addressLocality": city, "addressRegion": region,
                              "addressCountry": country}}


def ashby_item(**overrides):
    item = {
        "id": "def-456", "title": "Data Engineer", "location": "US-WA-Bellevue",
        "secondaryLocations": [{"location": "NYC (SoHo)",
                                "address": ashby_address("New York City", "New York",
                                                         "United States")}],
        "address": ashby_address("Bellevue", "Washington", "USA"),
        "isListed": True, "isRemote": True, "workplaceType": "Hybrid",
        "publishedAt": "2026-11-05T02:20:02.702+00:00",
        "jobUrl": "https://jobs.ashbyhq.com/acme/def-456",
        "descriptionPlain": "Write SQL.",
        "compensation": {"scrapeableCompensationSalarySummary": "$207K - $285K",
                         "compensationTierSummary": "$207K – $285K • Offers Equity"},
    }
    return {**item, **overrides}


def test_parse_ashby_maps_fields_and_hybrid_is_not_remote():
    job = boards.parse_ashby(ashby_item(), "Acme")
    assert job["job_id"] == "ashby:def-456" and job["source"] == "ashby"
    assert job["remote"] is False  # isRemote is true on Hybrid jobs
    assert job["location"] == "US-WA-Bellevue; NYC (SoHo)"
    assert job["cities"] == ["Bellevue, Washington", "New York City, New York"]
    assert job["salary"] == "$207K - $285K"
    assert job["date_posted"] == "2026-11-05"
    assert job["url"] == "https://jobs.ashbyhq.com/acme/def-456"
    assert job["text"] == "Write SQL."


@pytest.mark.parametrize("workplace,location,country,expected", [
    ("Remote", "Remote - US", "United States", True), ("Remote", "New York", "USA", True),
    ("Remote", "Remote - United Kingdom", "United Kingdom", False),
    ("Remote", "Toronto", "Canada", False), ("OnSite", "Seattle", "USA", False),
    ("Hybrid", "US - Remote", "United States", False),
    (None, "US-WA-Seattle-Remote", "", True), (None, "PL-Poland-Remote", "", False),
    (None, "San Francisco", "", False),
])
def test_ashby_remote(workplace, location, country, expected):
    item = ashby_item(workplaceType=workplace, location=location, secondaryLocations=[],
                      address=ashby_address("", "", country))
    assert boards.parse_ashby(item, "Acme")["remote"] is expected


def test_ashby_remote_when_only_a_secondary_location_is_us():
    item = ashby_item(workplaceType="Remote", location="Toronto",
                      address=ashby_address("Toronto", "Ontario", "Canada"))
    job = boards.parse_ashby(item, "Acme")
    assert job["remote"] is True
    assert job["cities"] == ["New York City, New York"]  # Toronto is left out


def test_ashby_city_falls_back_to_location_text_without_an_address():
    item = ashby_item(location="Seattle", secondaryLocations=[], address=None)
    assert boards.parse_ashby(item, "Acme")["cities"] == ["Seattle"]


def test_ashby_salary_falls_back_to_tier_summary_and_blank():
    hourly = {"scrapeableCompensationSalarySummary": None,
              "compensationTierSummary": "$40 – $47 per hour"}
    assert boards.parse_ashby(ashby_item(compensation=hourly), "A")["salary"] == "$40 – $47 per hour"
    assert boards.parse_ashby(ashby_item(compensation={}), "A")["salary"] == ""


def test_fetch_ashby_requests_compensation_and_skips_unlisted():
    body = {"jobs": [ashby_item(), ashby_item(id="hidden", isListed=False)]}
    session = ScriptedSession(HeaderResp("application/json", body))
    jobs = boards.fetch_ashby("Acme", "Acme", session)
    assert [j["job_id"] for j in jobs] == ["ashby:def-456"]
    assert session.calls == [("https://api.ashbyhq.com/posting-api/job-board/Acme",
                              {"includeCompensation": "true"})]


def test_every_configured_company_has_a_fetcher():
    assert {c["source"] for c in boards.load_companies()} <= set(boards.FETCHERS)


def test_companies_config_has_jama():
    assert {"name": "Jama Software", "source": "greenhouse", "slug": "jamasoftware"} \
        in boards.load_companies()
