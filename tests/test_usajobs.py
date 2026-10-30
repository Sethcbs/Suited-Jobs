import pytest

from collector import usajobs


def make_item(obj_id="123", remote=False, city="Portland"):
    return {
        "MatchedObjectId": obj_id,
        "MatchedObjectDescriptor": {
            "PositionTitle": "IT Specialist",
            "OrganizationName": "Bonneville Power Administration",
            "PositionLocationDisplay": f"{city}, Oregon",
            "PositionLocation": [{"CityName": f"{city}, Oregon"}],
            "PositionRemuneration": [{"MinimumRange": "80000", "MaximumRange": "100000",
                                      "Description": "Per Year"}],
            "PositionURI": f"https://www.usajobs.gov:443/job/{obj_id}",
            "PublicationStartDate": "2026-10-30T00:00:00.0000",
            "UserArea": {"Details": {
                "JobSummary": "Manage Python systems.",
                "MajorDuties": ["Write SQL.", "Run Linux servers."],
                "RemoteIndicator": remote,
            }},
        },
    }


class FakeResp:
    def __init__(self, items):
        self.items = items

    def raise_for_status(self):
        pass

    def json(self):
        return {"SearchResult": {"SearchResultItems": self.items}}


class FakeSession:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def get(self, url, params, headers, timeout):
        self.calls.append(params)
        if self.fail_on and self.fail_on in params.values():
            raise ConnectionError("boom")
        return FakeResp([make_item(str(len(self.calls)))])


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv("USAJOBS_API_KEY", "test-key")
    monkeypatch.setenv("USAJOBS_USER_AGENT_EMAIL", "test@example.com")


def test_parse_item_maps_fields():
    job = usajobs.parse_item(make_item(remote=True))
    assert job["job_id"] == "usajobs:123"
    assert job["company"] == "Bonneville Power Administration"
    assert job["remote"] is True
    assert job["salary"] == "$80000-$100000 Per Year"
    assert job["date_posted"] == "2026-10-30"
    assert job["cities"] == ["Portland, Oregon"]
    assert "Write SQL." in job["text"] and "Manage Python" in job["text"]


def test_parse_item_missing_fields_stay_blank():
    item = {"MatchedObjectId": "9", "MatchedObjectDescriptor": {}}
    job = usajobs.parse_item(item)
    assert job["salary"] == "" and job["date_posted"] == "" and job["remote"] is False


def test_fetch_all_runs_three_searches_sorted_newest_first():
    session = FakeSession()
    jobs, failed = usajobs.fetch_all(session)
    assert failed == 0 and len(jobs) == 3
    assert all(c["SortField"] == "opendate" and c["SortDirection"] == "Desc" for c in session.calls)
    assert any(c.get("RemoteIndicator") == "True" for c in session.calls)


def test_one_failed_search_does_not_stop_others():
    jobs, failed = usajobs.fetch_all(FakeSession(fail_on="Seattle, Washington"))
    assert failed == 1 and len(jobs) == 2
