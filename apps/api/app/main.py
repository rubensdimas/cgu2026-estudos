from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import config, errors


def mount_spa(app: FastAPI) -> None:
    static = config.STATIC_DIR.resolve()
    if not (static / "index.html").is_file():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise errors.ApiError(404, "not_found", "Rota inexistente.")
        candidate = (static / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static):
            return FileResponse(candidate)
        return FileResponse(static / "index.html")


def create_app() -> FastAPI:
    app = FastAPI(title="CGU 2026", docs_url="/api/docs", openapi_url="/api/openapi.json")
    errors.install(app)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)
    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    for router in ():  # cada tarefa seguinte registra seu roteador aqui
        api.include_router(router)
    app.include_router(api)
    mount_spa(app)
    return app


app = create_app()
