import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path

APP_MODE = os.getenv("APP_MODE", "NORMAL")
if APP_MODE == "NORMAL":
    from app.db.session import engine
    from app.db.base import Base
    from app.api.v1.lecturas import router as lecturas_router
    from app.api.v1.config import router as config_router
    from app.api.v1.mecanismos import router as mecanismos_router

    from app.conexiones.conexion_esp32 import iniciar_lector, get_snapshot, enviar_cmd

def create_app():
    app = FastAPI(title="Greenhouse API")

    if APP_MODE == "CONFIGURATION":
        conf_dir = Path(__file__).parent / "frontend/conf_mode"
        app.mount("/", StaticFiles(directory=conf_dir, html=True), name="setup_form")

        @app.post("/api/v1/wifi")
        async def setup_wifi(credentials: dict):
            ssid = credentials.get("ssid")
            password = credentials.get("password")
            if not ssid or not password:
                raise HTTPException(status_code=400, detail="Nombre y Contraseña requeridos.")
            
            print(f"Recibidas credenciales para la red: {ssid}")
            
            try:
                network_config = f'\nnetwork={{\n    ssid="{ssid}"\n    psk="{password}"\n}}\n'
                with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
                    f.write(network_config)
                
                print("Configuración guardada. Reiniciando el sistema...")
                os.system("sudo reboot &")
                return {"status": "ok", "message": "Credenciales guardadas. Reiniciando..."}
            except Exception as e:
                print(f"Error al guardar configuración: {e}")
                raise HTTPException(status_code=500, detail=f"Error al guardar la configuración: {e}")

    else:
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
