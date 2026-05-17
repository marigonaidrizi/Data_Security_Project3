# Data_Security_Project3

# Secure File Transfer Protocol using Hybrid Cryptography

A Python/FastAPI secure file transfer system for a university assignment. It implements a hybrid cryptography protocol over HTTP with a browser client and server dashboard.

## Features

- FastAPI server with JSON HTTP API.
- Browser client built with HTML, CSS, and JavaScript.
- Server dashboard for status, uploaded files, verification state, and download counts.
- RSA key generation on server startup and in the browser client.
- RSA-OAEP with SHA-256 for AES key encryption.
- RSA-PSS with SHA-256 for signing and verifying file hashes.
- AES-256-GCM for file encryption and decryption.
- SHA-256 for file integrity checks.
- Local file storage under `server/storage/uploads/`.
- JSON metadata storage in `server/storage/metadata.json`.
- Pytest coverage for crypto helpers and core transfer behavior.

## Setup

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the Server

```bash
uvicorn server.app:app --reload
```

Open:

- Dashboard: `http://127.0.0.1:8000/dashboard`
- Client frontend: `http://127.0.0.1:8000/client/index.html`
- API docs: `http://127.0.0.1:8000/docs`

The client should be opened through the FastAPI server so the browser Web Crypto API is available in a secure local context.

## API Endpoints

- `GET /api/health`
- `GET /api/crypto/server-public-key`
- `POST /api/files/upload`
- `GET /api/files`
- `POST /api/files/download/{file_id}`
- `GET /api/files/{file_id}/metadata`
- `GET /dashboard`
- `GET /dashboard/files`
- `GET /dashboard/files/{file_id}`

## Upload Protocol

1. Browser client generates RSA keys.
2. Client fetches the server public key.
3. User selects a file.
4. Client generates a fresh AES-256 key and AES-GCM nonce.
5. Client encrypts the file with AES-GCM.
6. Client hashes the original plaintext file with SHA-256.
7. Client signs the hash with RSA-PSS.
8. Client encrypts the AES key with the server RSA public key using RSA-OAEP.
9. Client sends the JSON upload package to the server.
10. Server decrypts the AES key with its RSA private key.
11. Server decrypts the file with AES-GCM.
12. Server hashes the decrypted file and compares the hash.
13. Server verifies the client signature.
14. Server stores the file and metadata only after verification succeeds.

## Download Protocol

1. Client requests the file list.
2. User selects a file.
3. Client sends its RSA-OAEP public key to the server.
4. Server loads the stored file.
5. Server generates a fresh AES-256 key and AES-GCM nonce.
6. Server encrypts the file with AES-GCM.
7. Server hashes the plaintext file with SHA-256.
8. Server signs the hash with RSA-PSS.
9. Server encrypts the AES key with the client public key.
10. Client decrypts the AES key with its private key.
11. Client decrypts the file.
12. Client verifies the SHA-256 hash and server signature.
13. Client saves the decrypted file only after verification succeeds.

## Crypto Notes

The server uses one runtime RSA key pair for RSA-OAEP and RSA-PSS operations. Browser Web Crypto binds RSA keys to a specific algorithm, so the client generates one RSA-OAEP key pair for download key exchange and one RSA-PSS key pair for upload signatures. This preserves the assignment's protocol roles while staying compatible with browser crypto APIs.

AES-GCM ciphertext includes the authentication tag in the encrypted byte string, which is the standard representation used by Python `cryptography` and browser Web Crypto.

## Testing

```bash
pytest
```

The tests cover:

- RSA key generation and public key serialization.
- RSA-OAEP encryption and decryption.
- RSA-PSS signing and verification.
- AES-GCM encryption, decryption, and tamper failure.
- SHA-256 hashing.
- Successful upload processing.
- Hash mismatch rejection.
- Signature failure rejection.
- Download package creation and verification.
- Missing file handling.

## Known Limitations

- Server RSA keys are generated at startup and are not persisted.
- Browser client keys are kept in memory and are lost on refresh.
- Uploaded files are stored decrypted after server-side verification to keep the assignment implementation simple.
- Metadata uses a local JSON file instead of a database.
- Large files are processed in memory; streaming encryption is a future improvement.
- This demonstrates application-layer cryptography, but real deployments should still use HTTPS.
