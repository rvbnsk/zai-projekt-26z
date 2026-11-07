import logging
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


def problem(status: int, detail: str | None = None, errors: list | None = None, headers: dict | None = None):
    """Error response in RFC 9457 Problem Details format."""
    body = {"type": "about:blank", "title": HTTPStatus(status).phrase, "status": status}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


async def http_error(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else None
    return problem(exc.status_code, detail, headers=getattr(exc, "headers", None))


async def validation_error(request: Request, exc: RequestValidationError):
    errors = []
    status = 422
    for err in exc.errors():
        location = err["loc"][0] if err["loc"] else ""
        if location == "path":
            # A malformed id cannot point to an existing resource.
            return problem(404, "Resource not found")
        if location == "query" or err["type"] == "json_invalid":
            status = 400
        field = ".".join(str(part) for part in err["loc"][1:])
        errors.append({"field": field, "message": err["msg"]})
    return problem(status, "Invalid request data", errors)


async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return problem(500, "Internal server error")


def register_handlers(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(Exception, unexpected_error)
