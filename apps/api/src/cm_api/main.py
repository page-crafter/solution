import os
from pathlib import Path

from cm_shared.db.init import create_database_schema
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from cm_api.routers import (
    auth,
    chat,
    confluence,
    jobs,
    kpis,
    lightrag_status,
    page_editor,
    spaces,
    sync,
)

DEFAULT_FRONTEND_DIST_DIR = Path("apps/web/dist")


def frontend_dist_dir() -> Path:
    """Return the built Vue app directory, if it exists in this runtime."""
    return Path(os.getenv("FRONTEND_DIST_DIR", DEFAULT_FRONTEND_DIST_DIR)).resolve()


def resolve_frontend_file(frontend_dir: Path, request_path: str) -> Path | None:
    """Resolve a static frontend path without allowing traversal outside dist."""
    candidate = (frontend_dir / request_path).resolve()
    if candidate != frontend_dir and frontend_dir not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def mount_frontend(app: FastAPI) -> None:
    """Serve the compiled Vue app from FastAPI when the dist directory is present."""
    frontend_dir = frontend_dist_dir()
    index_file = frontend_dir / "index.html"
    if not index_file.is_file():
        return

    assets_dir = frontend_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/config.json", include_in_schema=False)
    def serve_frontend_config() -> FileResponse:
        config_file = frontend_dir / "config.json"
        if not config_file.is_file():
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(
            config_file,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/", include_in_schema=False)
    def serve_frontend_index() -> FileResponse:
        return FileResponse(index_file, media_type="text/html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_route(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        static_file = resolve_frontend_file(frontend_dir, full_path)
        if static_file is not None:
            return FileResponse(static_file)

        return FileResponse(index_file, media_type="text/html")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(title="Page Crafter API", version="0.1.0")
    app.include_router(auth.router, prefix="/api")
    app.include_router(kpis.router, prefix="/api")
    app.include_router(sync.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(confluence.router, prefix="/api")
    app.include_router(page_editor.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(spaces.router, prefix="/api")
    app.include_router(lightrag_status.router, prefix="/api")
    mount_frontend(app)
    return app


app = create_app()


@app.on_event("startup")
def on_startup() -> None:
    create_database_schema()
