import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from backend.app.models.dataset import Dataset
from backend.app.models.dataset_column import DatasetColumn
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.profile import DatasetProfile


class DuplicateDatasetError(Exception):
    pass


class MetadataDatabaseError(Exception):
    pass


def create_logical_dataset(db: Session, *, name: str, description: str | None = None) -> Dataset:
    dataset = Dataset(name=name.strip(), description=description, status="active")
    try:
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
    except SQLAlchemyError as exc:
        db.rollback()
        raise MetadataDatabaseError("Failed to create dataset.") from exc
    return dataset


def create_dataset_record(
    db: Session,
    *,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    file_hash: str,
    file_size_bytes: int,
    row_count: int | None,
    column_count: int | None,
) -> Dataset:
    """Compatibility helper retained for callers from DataForge v0.1."""
    dataset = Dataset(
        name=original_filename,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_hash=file_hash,
        file_size_bytes=file_size_bytes,
        row_count=row_count,
        column_count=column_count,
        status="active",
    )
    try:
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateDatasetError("Dataset with the same file hash already exists.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise MetadataDatabaseError("Failed to store dataset metadata.") from exc
    return dataset


def list_datasets(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[Dataset], int]:
    total = int(db.scalar(select(func.count()).select_from(Dataset)) or 0)
    statement = select(Dataset).order_by(Dataset.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all()), total


def get_dataset_by_id(db: Session, dataset_id: uuid.UUID) -> Dataset | None:
    return db.get(Dataset, dataset_id)


def get_dataset_version(
    db: Session, dataset_id: uuid.UUID, version_id: uuid.UUID
) -> DatasetVersion | None:
    statement = select(DatasetVersion).where(
        DatasetVersion.id == version_id, DatasetVersion.dataset_id == dataset_id
    )
    return db.scalar(statement)


def list_dataset_versions(
    db: Session, dataset_id: uuid.UUID, *, limit: int = 50, offset: int = 0
) -> tuple[list[DatasetVersion], int]:
    base = DatasetVersion.dataset_id == dataset_id
    total = int(db.scalar(select(func.count()).select_from(DatasetVersion).where(base)) or 0)
    statement = (
        select(DatasetVersion)
        .where(base)
        .order_by(DatasetVersion.version_number.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all()), total


def get_profile(
    db: Session, dataset_id: uuid.UUID, version_id: uuid.UUID
) -> tuple[DatasetProfile, list[DatasetColumn]] | None:
    version = db.scalar(
        select(DatasetVersion)
        .options(selectinload(DatasetVersion.profile), selectinload(DatasetVersion.columns))
        .where(DatasetVersion.id == version_id, DatasetVersion.dataset_id == dataset_id)
    )
    if version is None or version.profile is None:
        return None
    return version.profile, version.columns


def list_columns_for_version(
    db: Session, dataset_id: uuid.UUID, version_id: uuid.UUID
) -> list[DatasetColumn] | None:
    version = get_dataset_version(db, dataset_id, version_id)
    if version is None:
        return None
    statement = (
        select(DatasetColumn)
        .where(DatasetColumn.dataset_version_id == version_id)
        .order_by(DatasetColumn.column_position)
    )
    return list(db.scalars(statement).all())


def update_dataset_status(db: Session, dataset: Dataset, status: str) -> Dataset:
    dataset.status = status
    try:
        db.commit()
        db.refresh(dataset)
    except SQLAlchemyError as exc:
        db.rollback()
        raise MetadataDatabaseError("Failed to update dataset status.") from exc
    return dataset
