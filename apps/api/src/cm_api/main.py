from cm_shared.db.init import create_database_schema
from cm_shared.settings.app import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(title="Page Crafter API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth.router, prefix="/api")
    app.include_router(kpis.router, prefix="/api")
    app.include_router(sync.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(confluence.router, prefix="/api")
    app.include_router(page_editor.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(spaces.router, prefix="/api")
    app.include_router(lightrag_status.router, prefix="/api")
    return app


app = create_app()


@app.on_event("startup")
def on_startup() -> None:
    create_database_schema()
