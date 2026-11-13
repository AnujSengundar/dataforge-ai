from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.database import get_db
from backend.turning_point import investigator
from backend.turning_point.cases import CASES
from backend.turning_point.investigator import Finding, Plan, investigate
from backend.turning_point.main import app
from backend.turning_point.storage import Investigation


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Investigation.__table__.create(engine)

    def db() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    def offline(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(investigator, "ask", offline)
    app.dependency_overrides[get_db] = db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_cricket_totals_and_final_equation():
    case = CASES["eden-gardens-2016"]
    assert len(case.events) == 124
    assert "161/6; 2 legal balls left" in case.events[-1].text
    assert case.events[-5].value == 19
    assert [event.label for event in case.events[-4:]] == ["19.1", "19.2", "19.3", "19.4"]
    assert "24 in the final over" in case.tools["scoring_windows"][-1].text


def test_review_retains_original_and_resolves_citations(client: TestClient):
    catalog = client.get("/api/cases").json()
    assert len(catalog) == 3
    case = catalog[0]
    path = f"/api/cases/{case['id']}"
    events = {event["id"] for event in client.get(path).json()["events"]}
    response = client.post(path + "/investigations", json={"claim": case["claim"]})
    assert response.status_code == 201
    initial = response.json()
    assert initial["model"] == "evidence-only"
    review_url = f"/api/investigations/{initial['id']}/challenge"
    review = client.post(review_url).json()
    assert review["parent_id"] == initial["id"]
    assert review["source_version"] == case["source_version"]
    assert review["conflicting"][0]["id"] == "earlier-window"
    assert not review["changed"]
    for fact in initial["supporting"] + review["supporting"] + review["conflicting"]:
        assert set(fact["refs"]) <= events


def test_unknown_claim_and_missing_timing(client: TestClient):
    result = client.post(
        "/api/cases/monaco-2021/investigations",
        json={"claim": "What was Vettel's exact gap to Gasly on rejoin?"},
    ).json()
    assert result["verdict"] == "insufficient"
    assert "exact gaps" in result["limitations"]
    assert client.get("/api/cases/missing").status_code == 404


def test_spoiler_boundary_on_tools_and_api(client: TestClient):
    path = "/api/cases/liore-reveal"
    assert len(client.get(path).json()["events"]) == 2
    assert len(client.get(path, params={"level": 2}).json()["events"]) == 4
    case = CASES["liore-reveal"]
    result = client.post(path + "/investigations", json={"claim": case.claim}).json()
    assert {f["id"] for f in result["supporting"]} == {"opening-order"}
    review = client.post(f"/api/investigations/{result['id']}/challenge").json()
    assert {f["id"] for f in review["conflicting"]} == {"different-context"}


def test_invalid_or_hidden_citations_rejected(monkeypatch: pytest.MonkeyPatch):
    case = CASES["liore-reveal"]

    def answer(schema, *_):
        if schema is Plan:
            return Plan(tools=["clue_order"])
        return Finding(verdict="supported", supporting=["liore-context"], conflicting=[])

    monkeypatch.setattr(investigator, "ask", answer)
    result = investigate(case, case.claim, 1)
    assert result.model == "evidence-only"
    assert all(f.level == 1 for f in result.supporting)


def test_model_can_revise_verdict_and_must_use_counter_tool(monkeypatch: pytest.MonkeyPatch):
    case = CASES["monaco-2021"]

    def answer(schema, _instruction, data):
        if schema is Plan:
            return Plan(tools=["pit_window"])
        if data["previous"]:
            assert "not-stop-speed" in {fact["id"] for fact in data["facts"]}
            return Finding(verdict="contradicted", supporting=[], conflicting=["not-stop-speed"])
        return Finding(verdict="supported", supporting=["overcut"], conflicting=[])

    monkeypatch.setattr(investigator, "ask", answer)
    initial = investigate(case, "Vettel's stop was faster than Hamilton's.", 1)
    review = investigate(case, "Vettel's stop was faster than Hamilton's.", 1, initial)
    assert initial.model != "evidence-only"
    assert review.changed
    assert review.verdict == "contradicted"
