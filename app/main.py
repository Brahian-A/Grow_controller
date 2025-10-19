import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import config # config del venv para depues (base de datos y cors para la api)

APP_MODE = os.getenv("APP_MODE", "NORMAL")

if APP_MODE == "NORMAL":
    from app.db.session import engine, SessionLocal
    from app.db.base import Base
    from app.api.v1.lecturas import router as lecturas_router
    from app.api.v1.config import router as config_router
    from app.api.v1.mecanismos import router as mecanismos_router
    from app.api.v1.system import router as system_router

    from app.conexiones.conexion_esp32 import iniciar_lector


def create_app() -> FastAPI:
    app = FastAPI(title="Greenhouse API")
    # middlewares basicos
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    if APP_MODE == "CONFIGURATION":
        # mini front de configuración wifi
        conf_dir = Path(__file__).parent / "frontend" / "conf_mode"
        app.mount("/", StaticFiles(directory=conf_dir, html=True), name="setup_form")

        @app.post("/api/v1/wifi")
        async def setup_wifi(credentials: dict):
            ssid = credentials.get("ssid")
            password = credentials.get("password")
            if not ssid or not password:
                raise HTTPException(status_code=400, detail="Nombre y Contraseña requeridos.")

            print(f"Recibidas credenciales para la red: {ssid}")
            try:
                network_config = (
                    '\nnetwork={\n'
                    f'      ssid="{ssid}"\n'
                    f'      psk="{password}"\n'
                    '}\n'
                )
                with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
                    f.write(network_config)

                print("Configuración guardada. Reiniciando el sistema...")
                os.system("sudo reboot &")
                return {"status": "ok", "message": "Credenciales guardadas. Reiniciando..."}
            except Exception as e:
                print(f"Error al guardar configuración: {e}")
                raise HTTPException(status_code=500, detail=f"Error al guardar la configuración: {e}")

    else:
        # lo dejamos por ahora para que todo ande
        #Cuando metemos migraciones lo quitamos de aca
        Base.metadata.create_all(bind=engine)

        # rutas de la api
        app.include_router(lecturas_router, prefix="/api/v1")
        app.include_router(config_router, prefix="/api/v1")
        app.include_router(mecanismos_router, prefix="/api/v1")
        app.include_router(system_router, prefix="/api/v1")
        
        @app.get("/health")
        async def health_check(db: Session = Depends(get_db)):
            try:
                db.execute(text("SELECT 1"))
                return {"status": "healthy", "database": "connected"}
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

        frontend_dir = Path(__file__).parent / "frontend" / "api"
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
        
        @app.on_event("startup")
        def _startup():
            iniciar_lector()

    return app


app = create_app()