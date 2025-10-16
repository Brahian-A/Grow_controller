from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.db.session import engine
from app.db.base import Base
from app.api.v1.lecturas import router as lecturas_router
from app.api.v1.config import router as config_router
from app.api.v1.mecanismos import router as mecanismos_router


def create_app():
    app = FastAPI(title="Greenhouse API")
    Base.metadata.create_all(bind=engine)

    # Rutas API
    app.include_router(lecturas_router)
    app.include_router(config_router)
    app.include_router(mecanismos_router)

    # Frontend
    frontend_dir = Path(__file__).parent / "frontend"
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
