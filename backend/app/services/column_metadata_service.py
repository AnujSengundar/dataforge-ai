import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.models.dataset_column import DatasetColumn
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.profile import DatasetProfile
from backend.app.services.profiling_service import TabularDataError, profile_dataframe, read_tabular


class ColumnMetadataError(Exception):
    """Expected column metadata failure safe to expose at the API boundary."""


def create_column_metadata(
    db: Session,
    *,
    dataset_version_id: uuid.UUID,
    csv_file_path: str,
    settings: Settings,
) -> list[DatasetColumn]:
    try:
        version = db.get(DatasetVersion, dataset_version_id)
        if version is None:
            raise ColumnMetadataError("Dataset version not found.")

        dataframe = read_tabular(Path(csv_file_path), "csv")
        profile_result = profile_dataframe(
            dataframe,
            dataset_version_id=dataset_version_id,
            file_size_bytes=version.file_size_bytes,
            settings=settings,
        )

        db.execute(
            delete(DatasetColumn).where(DatasetColumn.dataset_version_id == dataset_version_id)
        )
        db.execute(
            delete(DatasetProfile).where(DatasetProfile.dataset_version_id == dataset_version_id)
        )
        db.add(profile_result.profile)
        db.add_all(profile_result.columns)
        db.commit()

        for column in profile_result.columns:
            db.refresh(column)
        return profile_result.columns
    except ColumnMetadataError:
        db.rollback()
        raise
    except (TabularDataError, SQLAlchemyError) as exc:
        db.rollback()
        raise ColumnMetadataError("Failed to extract and store column metadata.") from exc


def list_columns_for_dataset_version(
    db: Session,
    dataset_version_id: uuid.UUID,
) -> list[DatasetColumn]:
    statement = (
        select(DatasetColumn)
        .where(DatasetColumn.dataset_version_id == dataset_version_id)
        .order_by(DatasetColumn.column_position)
    )
    return list(db.scalars(statement).all())
