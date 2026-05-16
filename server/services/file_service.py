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