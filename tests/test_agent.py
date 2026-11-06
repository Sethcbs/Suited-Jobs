"""The agent loop against a fake Claude client. No test here calls the real API."""
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS

import anthropic
import httpx2
import pytest

from app import agent
from app import app as webapp
from app.tools import JobTools
from collector import skills
from tests.helpers import make_pdf

DUMMY = str(Path(__file__).parent.parent / "app" / "dummy_jobs.csv")


def row(job_id, job_skills, title="Engineer"):
    return {"job_id": job_id, "title": title, "company": "Acme", "location": "Portland, OR",
            "metro": "Portland", "remote": "false", "salary": "$1", "skills": "|".join(job_skills),
            "url": f"https://example.com/{job_id}", "description_snippet": "Text.",
            "date_posted": "2026-10-01", "source": "lever", "date_fetched": "2026-11-06"}


@pytest.fixture
def tools():
    rows = [row("a", ["Python", "AWS", "Docker"]), row("b", ["Python", "AWS"]), row("c", ["Java"])]
    return JobTools(rows, "Python developer", skills.load())


def usage():
    return NS(input_tokens=100, output_tokens=10, cache_read_input_tokens=50,
              cache_creation_input_tokens=5)


def use(name, call_id="t1", **args):
    return NS(type="tool_use", id=call_id, name=name, input=args)


def called(*blocks):
    return NS(stop_reason="tool_use", content=list(blocks), usage=usage(), _request_id="req")


def answered(matches=(), assessment="Good fit.", guidance=("Lead with Python.",)):
    text = json.dumps({"matches": list(matches), "assessment": assessment, "guidance": list(guidance)})
    thinking = NS(type="thinking", thinking="", signature="sig")
    return NS(stop_reason="end_turn", content=[thinking, NS(type="text", text=text)],
              usage=usage(), _request_id="req")


class FakeClient:
    """Plays back responses and records each request, including the messages at that moment."""

    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def run(tools, *responses, model="claude-opus-5-5"):
    client = FakeClient(*responses)
    return agent.run_agent(tools, "Python developer", ["Portland"],
                           agent.ClaudeAdapter(client, model)), client


def test_full_loop_runs_tools_and_returns_checked_matches(tools):
    result, client = run(
        tools,
        called(use("get_skills")),
        called(use("search_jobs", skills=["Python"])),
        called(use("get_job", job_id="a")),
        answered([{"job_id": "a", "reason": "Uses Python."}]))
    assert len(client.requests) == 4
    match = result["matches"][0]
    assert match["url"] == "https://example.com/a" and match["reason"] == "Uses Python."
    assert match["matching_skills"] == ["Python"] and match["missing_skills"] == ["AWS", "Docker"]
    assert result["assessment"] == "Good fit." and result["guidance"] == ["Lead with Python."]
    assert result["usage"] == {"input": 400, "output": 40, "cache_read": 200, "cache_write": 20}


def test_tool_results_go_back_to_the_model(tools):
    _, client = run(tools, called(use("get_skills", "t9")), answered())
    assistant, results = client.requests[1]["messages"][1:]
    assert assistant["role"] == "assistant" and assistant["content"][0].id == "t9"
    block = results["content"][0]
    assert block["tool_use_id"] == "t9" and block["is_error"] is False
    assert json.loads(block["content"]) == {"skills": [{"skill": "Python", "mentions": 1}]}


def test_parallel_tool_calls_return_in_one_user_message(tools):
    _, client = run(tools, called(use("get_job", "t1", job_id="a"), use("get_job", "t2", job_id="b")),
                    answered())
    results = client.requests[1]["messages"][2]
    assert [b["tool_use_id"] for b in results["content"]] == ["t1", "t2"]


def test_unknown_job_and_tool_return_errors_to_the_model(tools):
    _, client = run(tools, called(use("get_job", "t1", job_id="nope"), use("delete_all", "t2")),
                    answered())
    blocks = client.requests[1]["messages"][2]["content"]
    assert [b["is_error"] for b in blocks] == [True, True]
    assert "No job has that ID" in blocks[0]["content"]


