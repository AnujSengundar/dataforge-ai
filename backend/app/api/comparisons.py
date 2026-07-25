import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.services.comparison_service import ComparisonError, compare_versions


router = APIRouter(prefix="/datasets/{dataset_id}/compare", tags=["comparisons"])


@router.get("")
def compare(
    dataset_id: uuid.UUID,
    base_version_id: uuid.UUID | None = Query(default=None),
    comparison_version_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        return compare_versions(
            db,
            dataset_id=dataset_id,
            settings=settings,
            base_version_id=base_version_id,
            comparison_version_id=comparison_version_id,
        )
    except ComparisonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
