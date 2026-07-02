import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


ALLOWED_EXTENSIONS = {".csv"}


def validate_file_extension(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .csv files are supported.",
        )


async def validate_file_size(file: UploadFile, max_upload_bytes: int) -> int:
    await file.seek(0)
    content = await file.read()
    file_size = len(content)
    await file.seek(0)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the configured size limit.",
        )

    return file_size


def _build_stored_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4()}{suffix}"


async def save_upload_file(file: UploadFile, upload_dir: str) -> tuple[str, str]:
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    stored_filename = _build_stored_filename(file.filename or "dataset.csv")
    destination = upload_path / stored_filename

    await file.seek(0)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    await file.seek(0)

    return stored_filename, str(destination)


def calculate_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with Path(file_path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