def test_invented_job_is_dropped_and_flagged(tools):
    result, _ = run(tools, answered([{"job_id": "made-up", "reason": "x"},
                                     {"job_id": "a", "reason": "y"}]))
    assert [m["job_id"] for m in result["matches"]] == ["a"]
    assert result["dropped_ids"] == ["made-up"]


def test_duplicate_matches_are_removed_and_list_is_capped(tools):
    rows = [row(str(i), ["Python"]) for i in range(15)]
    many = JobTools(rows, "Python", skills.load())
    answer = [{"job_id": str(i), "reason": "x"} for i in range(15)] + [{"job_id": "0", "reason": "x"}]
    result, _ = run(many, answered(answer))
    ids = [m["job_id"] for m in result["matches"]]
    assert len(ids) == agent.MAX_MATCHES and len(set(ids)) == len(ids)


def test_missing_common_lists_skills_in_at_least_two_matches(tools):
    result, _ = run(tools, answered([{"job_id": "a", "reason": "x"}, {"job_id": "b", "reason": "y"}]))
    assert result["missing_common"] == ["AWS"]  # Docker is in only one match


def test_missing_common_with_one_match_lists_its_missing_skills(tools):
    result, _ = run(tools, answered([{"job_id": "a", "reason": "x"}]))
    assert result["missing_common"] == ["AWS", "Docker"]


def test_loop_stops_at_the_turn_limit(tools):
    endless = [called(use("get_skills")) for _ in range(agent.MAX_TURNS + 5)]
    client = FakeClient(*endless)
    with pytest.raises(agent.AgentError, match="didn't finish"):
        agent.run_agent(tools, "x", [], agent.ClaudeAdapter(client, "claude-opus-5-5"))
    assert len(client.requests) == agent.MAX_TURNS


@pytest.mark.parametrize("stop,message", [
    ("refusal", "declined"), ("max_tokens", "cut off"), ("pause_turn", "unexpectedly")])
def test_other_stop_reasons_become_clear_errors(tools, stop, message):
    response = NS(stop_reason=stop, content=[], usage=usage(), _request_id="req")
    with pytest.raises(agent.AgentError, match=message):
        run(tools, response)


def test_unreadable_answer_is_a_clear_error(tools):
    bad = NS(stop_reason="end_turn", content=[NS(type="text", text="not json")], usage=usage(),
             _request_id="req")
    with pytest.raises(agent.AgentError, match="couldn't be read"):
        run(tools, bad)


def api_error(cls, status, message="boom"):
    response = httpx2.Response(status, request=httpx2.Request("POST", "https://api.example.com"))
    return cls(message, response=response, body=None)


@pytest.mark.parametrize("error,message", [
    (api_error(anthropic.AuthenticationError, 401), "was rejected"),
    (api_error(anthropic.RateLimitError, 429), "rate limiting"),
    (api_error(anthropic.BadRequestError, 400, "credit balance is too low"), "credit balance"),
    (api_error(anthropic.InternalServerError, 500), r"error \(500\)"),
    (anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.example.com")),
     "Couldn't reach"),
    (TypeError("Could not resolve authentication method"), "No Anthropic API key"),
])
def test_api_failures_become_clear_errors(tools, error, message):
    with pytest.raises(agent.AgentError, match=message):
        run(tools, error)


def test_unrelated_type_errors_are_not_hidden(tools):
    with pytest.raises(TypeError, match="a real bug"):
        run(tools, TypeError("a real bug"))


def test_request_settings(tools):
    _, client = run(tools, answered())
    request = client.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["betas"] == ["server-side-fallback-2026-07-01"] and request["fallbacks"] == "default"
    assert request["output_config"]["format"]["schema"] == agent.ANSWER_SCHEMA
    assert all(t["strict"] for t in request["tools"])
    assert "Python developer" in request["messages"][0]["content"]
    assert "Portland" in request["messages"][0]["content"]


