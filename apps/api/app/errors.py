import logging
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import config

log = logging.getLogger("app")
MUTATIONS = {"POST", "PUT", "PATCH", "DELETE"}
WITH_BODY = {"POST", "PUT", "PATCH"}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}


def _body(request_id: str, code: str, message: str, fields: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id, "fields": fields or {}}}


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        rid = request.state.request_id
        if request.url.path.startswith("/api/") and request.method in MUTATIONS:
            origin = request.headers.get("origin")
            if origin and not config.host_allowed(urlsplit(origin).hostname):
                return JSONResponse(_body(rid, "forbidden_origin", "Origem não permitida."), status_code=403)
            ctype = request.headers.get("content-type", "")
            if request.method in WITH_BODY and not ctype.startswith("application/json"):
                return JSONResponse(_body(rid, "unsupported_media_type", "Envie JSON."), status_code=415)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return JSONResponse(_body(_rid(request), exc.code, exc.message, exc.fields), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = {".".join(str(p) for p in e["loc"][1:]) or "body": e["msg"] for e in exc.errors()}
        return JSONResponse(_body(_rid(request), "invalid_input", "Revise os campos destacados.", fields), status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("erro inesperado request_id=%s", _rid(request))
        return JSONResponse(_body(_rid(request), "internal_error", "Erro interno. Tente novamente."), status_code=500)
