from pathlib import Path

import pytest

from app import app as webapp

DUMMY = str(Path(__file__).parent.parent / "app" / "dummy_jobs.csv")


@pytest.fixture
def rows():
    webapp._cache.update(source=None, rows=None, time=0.0)
    return webapp.load_rows(DUMMY)


@pytest.fixture
def client(monkeypatch):
    webapp._cache.update(source=None, rows=None, time=0.0)
    monkeypatch.setenv("JOBS_CSV", DUMMY)
    return webapp.app.test_client()


@pytest.mark.parametrize("places,expected", [
    ((), 6), (["Portland"], 2), (["Seattle"], 2), (["Remote"], 2), (["Portland", "Remote"], 4),
])
def test_place_filter_counts(rows, places, expected):
    assert len(webapp.filter_rows(rows, places)) == expected


def test_skill_and_source_filters(rows):
    assert {r["job_id"] for r in webapp.filter_rows(rows, skill="Python")} == \
        {"usajobs:1", "usajobs:3", "greenhouse:5"}
    assert len(webapp.filter_rows(rows, source="greenhouse")) == 2
    assert len(webapp.filter_rows(rows, ["Remote"], "Python", "greenhouse")) == 1


def test_sorted_newest_first(rows):
    dates = [r["date_posted"] for r in webapp.filter_rows(rows)]
    assert dates == sorted(dates, reverse=True)


def test_page_renders_with_filters(client):
    page = client.get("/?place=Seattle&skill=SQL").get_data(as_text=True)
    assert "Showing 1 of 6 jobs" in page and "Data Analyst" in page


def test_falls_back_to_last_copy(rows, monkeypatch):
    webapp._cache["time"] = 0.0  # cache expired
    monkeypatch.setattr(webapp, "_read", lambda s: (_ for _ in ()).throw(ConnectionError()))
    assert webapp.load_rows(DUMMY) == rows
