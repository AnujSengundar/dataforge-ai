import asyncio
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select

from backend.app.api.datasets import get_version_columns, upload_dataset_version
from backend.app.models.dataset_column import DatasetColumn
from backend.app.models.dataset_version import DatasetVersion
from backend.app.services.column_metadata_service import ColumnMetadataError, create_column_metadata
from backend.app.services.metadata_service import create_logical_dataset


def _upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


def _run(coro):
    return asyncio.run(coro)


def test_successful_csv_upload_and_metadata_creation(db_session, test_settings):
    dataset = create_logical_dataset(db_session, name=f"integration-{uuid.uuid4()}")

    response = _run(
        upload_dataset_version(
            dataset.id,
            _upload("sales.csv", b"name,amount\nalpha,10\nbeta,20\n"),
            db_session,
            test_settings,
        )
    )

    columns = get_version_columns(dataset.id, response.dataset_version_id, db_session)
    assert response.status == "completed"
    assert [column.column_name for column in columns] == ["name", "amount"]
    assert columns[1].logical_type == "integer"


def test_columns_returned_in_ordinal_order(db_session, test_settings):
    dataset = create_logical_dataset(db_session, name=f"ordering-{uuid.uuid4()}")

    response = _run(
        upload_dataset_version(
            dataset.id,
            _upload("ordered.csv", b"b,a,c\n2,1,3\n"),
            db_session,
            test_settings,
        )
    )

    columns = get_version_columns(dataset.id, response.dataset_version_id, db_session)
    assert [column.column_name for column in columns] == ["b", "a", "c"]


def test_nonexistent_dataset_columns_returns_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_version_columns(uuid.uuid4(), uuid.uuid4(), db_session)

    assert exc_info.value.status_code == 404


def test_extraction_failure_marks_metadata_failed(db_session, test_settings, monkeypatch):
    dataset = create_logical_dataset(db_session, name=f"failure-{uuid.uuid4()}")

    def fail_profile(*args, **kwargs):
        raise RuntimeError("unsafe internal detail")

    monkeypatch.setattr("backend.app.services.ingestion_service.profile_dataframe", fail_profile)

    with pytest.raises(HTTPException) as exc_info:
        _run(
            upload_dataset_version(
                dataset.id,
                _upload("bad_metadata.csv", b"name\nalpha\n"),
                db_session,
                test_settings,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Column metadata extraction failed."
    version = db_session.scalar(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset.id)
    )
    assert version is not None
    assert version.processing_status == "metadata_failed"
    assert version.error_message == "Column metadata extraction failed."
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DatasetColumn)
            .where(DatasetColumn.dataset_version_id == version.id)
        )
        == 0
    )


def test_upload_column_commit_failure_marks_metadata_failed(db_session, test_settings, monkeypatch):
    dataset = create_logical_dataset(db_session, name=f"commit-failure-{uuid.uuid4()}")

    def duplicate_column_profile(dataframe, *, dataset_version_id, file_size_bytes, settings):
        duplicate_a = DatasetColumn(
            dataset_version_id=dataset_version_id,
            column_name="a",
            column_position=0,
            logical_type="integer",
            physical_type="Int64",
            nullable=False,
            null_count=0,
            non_null_count=1,
            null_percentage=0,
            distinct_count=1,
            unique_percentage=100,
            sample_values=["1"],
            is_constant=True,
            is_fully_null=False,
            is_high_null=False,
            is_candidate_identifier=False,
            is_possible_categorical=False,
            is_possible_datetime_text=False,
            is_possible_numeric_text=False,
            top_values=[],
        )
        duplicate_b = DatasetColumn(
            dataset_version_id=dataset_version_id,
            column_name="b",
            column_position=0,
            logical_type="integer",
            physical_type="Int64",
            nullable=False,
            null_count=0,
            non_null_count=1,
            null_percentage=0,
            distinct_count=1,
            unique_percentage=100,
            sample_values=["2"],
            is_constant=True,
            is_fully_null=False,
            is_high_null=False,
            is_candidate_identifier=False,
            is_possible_categorical=False,
            is_possible_datetime_text=False,
            is_possible_numeric_text=False,
            top_values=[],
        )
        return type(
            "ProfileResultStub",
            (),
            {
                "profile": None,
                "columns": [duplicate_a, duplicate_b],
                "schema_signature": "duplicate-columns",
            },
        )()

    monkeypatch.setattr(
        "backend.app.services.ingestion_service.profile_dataframe",
        duplicate_column_profile,
    )

    with pytest.raises(HTTPException) as exc_info:
        _run(
            upload_dataset_version(
                dataset.id,
                _upload("duplicate_positions.csv", b"a,b\n1,2\n"),
                db_session,
                test_settings,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Column metadata extraction failed."
    version = db_session.scalar(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset.id)
    )
    assert version is not None
    assert version.processing_status == "metadata_failed"
    assert version.error_message == "Column metadata extraction failed."
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DatasetColumn)
            .where(DatasetColumn.dataset_version_id == version.id)
        )
        == 0
    )


