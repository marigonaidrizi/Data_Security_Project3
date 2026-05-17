from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from server.services.protocol_service import TransferError

router = APIRouter(prefix="/api/files", tags=["files"])


def error_response(exc: TransferError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


@router.post("/upload", response_model=None)
async def upload_file(request: Request, payload: dict[str, Any] = Body(...)):
    try:
        return request.app.state.transfer_service.process_upload(payload)
    except TransferError as exc:
        return error_response(exc)


@router.get("")
async def list_files(request: Request) -> dict:
    return {"success": True, "files": request.app.state.transfer_service.list_files()}


@router.get("/{file_id}/metadata", response_model=None)
async def file_metadata(request: Request, file_id: str):
    try:
        return {"success": True, "file": request.app.state.transfer_service.get_file_metadata(file_id)}
    except TransferError as exc:
        return error_response(exc)


@router.post("/download/{file_id}", response_model=None)
async def download_file(
    request: Request,
    file_id: str,
    payload: dict[str, Any] = Body(...),
):
    try:
        return request.app.state.transfer_service.process_download(file_id, payload)
    except TransferError as exc:
        return error_response(exc)
