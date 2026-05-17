from pathlib import Path

APP_NAME = "Secure File Transfer"
APP_VERSION = "1.0.0"

SERVER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_DIR.parent

STORAGE_DIR = SERVER_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"
METADATA_PATH = STORAGE_DIR / "metadata.json"

TEMPLATES_DIR = SERVER_DIR / "templates"
SERVER_STATIC_DIR = SERVER_DIR / "static"
CLIENT_WEB_DIR = PROJECT_ROOT / "client-web"

RSA_KEY_SIZE = 3072
AES_KEY_BYTES = 32
AES_GCM_NONCE_BYTES = 12
MAX_FILE_SIZE = 25 * 1024 * 1024

ALLOWED_CORS_ORIGINS = ["*"]
