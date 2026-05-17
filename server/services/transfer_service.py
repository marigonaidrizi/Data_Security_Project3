from __future__ import annotations

from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa

from server import config
from server.crypto import aes_utils, hash_utils, rsa_utils, signature_utils
from server.services.file_service import FileStorage
from server.services.protocol_service import (
    MetadataStore,
    TransferError,
    b64decode,
    b64encode,
    require_fields,
    utc_now,
)


class SecureTransferService:
    def __init__(
        self,
        server_private_key: rsa.RSAPrivateKey,
        storage: FileStorage,
        metadata: MetadataStore,
    ) -> None:
        self.server_private_key = server_private_key
        self.server_public_key = rsa_utils.public_key_from_private(server_private_key)
        self.storage = storage
        self.metadata = metadata

    @property
    def server_public_key_pem(self) -> str:
        return rsa_utils.serialize_public_key(self.server_public_key)

    @property
    def server_public_key_fingerprint(self) -> str:
        return rsa_utils.public_key_fingerprint(self.server_public_key)

    def health(self) -> dict[str, Any]:
        return {
            "success": True,
            "status": "running",
            "app": config.APP_NAME,
            "version": config.APP_VERSION,
            "server_public_key_fingerprint": self.server_public_key_fingerprint,
            "files_stored": len(self.metadata.list_files()),
        }

    def server_public_key_response(self) -> dict[str, Any]:
        return {
            "success": True,
            "public_key": self.server_public_key_pem,
            "fingerprint": self.server_public_key_fingerprint,
            "algorithm": "RSA-OAEP/RSA-PSS",
            "key_size": self.server_public_key.key_size,
        }

    def list_files(self) -> list[dict[str, Any]]:
        return [self._public_record(record) for record in self.metadata.list_files()]

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        record = self.metadata.get_file(file_id)
        if record is None:
            raise TransferError("FILE_NOT_FOUND", "The requested file was not found.", 404)
        return self._public_record(record)

    def recent_transfers(self) -> list[dict[str, Any]]:
        return self.metadata.list_transfers()

    def process_upload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TransferError("MALFORMED_REQUEST", "Upload request body must be a JSON object.")

        require_fields(
            payload,
            [
                "filename",
                "client_public_key",
                "encrypted_aes_key",
                "aes_nonce",
                "encrypted_file",
                "file_hash",
                "signature",
                "original_size",
            ],
        )

        try:
            filename = self.storage.sanitize_filename(payload["filename"])
        except ValueError as exc:
            raise TransferError("INVALID_FILENAME", "The provided filename is not valid.") from exc

        try:
            original_size = int(payload["original_size"])
        except (TypeError, ValueError) as exc:
            raise TransferError("MALFORMED_REQUEST", "original_size must be an integer.") from exc

        if original_size < 0 or original_size > config.MAX_FILE_SIZE:
            raise TransferError("FILE_TOO_LARGE", "The uploaded file is too large.", 413)

        file_hash = str(payload["file_hash"]).lower()
        if not hash_utils.is_sha256_hex(file_hash):
            raise TransferError("MALFORMED_REQUEST", "file_hash must be a SHA-256 hex digest.")

        encrypted_aes_key = b64decode(payload["encrypted_aes_key"], "encrypted_aes_key")
        nonce = b64decode(payload["aes_nonce"], "aes_nonce")
        encrypted_file = b64decode(payload["encrypted_file"], "encrypted_file")
        signature = b64decode(payload["signature"], "signature")

        try:
            client_public_key = rsa_utils.load_public_key(payload["client_public_key"])
        except ValueError as exc:
            raise TransferError("INVALID_PUBLIC_KEY", "The client public key is invalid.") from exc

        try:
            aes_key = rsa_utils.decrypt_with_private_key(self.server_private_key, encrypted_aes_key)
        except ValueError as exc:
            raise TransferError("INVALID_ENCRYPTED_AES_KEY", "The AES key could not be decrypted.") from exc

        if len(aes_key) != config.AES_KEY_BYTES:
            raise TransferError("INVALID_ENCRYPTED_AES_KEY", "The AES key must be 256 bits.")

        try:
            plaintext = aes_utils.decrypt_bytes(encrypted_file, aes_key, nonce)
        except ValueError as exc:
            raise TransferError("AES_DECRYPTION_FAILED", "The uploaded file could not be decrypted.") from exc

        if len(plaintext) != original_size:
            raise TransferError("MALFORMED_REQUEST", "The decrypted file size does not match original_size.")

        if not hash_utils.verify_sha256_hex(plaintext, file_hash):
            self.metadata.record_transfer(
                {"type": "upload", "status": "failed", "filename": filename, "message": "Hash mismatch"}
            )
            raise TransferError("HASH_MISMATCH", "The uploaded file hash does not match.")

        signature_ok = signature_utils.verify_signature(client_public_key, signature, bytes.fromhex(file_hash))
        if not signature_ok:
            self.metadata.record_transfer(
                {
                    "type": "upload",
                    "status": "failed",
                    "filename": filename,
                    "message": "Signature verification failed",
                }
            )
            raise TransferError(
                "SIGNATURE_VERIFICATION_FAILED",
                "The uploaded file signature could not be verified.",
            )

        file_id = self.storage.generate_file_id()
        stored_filename = self.storage.stored_filename(file_id, filename)

        try:
            self.storage.write_uploaded_file(stored_filename, plaintext)
        except OSError as exc:
            raise TransferError("STORAGE_WRITE_FAILED", "The server could not store the uploaded file.", 500) from exc

        record = {
            "file_id": file_id,
            "filename": filename,
            "stored_filename": stored_filename,
            "stored_path": self.storage.relative_upload_path(stored_filename),
            "original_size": original_size,
            "sha256": file_hash,
            "uploaded_at": utc_now(),
            "client_public_key_fingerprint": rsa_utils.public_key_fingerprint(client_public_key),
            "hash_verified": True,
            "signature_verified": True,
            "aes_decrypt_successful": True,
            "download_count": 0,
        }
        self.metadata.add_file(record)
        self.metadata.record_transfer(
            {"type": "upload", "status": "success", "filename": filename, "file_id": file_id}
        )

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "hash_verified": True,
            "signature_verified": True,
            "aes_decrypt_successful": True,
        }

    def process_download(self, file_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise TransferError("MALFORMED_REQUEST", "Download request body must be a JSON object.")
        require_fields(payload, ["client_public_key"])

        record = self.metadata.get_file(file_id)
        if record is None:
            raise TransferError("FILE_NOT_FOUND", "The requested file was not found.", 404)

        try:
            client_public_key = rsa_utils.load_public_key(payload["client_public_key"])
        except ValueError as exc:
            raise TransferError("INVALID_PUBLIC_KEY", "The client public key is invalid.") from exc

        try:
            plaintext = self.storage.read_uploaded_file(record["stored_filename"])
        except (KeyError, FileNotFoundError) as exc:
            raise TransferError("FILE_NOT_FOUND", "The requested file was not found.", 404) from exc

        aes_key = aes_utils.generate_aes_key()
        encrypted = aes_utils.encrypt_bytes(plaintext, aes_key)
        file_hash = hash_utils.sha256_hex(plaintext)
        signature = signature_utils.sign_hash(self.server_private_key, bytes.fromhex(file_hash))

        try:
            encrypted_aes_key = rsa_utils.encrypt_with_public_key(client_public_key, aes_key)
        except ValueError as exc:
            raise TransferError("INVALID_PUBLIC_KEY", "The client public key cannot be used for encryption.") from exc

        self.metadata.increment_download_count(file_id)
        self.metadata.record_transfer(
            {"type": "download", "status": "success", "filename": record["filename"], "file_id": file_id}
        )

        return {
            "success": True,
            "file_id": file_id,
            "filename": record["filename"],
            "server_public_key": self.server_public_key_pem,
            "encrypted_aes_key": b64encode(encrypted_aes_key),
            "aes_nonce": b64encode(encrypted.nonce),
            "encrypted_file": b64encode(encrypted.ciphertext),
            "file_hash": file_hash,
            "signature": b64encode(signature),
            "original_size": len(plaintext),
            "timestamp": utc_now(),
        }

    def _public_record(self, record: dict[str, Any]) -> dict[str, Any]:
        fields = [
            "file_id",
            "filename",
            "original_size",
            "sha256",
            "uploaded_at",
            "client_public_key_fingerprint",
            "hash_verified",
            "signature_verified",
            "aes_decrypt_successful",
            "download_count",
        ]
        return {field: record.get(field) for field in fields}
