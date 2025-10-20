import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import config  # (config del venv para después)

APP_MODE = os.getenv("APP_MODE", "NORMAL")

if APP_MODE == "NORMAL":
    from app.db.session import engine, SessionLocal
    from app.db.base import Base

    # API
    from app.api.v1.lecturas import router as lecturas_router
    from app.api.v1.config import router as config_router
    from app.api.v1.mecanismos import router as mecanismos_router
    from app.api.v1.system import router as system_router
    from app.api.v1.devices import router as devices_router

    # Conexión ESP32
    from app.conexiones.conexion_esp32 import iniciar_lector


def create_app() -> FastAPI:
    "application factory: setup middlewares, routes and optional config mode UI"
    app = FastAPI(title="Greenhouse API")

    # middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Modo CONFIG (solo formulario Wi-Fi) 
    if APP_MODE == "CONFIGURATION":
        conf_dir = Path(__file__).parent / "frontend" / "conf_mode"
        app.mount("/", StaticFiles(directory=conf_dir, html=True), name="setup_form")

        @app.post("/api/v1/wifi")
        async def setup_wifi(credentials: dict):
            ssid = credentials.get("ssid")
            password = credentials.get("password")
            if not ssid or not password:
                raise HTTPException(status_code=400, detail="Nombre y Contraseña requeridos.")
            try:
                network_config = (
                    '\nnetwork={\n'
                    f'      ssid="{ssid}"\n'
                    f'      psk="{password}"\n'
                    '}\n'
                )
                with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
                    f.write(network_config)
                os.system("sudo reboot &")
                return {"status": "ok", "message": "Credenciales guardadas. Reiniciando..."}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al guardar la configuración: {e}")

    else:
        # creacion de las tablas de la db provisional hasta agregar migraciones
        Base.metadata.create_all(bind=engine)

        # rutas(con y sin prefijo)
        app.include_router(lecturas_router,   prefix="/api/v1")
        app.include_router(config_router,     prefix="/api/v1")
        app.include_router(mecanismos_router, prefix="/api/v1")
        app.include_router(system_router,     prefix="/api/v1")
        app.include_router(devices_router, prefix="/api/v1")

        # rutas sin prefijo si ellas no funciona el front

        # endpoint de salud
        @app.get("/health")
        async def health_check(db: Session = Depends(get_db)):
            try:
                db.execute(text("SELECT 1"))
                return {"status": "healthy", "database": "connected"}
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

        # frontend
        frontend_dir = Path(__file__).parent / "frontend"
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

        @app.on_event("startup")
        def _startup():
            "Inicia el lector serie de la(s) ESP32 al arrancar el servidor"
            iniciar_lector()

    return app


app = create_app()
