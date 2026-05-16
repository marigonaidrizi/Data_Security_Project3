from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from server import __version__, config
from server.api import routes_crypto, routes_dashboard, routes_files
from server.crypto.rsa_utils import generate_private_key
from server.services.file_service import FileStorage
from server.services.protocol_service import MetadataStore
from server.services.transfer_service import SecureTransferService


def create_app() -> FastAPI:
    app = FastAPI(title=config.APP_NAME, version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage = FileStorage()
    storage.ensure_directories()
    metadata = MetadataStore()
    metadata.ensure_exists()
    server_private_key = generate_private_key(config.RSA_KEY_SIZE)
    app.state.transfer_service = SecureTransferService(server_private_key, storage, metadata)

    app.mount("/static", StaticFiles(directory=str(config.SERVER_STATIC_DIR)), name="static")
    app.mount("/client", StaticFiles(directory=str(config.CLIENT_WEB_DIR), html=True), name="client")

    app.include_router(routes_crypto.router)
    app.include_router(routes_files.router)
    app.include_router(routes_dashboard.router)

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    @app.get("/api/health")
    async def health() -> dict:
        return app.state.transfer_service.health()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "MALFORMED_REQUEST",
                "message": "The request body or parameters are invalid.",
                "details": exc.errors(),
            },
        )

    return app


app = create_app()
