from __future__ import annotations

import base64
import binascii
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server import config


class TransferError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_response(self) -> dict[str, Any]:
        return {"success": False, "error": self.code, "message": self.message}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64decode(value: Any, field_name: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise TransferError("MISSING_FIELD", f"Missing or invalid field: {field_name}")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise TransferError("INVALID_BASE64", f"Invalid Base64 data in field: {field_name}") from exc


def require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    for field in fields:
        if field not in payload or payload[field] in (None, ""):
            raise TransferError("MISSING_FIELD", f"Missing required field: {field}")


class MetadataStore:
    def __init__(self, metadata_path: Path = config.METADATA_PATH) -> None:
        self.metadata_path = metadata_path
        self._lock = threading.Lock()

    def ensure_exists(self) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.metadata_path.exists():
            self._write({"files": [], "transfers": []})

    def _empty(self) -> dict[str, Any]:
        return {"files": [], "transfers": []}

    def _normalize(self, data: Any) -> dict[str, Any]:
        if isinstance(data, list):
            return {"files": data, "transfers": []}
        if not isinstance(data, dict):
            return self._empty()
        files = data.get("files", [])
        transfers = data.get("transfers", [])
        return {
            "files": files if isinstance(files, list) else [],
            "transfers": transfers if isinstance(transfers, list) else [],
        }

    def _read(self) -> dict[str, Any]:
        self.ensure_exists()
        try:
            return self._normalize(json.loads(self.metadata_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return self._empty()

    def _write(self, data: dict[str, Any]) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.metadata_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self.metadata_path)

    def list_files(self) -> list[dict[str, Any]]:
        with self._lock:
            data = self._read()
            return sorted(data["files"], key=lambda item: item.get("uploaded_at", ""), reverse=True)

    def list_transfers(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            data = self._read()
            return list(reversed(data["transfers"][-limit:]))

    def get_file(self, file_id: str) -> dict[str, Any] | None:
        with self._lock:
            data = self._read()
            for record in data["files"]:
                if record.get("file_id") == file_id:
                    return dict(record)
        return None

    def add_file(self, record: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            data["files"].append(record)
            self._write(data)

    def update_file(self, file_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            data = self._read()
            updated = None
            for record in data["files"]:
                if record.get("file_id") == file_id:
                    record.update(values)
                    updated = dict(record)
                    break
            if updated is not None:
                self._write(data)
            return updated

    def increment_download_count(self, file_id: str) -> None:
        record = self.get_file(file_id)
        if record is None:
            return
        self.update_file(file_id, {"download_count": int(record.get("download_count", 0)) + 1})

    def record_transfer(self, event: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            safe_event = {
                "timestamp": utc_now(),
                "type": event.get("type", "transfer"),
                "status": event.get("status", "unknown"),
                "filename": event.get("filename"),
                "file_id": event.get("file_id"),
                "message": event.get("message", ""),
            }
            data["transfers"].append(safe_event)
            data["transfers"] = data["transfers"][-100:]
            self._write(data)
