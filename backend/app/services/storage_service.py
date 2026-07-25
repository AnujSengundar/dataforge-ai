import hashlib
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile


class StorageError(Exception):
    """Raised when a storage operation cannot be completed."""


@dataclass(frozen=True)
class StagedUpload:
    path: Path
    size_bytes: int
    sha256_hash: str
    safe_filename: str


class LocalStorage:
    """Filesystem storage with object-key-like paths and traversal-safe names."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        basename = Path(filename).name
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", basename).strip("._")
        return safe[:255] or "dataset"

    async def stage_upload(self, upload: UploadFile, max_bytes: int) -> StagedUpload:
        incoming = self.root / "_incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        safe_filename = self.sanitize_filename(upload.filename or "dataset")
        destination = incoming / f"{uuid.uuid4()}.upload"
        digest = hashlib.sha256()
        size = 0
        try:
            await upload.seek(0)
            with destination.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise StorageError("Uploaded file exceeds the configured size limit.")
                    digest.update(chunk)
                    output.write(chunk)
            if size == 0:
                raise StorageError("Uploaded file is empty.")
            return StagedUpload(destination, size, digest.hexdigest(), safe_filename)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.seek(0)

    def promote_source(
        self,
        staged: StagedUpload,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> str:
        relative = (
            Path("datasets")
            / str(dataset_id)
            / "versions"
            / str(version_id)
            / "source"
            / staged.safe_filename
        )
        destination = self._resolve(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged.path), destination)
        return relative.as_posix()

    def validation_path(
        self,
        dataset_id: uuid.UUID,
        version_id: uuid.UUID,
        run_id: uuid.UUID,
        filename: str,
    ) -> tuple[str, Path]:
        relative = (
            Path("datasets")
            / str(dataset_id)
            / "versions"
            / str(version_id)
            / "validation"
            / str(run_id)
            / filename
        )
        path = self._resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        return relative.as_posix(), path

    def resolve(self, object_key: str) -> Path:
        return self._resolve(Path(object_key))

    def discard(self, staged: StagedUpload) -> None:
        staged.path.unlink(missing_ok=True)

    def _resolve(self, relative: Path) -> Path:
        resolved = (self.root / relative).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise StorageError("Storage path escaped the configured root.")
        return resolved
