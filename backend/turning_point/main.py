from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.turning_point.cases import CASES, Case
from backend.turning_point.investigator import Result, investigate
from backend.turning_point.storage import Investigation

app = FastAPI(title="Turning Point", version="0.1.0")
WEB = Path(__file__).with_name("web")
app.mount("/assets", StaticFiles(directory=WEB), name="assets")
Db = Annotated[Session, Depends(get_db)]
Level = Annotated[int, Field(ge=1, le=2)]


class Claim(BaseModel):
    claim: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=400)]
    level: Level = 1


class InvestigationResponse(Result):
    id: UUID
    parent_id: UUID | None
    source_version: str


def case_for(case_id: str) -> Case:
    if case_id not in CASES:
        raise HTTPException(404, "Case not found")
    return CASES[case_id]


def summary(case: Case) -> dict:
    return {
        "id": case.id,
        "domain": case.domain,
        "title": case.title,
        "subtitle": case.subtitle,
        "claim": case.claim,
        "source_version": case.version,
    }


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/cases")
def list_cases() -> list[dict]:
    return [summary(case) for case in CASES.values()]


@app.get("/api/cases/{case_id}")
def get_case(case_id: str, level: Annotated[int, Query(ge=1, le=2)] = 1) -> dict:
    case = case_for(case_id)
    return summary(case) | {
        "source": case.source,
        "url": case.url,
        "links": case.links if case.domain != "Adaptations" or level == 2 else (),
        "events": case.visible(level),
    }


def persist(
    db: Session, case: Case, claim: str, level: int, parent: Investigation | None = None
) -> InvestigationResponse:
    result = investigate(
        case, claim, level, Result.model_validate(parent.result) if parent else None
    )
    row = Investigation(
        case_id=case.id,
        source_version=case.version,
        claim=claim,
        level=level,
        parent_id=parent.id if parent else None,
        result=result.model_dump(),
    )
    db.add(row)
    try:
        db.flush()
        response = InvestigationResponse(
            **row.result, id=row.id, parent_id=row.parent_id, source_version=row.source_version
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, "Investigation storage unavailable") from exc
    return response


@app.post("/api/cases/{case_id}/investigations", status_code=201)
def create_investigation(case_id: str, body: Claim, db: Db) -> InvestigationResponse:
    return persist(db, case_for(case_id), body.claim, body.level)


@app.post("/api/investigations/{investigation_id}/challenge", status_code=201)
def challenge(investigation_id: UUID, db: Db) -> InvestigationResponse:
    try:
        previous = db.get(Investigation, investigation_id)
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Investigation storage unavailable") from exc
    if previous is None:
        raise HTTPException(404, "Investigation not found")
    if previous.parent_id:
        raise HTTPException(409, "Challenge the original investigation")
    case = case_for(previous.case_id)
    if previous.source_version != case.version:
        raise HTTPException(409, "Case evidence has changed. Start a new investigation.")
    return persist(db, case, previous.claim, previous.level, previous)