def test_partial_inserts_are_rolled_back(db_session, test_settings, tmp_path: Path, monkeypatch):
    dataset = create_logical_dataset(db_session, name=f"rollback-{uuid.uuid4()}")
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=1,
        original_filename="rollback.csv",
        storage_path="rollback.csv",
        file_format="csv",
        file_size_bytes=10,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        processing_status="completed",
    )
    existing = DatasetColumn(
        dataset_version=version,
        column_name="existing",
        column_position=0,
        logical_type="string",
        physical_type="String",
        nullable=False,
        null_count=0,
        non_null_count=1,
        null_percentage=0,
        distinct_count=1,
        unique_percentage=100,
        sample_values=["x"],
        is_constant=True,
        is_fully_null=False,
        is_high_null=False,
        is_candidate_identifier=False,
        is_possible_categorical=False,
        is_possible_datetime_text=False,
        is_possible_numeric_text=False,
        top_values=[],
    )
    db_session.add(version)
    db_session.add(existing)
    db_session.commit()

    csv_path = tmp_path / "duplicate_columns.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    def duplicate_column_profile(*args, **kwargs):
        duplicate_a = DatasetColumn(
            dataset_version_id=version.id,
            column_name="a",
            column_position=0,
            logical_type="integer",
            physical_type="Int64",
            nullable=False,
            null_count=0,
            non_null_count=1,
            null_percentage=0,
            distinct_count=1,
            unique_percentage=100,
            sample_values=["1"],
            is_constant=True,
            is_fully_null=False,
            is_high_null=False,
            is_candidate_identifier=False,
            is_possible_categorical=False,
            is_possible_datetime_text=False,
            is_possible_numeric_text=False,
            top_values=[],
        )
        duplicate_b = DatasetColumn(
            dataset_version_id=version.id,
            column_name="b",
            column_position=0,
            logical_type="integer",
            physical_type="Int64",
            nullable=False,
            null_count=0,
            non_null_count=1,
            null_percentage=0,
            distinct_count=1,
            unique_percentage=100,
            sample_values=["2"],
            is_constant=True,
            is_fully_null=False,
            is_high_null=False,
            is_candidate_identifier=False,
            is_possible_categorical=False,
            is_possible_datetime_text=False,
            is_possible_numeric_text=False,
            top_values=[],
        )
        return type("ProfileResultStub", (), {"columns": [duplicate_a, duplicate_b]})()

    monkeypatch.setattr(
        "backend.app.services.column_metadata_service.profile_dataframe",
        duplicate_column_profile,
    )

    with pytest.raises(ColumnMetadataError):
        create_column_metadata(
            db_session,
            dataset_version_id=version.id,
            csv_file_path=str(csv_path),
            settings=test_settings,
        )

    columns = db_session.scalars(
        select(DatasetColumn).where(DatasetColumn.dataset_version_id == version.id)
    ).all()
    assert [column.column_name for column in columns] == ["existing"]


def test_duplicate_upload_behavior(db_session, test_settings):
    dataset = create_logical_dataset(db_session, name=f"duplicate-{uuid.uuid4()}")
    payload = b"name\nalpha\n"

    first = _run(
        upload_dataset_version(
            dataset.id,
            _upload("first.csv", payload),
            db_session,
            test_settings,
        )
    )
    second = _run(
        upload_dataset_version(
            dataset.id,
            _upload("second.csv", payload),
            db_session,
            test_settings,
        )
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert first.dataset_version_id == second.dataset_version_id


def test_repeated_metadata_extraction_does_not_create_duplicate_rows(
    db_session, test_settings, tmp_path: Path
):
    dataset = create_logical_dataset(db_session, name=f"idempotent-{uuid.uuid4()}")
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=1,
        original_filename="idempotent.csv",
        storage_path="idempotent.csv",
        file_format="csv",
        file_size_bytes=10,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        processing_status="completed",
    )
    db_session.add(version)
    db_session.commit()
    csv_path = tmp_path / "idempotent.csv"
    csv_path.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")

    create_column_metadata(
        db_session,
        dataset_version_id=version.id,
        csv_file_path=str(csv_path),
        settings=test_settings,
    )
    create_column_metadata(
        db_session,
        dataset_version_id=version.id,
        csv_file_path=str(csv_path),
        settings=test_settings,
    )

    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DatasetColumn)
            .where(DatasetColumn.dataset_version_id == version.id)
        )
        == 2
    )
