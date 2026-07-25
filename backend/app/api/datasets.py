import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetListResponse,
    DatasetResponse,
    DatasetVersionListResponse,
    DatasetVersionResponse,
    UploadVersionResponse,
)
from backend.app.schemas.dataset_column import DatasetColumnResponse
from backend.app.schemas.profile import DatasetProfileResponse
from backend.app.services.ingestion_service import IngestionError, ingest_dataset_version
from backend.app.services.metadata_service import (
    MetadataDatabaseError,
    create_logical_dataset,
    get_dataset_by_id,
    get_dataset_version,
    get_profile,
    list_columns_for_version,
    list_dataset_versions,
    list_datasets,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])
legacy_router = APIRouter(prefix="/datasets", tags=["legacy"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    request: DatasetCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetResponse:
    try:
        dataset = create_logical_dataset(db, name=request.name, description=request.description)
    except MetadataDatabaseError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=DatasetListResponse)
def get_datasets(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DatasetListResponse:
    datasets, total = list_datasets(db, limit=limit, offset=offset)
    return DatasetListResponse(items=datasets, total=total, limit=limit, offset=offset)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetResponse:
    dataset = get_dataset_by_id(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return DatasetResponse.model_validate(dataset)


@router.post("/{dataset_id}/versions", response_model=UploadVersionResponse)
async def upload_dataset_version(
    dataset_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UploadVersionResponse:
    try:
        result = await ingest_dataset_version(
            db, dataset_id=dataset_id, upload=file, settings=settings
        )
    except IngestionError as exc:
        message = str(exc)
        code = 404 if message == "Dataset not found." else 413 if "size limit" in message else 400
        raise HTTPException(status_code=code, detail=message) from exc
    version = result.version
    return UploadVersionResponse(
        dataset_id=dataset_id,
        dataset_version_id=version.id,
        version_number=version.version_number,
        status=version.processing_status,
        duplicate=result.duplicate,
        profile_available=version.profile is not None,
    )


@router.get("/{dataset_id}/versions", response_model=DatasetVersionListResponse)
def get_versions(
    dataset_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DatasetVersionListResponse:
    if get_dataset_by_id(db, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    versions, total = list_dataset_versions(db, dataset_id, limit=limit, offset=offset)
    return DatasetVersionListResponse(items=versions, total=total, limit=limit, offset=offset)


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
def get_version(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetVersionResponse:
    version = get_dataset_version(db, dataset_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found.")
    return DatasetVersionResponse.model_validate(version)


@router.get("/{dataset_id}/versions/{version_id}/profile", response_model=DatasetProfileResponse)
def get_version_profile(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetProfileResponse:
    result = get_profile(db, dataset_id, version_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")
    profile, columns = result
    response = DatasetProfileResponse.model_validate(profile)
    return response.model_copy(
        update={
            "dataset_id": dataset_id,
            "column_summary": profile.profile_summary,
            "columns": [DatasetColumnResponse.model_validate(column) for column in columns],
        }
    )


@router.get(
    "/{dataset_id}/versions/{version_id}/columns",
    response_model=list[DatasetColumnResponse],
)
def get_version_columns(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[DatasetColumnResponse]:
    columns = list_columns_for_version(db, dataset_id, version_id)
    if columns is None:
        raise HTTPException(status_code=404, detail="Dataset version not found.")
    return [DatasetColumnResponse.model_validate(column) for column in columns]


@router.get(
    "/{dataset_id}/versions/{version_id}/columns/{column_name}",
    response_model=DatasetColumnResponse,
)
def get_version_column(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    column_name: str,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetColumnResponse:
    columns = list_columns_for_version(db, dataset_id, version_id)
    if columns is None:
        raise HTTPException(status_code=404, detail="Dataset version not found.")
    column = next((item for item in columns if item.column_name == column_name), None)
    if column is None:
        raise HTTPException(status_code=404, detail="Dataset column not found.")
    return DatasetColumnResponse.model_validate(column)


@legacy_router.post("/upload", response_model=UploadVersionResponse)
async def legacy_upload(
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UploadVersionResponse:
    """Compatibility shim for the v0.1 one-step upload endpoint."""
    filename = file.filename or "dataset"
    dataset = create_logical_dataset(db, name=Path(filename).stem or "dataset")
    try:
        result = await ingest_dataset_version(
            db, dataset_id=dataset.id, upload=file, settings=settings
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UploadVersionResponse(
        dataset_id=dataset.id,
        dataset_version_id=result.version.id,
        version_number=result.version.version_number,
        status=result.version.processing_status,
        duplicate=result.duplicate,
        profile_available=True,
    )
