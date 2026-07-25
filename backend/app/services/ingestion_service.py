import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_version import DatasetVersion
from backend.app.services.profiling_service import TabularDataError, profile_dataframe, read_tabular
from backend.app.services.storage_service import LocalStorage, StorageError

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Expected ingestion failure safe to expose at the API boundary."""


@dataclass(frozen=True)
class IngestionResult:
    version: DatasetVersion
    duplicate: bool


async def ingest_dataset_version(
    db: Session,
    *,
    dataset_id: uuid.UUID,
    upload: UploadFile,
    settings: Settings,
) -> IngestionResult:
    started = time.perf_counter()
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in {".csv", ".parquet"}:
        raise IngestionError("Only .csv and .parquet files are supported.")
    file_format = suffix.removeprefix(".")
    storage = LocalStorage(settings.upload_dir)
    try:
        staged = await storage.stage_upload(upload, settings.max_upload_bytes)
    except StorageError as exc:
        raise IngestionError(str(exc)) from exc

    try:
        dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id).with_for_update())
        if dataset is None:
            raise IngestionError("Dataset not found.")
        existing = db.scalar(
            select(DatasetVersion).where(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.sha256_hash == staged.sha256_hash,
            )
        )
        if existing is not None:
            storage.discard(staged)
            return IngestionResult(existing, True)

        # Validate parseability before a durable version row or object is created.
        dataframe = read_tabular(staged.path, file_format)
        next_number = (
            int(
                db.scalar(
                    select(func.coalesce(func.max(DatasetVersion.version_number), 0)).where(
                        DatasetVersion.dataset_id == dataset_id
                    )
                )
                or 0
            )
            + 1
        )
        version = DatasetVersion(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_number=next_number,
            original_filename=staged.safe_filename,
            storage_path="pending",
            file_format=file_format,
            file_size_bytes=staged.size_bytes,
            sha256_hash=staged.sha256_hash,
            processing_status="processing",
            ingestion_started_at=datetime.now(UTC),
        )
        version.storage_path = storage.promote_source(staged, dataset_id, version.id)
        db.add(version)
        db.flush()
        try:
            profile = profile_dataframe(
                dataframe,
                dataset_version_id=version.id,
                file_size_bytes=staged.size_bytes,
                settings=settings,
            )
        except Exception as exc:
            version.row_count = dataframe.height
            version.column_count = dataframe.width
            version.processing_status = "metadata_failed"
            version.error_message = "Column metadata extraction failed."
            version.ingestion_completed_at = datetime.now(UTC)
            db.commit()
            raise IngestionError("Column metadata extraction failed.") from exc

        version.row_count = dataframe.height
        version.column_count = dataframe.width
        version.schema_signature = profile.schema_signature
        version.processing_status = "completed"
        version.ingestion_completed_at = datetime.now(UTC)
        version.profile = profile.profile
        version.columns = profile.columns
        try:
            dataset.current_version_id = version.id
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            failed_version = DatasetVersion(
                id=version.id,
                dataset_id=dataset_id,
                version_number=next_number,
                original_filename=version.original_filename,
                storage_path=version.storage_path,
                file_format=file_format,
                file_size_bytes=staged.size_bytes,
                sha256_hash=staged.sha256_hash,
                row_count=dataframe.height,
                column_count=dataframe.width,
                processing_status="metadata_failed",
                ingestion_started_at=version.ingestion_started_at,
                ingestion_completed_at=datetime.now(UTC),
                error_message="Column metadata extraction failed.",
            )
            db.add(failed_version)
            db.commit()
            raise IngestionError("Column metadata extraction failed.") from exc
        db.refresh(version)
        logger.info(
            "dataset_ingestion_completed dataset_id=%s dataset_version_id=%s "
            "format=%s rows=%s duration_ms=%.3f",
            dataset_id,
            version.id,
            file_format,
            version.row_count,
            (time.perf_counter() - started) * 1000,
        )
        return IngestionResult(version, False)
    except IngestionError:
        storage.discard(staged)
        db.rollback()
        raise
    except (TabularDataError, StorageError) as exc:
        storage.discard(staged)
        db.rollback()
        raise IngestionError(str(exc)) from exc
    except IntegrityError as exc:
        storage.discard(staged)
        db.rollback()
        existing = db.scalar(
            select(DatasetVersion).where(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.sha256_hash == staged.sha256_hash,
            )
        )
        if existing is not None:
            return IngestionResult(existing, True)
        raise IngestionError("A concurrent upload created this dataset version.") from exc
    except SQLAlchemyError as exc:
        storage.discard(staged)
        db.rollback()
        logger.exception("dataset_ingestion_failed dataset_id=%s", dataset_id)
        raise IngestionError("Database failure during dataset ingestion.") from exc
