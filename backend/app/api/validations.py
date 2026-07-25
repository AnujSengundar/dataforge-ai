import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.schemas.validation import (
    PaginatedQuarantine,
    PaginatedValidationResults,
    QuarantinedRowResponse,
    ValidationResultResponse,
    ValidationRunResponse,
)
from backend.app.services.validation_service import (
    ValidationError,
    get_validation_run,
    list_quarantined_rows,
    list_validation_results,
    run_validation,
)


router = APIRouter(tags=["validations"])


@router.post(
    "/datasets/{dataset_id}/versions/{version_id}/validate",
    response_model=ValidationRunResponse,
)
def validate(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ValidationRunResponse:
    try:
        return ValidationRunResponse.model_validate(
            run_validation(db, dataset_id=dataset_id, version_id=version_id, settings=settings)
        )
    except ValidationError as exc:
        code = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.get("/validation-runs/{run_id}", response_model=ValidationRunResponse)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> ValidationRunResponse:
    run = get_validation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")
    return ValidationRunResponse.model_validate(run)


@router.get(
    "/validation-runs/{run_id}/results", response_model=PaginatedValidationResults
)
def results(
    run_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedValidationResults:
    if get_validation_run(db, run_id) is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")
    items, total = list_validation_results(db, run_id, limit=limit, offset=offset)
    return PaginatedValidationResults(
        items=[ValidationResultResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/validation-runs/{run_id}/quarantine", response_model=PaginatedQuarantine)
def quarantine(
    run_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedQuarantine:
    if get_validation_run(db, run_id) is None:
        raise HTTPException(status_code=404, detail="Validation run not found.")
    items, total = list_quarantined_rows(db, run_id, limit=limit, offset=offset)
    return PaginatedQuarantine(
        items=[QuarantinedRowResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
