import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pandas.errors import EmptyDataError, ParserError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db
from backend.app.schemas.dataset import DatasetListResponse, DatasetResponse
from backend.app.services.file_service import (
    calculate_sha256,
    save_upload_file,
    validate_file_extension,
    validate_file_size,
)
from backend.app.services.metadata_service import (
    DuplicateDatasetError,
    MetadataDatabaseError,
    create_dataset_record,
    get_dataset_by_id,
    list_datasets,
)


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/upload",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    file: UploadFile,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DatasetResponse:
    original_filename = file.filename or ""
    validate_file_extension(original_filename)
    file_size_bytes = await validate_file_size(file, settings.max_upload_bytes)

    stored_filename, file_path = await save_upload_file(file, settings.upload_dir)
    file_hash = calculate_sha256(file_path)

    try:
        dataframe = pd.read_csv(file_path)
    except EmptyDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV read failure. Uploaded CSV is empty or has no columns.",
        ) from exc
    except (ParserError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV read failure. Unable to parse the uploaded file.",
        ) from exc

    row_count, column_count = dataframe.shape

    try:
        dataset = create_dataset_record(
            db,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size_bytes,
            row_count=row_count,
            column_count=column_count,
        )
    except DuplicateDatasetError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset with the same file hash already exists.",
        ) from exc
    except MetadataDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failure while storing dataset metadata.",
        ) from exc

    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=DatasetListResponse)
def get_datasets(db: Session = Depends(get_db)) -> DatasetListResponse:
    try:
        datasets = list_datasets(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failure while listing datasets.",
        ) from exc
    return DatasetListResponse(datasets=datasets, count=len(datasets))


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: uuid.UUID, db: Session = Depends(get_db)) -> DatasetResponse:
    try:
        dataset = get_dataset_by_id(db, dataset_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failure while retrieving dataset.",
        ) from exc

    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found.",
        )
    return DatasetResponse.model_validate(dataset)
