"""JSON response helpers matching the legacy Flask API envelope."""
from fastapi import HTTPException
from fastapi.responses import JSONResponse


def success_json(content: dict, status_code: int = 200) -> JSONResponse:
    payload = {"success": True, **content}
    return JSONResponse(status_code=status_code, content=payload)


def error_json(status_code: int, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message},
    )


def legacy_error_response(request, exc: HTTPException) -> JSONResponse:
    """Exception handler: preserve {success, error} shape from HTTPException.detail."""
    detail = exc.detail
    if isinstance(detail, dict) and "success" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(detail)},
    )