def test_haiku_requests_leave_out_fallbacks(tools):
    _, client = run(tools, answered(), model="claude-haiku-5-5")
    assert "fallbacks" not in client.requests[0] and "betas" not in client.requests[0]


def test_model_can_be_set_from_the_environment(monkeypatch):
    monkeypatch.setenv("SUITED_JOBS_MODEL", "claude-sonnet-5-5")
    assert agent.ClaudeAdapter(FakeClient()).model == "claude-sonnet-5-5"


# --- the page ---
@pytest.fixture
def page_client(monkeypatch):
    webapp._cache.update(source=None, rows=None, time=0.0)
    monkeypatch.setenv("JOBS_CSV", DUMMY)
    return webapp.app.test_client()


def post(client, action="match", places=()):
    form = {"resume": (io.BytesIO(make_pdf("Python and SQL developer")), "resume.pdf"),
            "action": action, "place": list(places)}
    return client.post("/match", data=form, content_type="multipart/form-data")


def fake_result(**overrides):
    match = {"job_id": "usajobs:1", "title": "Data Engineer", "company": "Agency",
             "location": "Portland, OR", "remote": "false", "salary": "$1",
             "url": "https://example.com/1", "reason": "<b>Uses Python</b>",
             "matching_skills": ["Python"], "missing_skills": ["AWS"]}
    return {"matches": [match], "assessment": "A solid fit.", "guidance": ["Lead with Python."],
            "missing_common": ["AWS"], "dropped_ids": [],
            "usage": {"input": 1, "output": 2, "cache_read": 3, "cache_write": 4}, **overrides}


def test_page_shows_matches_guidance_and_escapes_model_text(page_client, monkeypatch):
    monkeypatch.setattr(webapp.agent, "run_agent", lambda *a: fake_result())
    page = post(page_client).get_data(as_text=True)
    assert 'href="https://example.com/1"' in page and "A solid fit." in page
    assert "Lead with Python." in page and "&lt;b&gt;Uses Python&lt;/b&gt;" in page


def test_page_flags_dropped_jobs(page_client, monkeypatch):
    monkeypatch.setattr(webapp.agent, "run_agent", lambda *a: fake_result(dropped_ids=["x", "y"]))
    assert "2 suggested jobs" in post(page_client).get_data(as_text=True)


def test_page_passes_only_chosen_places_to_the_agent(page_client, monkeypatch):
    seen = {}

    def fake_run(tools, text, places):
        seen.update(places=places, metros={r["metro"] for r in tools.rows.values()},
                    remote={r["remote"] for r in tools.rows.values()}, text=text)
        return fake_result()
    monkeypatch.setattr(webapp.agent, "run_agent", fake_run)
    post(page_client, places=["Portland"])
    assert seen["places"] == ["Portland"] and seen["metros"] == {"Portland"}
    assert "Python and SQL developer" in seen["text"]


def test_read_only_does_not_call_the_agent(page_client, monkeypatch):
    def fail(*a):
        raise AssertionError("agent should not run")
    monkeypatch.setattr(webapp.agent, "run_agent", fail)
    page = post(page_client, action="read").get_data(as_text=True)
    assert "Python and SQL developer" in page


def test_agent_error_still_shows_the_resume_text(page_client, monkeypatch):
    def fail(*a):
        raise agent.AgentError("No Anthropic API key found.")
    monkeypatch.setattr(webapp.agent, "run_agent", fail)
    page = post(page_client).get_data(as_text=True)
    assert "No Anthropic API key found." in page and "Python and SQL developer" in page


def test_no_jobs_in_chosen_places_skips_the_model(page_client, monkeypatch):
    def fail(*a):
        raise AssertionError("agent should not run")
    monkeypatch.setattr(webapp.agent, "run_agent", fail)
    monkeypatch.setattr(webapp, "filter_rows", lambda *a: [])
    assert "No jobs are available" in post(page_client).get_data(as_text=True)


def test_collector_does_not_use_ai():  # NFR-2
    for path in (Path(__file__).parent.parent / "collector").glob("*.py"):
        assert "anthropic" not in path.read_text().lower(), path.name
