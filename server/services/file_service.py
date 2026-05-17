from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path, PurePath

from server import config


class FileStorage:
    def __init__(
        self,
        uploads_dir: Path = config.UPLOADS_DIR,
        downloads_dir: Path = config.DOWNLOADS_DIR,
    ) -> None:
        self.uploads_dir = uploads_dir
        self.downloads_dir = downloads_dir

    def ensure_directories(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def generate_file_id(self) -> str:
        return str(uuid.uuid4())

    def sanitize_filename(self, filename: str) -> str:
        if not isinstance(filename, str):
            raise ValueError("Filename must be a string.")
        name = PurePath(filename).name
        name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        if not name:
            raise ValueError("Filename is empty after sanitization.")
        return name[:180]
    
      def stored_filename(self, file_id: str, filename: str) -> str:
        return f"{file_id}_{self.sanitize_filename(filename)}"

    def upload_path(self, stored_filename: str) -> Path:
        path = (self.uploads_dir / stored_filename).resolve()
        uploads_root = self.uploads_dir.resolve()
        try:
            path.relative_to(uploads_root)
        except ValueError as exc:
            raise ValueError("Invalid upload path.") from exc
        return path

    def write_uploaded_file(self, stored_filename: str, data: bytes) -> Path:
        self.ensure_directories()
        path = self.upload_path(stored_filename)
        path.write_bytes(data)
        return path

    def read_uploaded_file(self, stored_filename: str) -> bytes:
        path = self.upload_path(stored_filename)
        if not path.is_file():
            raise FileNotFoundError(stored_filename)
        return path.read_bytes()

    def relative_upload_path(self, stored_filename: str) -> str:
        return str(Path("server") / "storage" / "uploads" / stored_filename)