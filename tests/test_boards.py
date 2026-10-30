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


def test_companies_config_has_jama():
    assert {"name": "Jama Software", "source": "greenhouse", "slug": "jamasoftware"} \
        in boards.load_companies()
