from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from server import config
from server.services.protocol_service import TransferError

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


def size_label(size: int | None) -> str:
    if size is None:
        return "unknown"
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{size} B"


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    service = request.app.state.transfer_service
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "health": service.health(),
            "files": service.list_files(),
            "transfers": service.recent_transfers(),
            "size_label": size_label,
        },
    )


@router.get("/dashboard/files", response_class=HTMLResponse)
async def dashboard_files(request: Request) -> HTMLResponse:
    return await dashboard(request)


@router.get("/dashboard/files/{file_id}", response_class=HTMLResponse)
async def dashboard_file_detail(request: Request, file_id: str) -> HTMLResponse:
    service = request.app.state.transfer_service
    try:
        file_record = service.get_file_metadata(file_id)
    except TransferError:
        file_record = None
    return templates.TemplateResponse(
        request,
        "file_detail.html",
        {
            "health": service.health(),
            "file": file_record,
            "size_label": size_label,
        },
    )
