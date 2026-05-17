from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/crypto", tags=["crypto"])


@router.get("/server-public-key")
async def server_public_key(request: Request) -> dict:
    return request.app.state.transfer_service.server_public_key_response()
