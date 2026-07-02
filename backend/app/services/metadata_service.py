import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.dataset import Dataset


class DuplicateDatasetError(Exception):
    pass


class MetadataDatabaseError(Exception):
    pass


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
    dataset = Dataset(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_hash=file_hash,
        file_size_bytes=file_size_bytes,
        row_count=row_count,
        column_count=column_count,
        status="uploaded",
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


def list_datasets(db: Session) -> list[Dataset]:
    statement = select(Dataset).order_by(Dataset.created_at.desc())
    return list(db.scalars(statement).all())


def get_dataset_by_id(db: Session, dataset_id: uuid.UUID) -> Dataset | None:
    return db.get(Dataset, dataset_id)
