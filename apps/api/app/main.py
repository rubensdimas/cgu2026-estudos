from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import config, errors
from app.catalog.router import router as catalog_router
from app.flashcards.router import router as flashcards_router
from app.game.mission_router import router as mission_router
from app.game.router import router as game_router
from app.guidance.router import router as guidance_router
from app.planning.router import router as planning_router
from app.reviews.router import router as reviews_router
from app.study.router import router as study_router


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

    for router in (catalog_router, planning_router, study_router, game_router, mission_router, guidance_router,
                   flashcards_router, reviews_router):
        api.include_router(router)
    app.include_router(api)
    mount_spa(app)
    return app


app = create_app()
