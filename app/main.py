from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.db.session import engine
from app.db.base import Base
from app.api.v1.lecturas import router as lecturas_router
from app.api.v1.config import router as config_router
from app.api.v1.mecanismos import router as mecanismos_router

from app.conexiones.conexion_esp32 import iniciar_lector, get_snapshot, enviar_cmd

def create_app():
    app = FastAPI(title="Greenhouse API")
    Base.metadata.create_all(bind=engine)

    app.include_router(lecturas_router)
    app.include_router(config_router)
    app.include_router(mecanismos_router)

    frontend_dir = Path(__file__).parent / "frontend"
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    @app.on_event("startup")
    def _startup():
        iniciar_lector()

    @app.get("/snapshot")
    def snapshot():
        return get_snapshot()

    @app.post("/mecanismos/{target}/{value}")
    def set_mecanismo(target: str, value: str):
        target = target.upper()
        value  = value.upper()
        if target not in ("RIEGO","VENT","LUZ") or value not in ("ON","OFF"):
            return {"ok": False, "error": "target/value inválidos"}
        enviar_cmd({"cmd":"SET","target":target,"value":value})
        return {"ok": True}

    @app.post("/status")
    def pedir_status():
        enviar_cmd({"cmd":"STATUS"})
        return {"ok": True}

    return app

app = create_app()
