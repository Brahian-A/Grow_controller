import os, time, subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.mqtt_client import start_mqtt_listener

from app.api.deps import get_db
from app.core.config import config  # noqa

APP_MODE = (os.getenv("APP_MODE", "NORMAL") or "NORMAL").upper()

# ===== Helpers mínimos para modo CONFIGURATION (nmcli) =====
def _has_nmcli() -> bool:
    try:    
        subprocess.check_output(["which", "nmcli"])
        return True
    except Exception:
        return False

def _nmcli_connect(ssid: str, password: str):
    if not _has_nmcli():
        raise HTTPException(status_code=500, detail="nmcli no disponible")
    try:
        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            cmd += ["password", password]
        subprocess.run(cmd, check=True)
        time.sleep(2)
        # Lee IP actual (si ya tomó DHCP)
        st = subprocess.check_output(
            ["nmcli", "-t", "-f", "NAME,IP4.ADDRESS", "con", "show", "--active"],
            text=True
        ).strip()
        ip = None
        if st:
            parts = st.split(":")
            ip = parts[1].split("/")[0] if len(parts) > 1 and parts[1] else None
        return {"status": "ok", "ip": ip}
    except subprocess.CalledProcessError:
        return {"status": "error", "message": "No se pudo conectar (clave o alcance)."}

# ===== Imports sólo si estamos en NORMAL =====
if APP_MODE == "NORMAL":
    from app.db.session import engine  # noqa
    from app.db.base import Base  # noqa
    from app.api.v1.lecturas import router as lecturas_router  # noqa
    from app.api.v1.config import router as config_router  # noqa
    from app.api.v1.mecanismos import router as mecanismos_router  # noqa
    from app.api.v1.system import router as system_router  # noqa
    from app.api.v1.devices import router as devices_router  # noqa
    from app.api.v1.gemini import router as gemini_router
    from app.conexiones.conexion_esp32 import iniciar_lector  # noqa


def create_app() -> FastAPI:
    app = FastAPI(title="Greenhouse API")

    # Middlewares básicos
    app.add_middleware(CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"]
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ---------- CONFIGURATION: portal Wi-Fi + endpoint mínimo ----------
    if APP_MODE == "CONFIGURATION":
        conf_dir = Path(__file__).parent / "frontend" / "conf_mode"
        conf_dir.mkdir(parents=True, exist_ok=True)

        @app.post("/api/v1/wifi")
        async def setup_wifi(payload: dict):
            ssid = (payload.get("ssid") or "").strip()
            password = payload.get("password") or ""
            if not ssid:
                raise HTTPException(status_code=400, detail="Nombre (SSID) requerido.")
            res = _nmcli_connect(ssid, password)
            if res.get("status") == "ok":
                return {"status": "ok", "message": "Conectado. Reinicia para modo NORMAL.", "ip": res.get("ip")}
            raise HTTPException(status_code=500, detail=res.get("message", "Error de conexión"))

        # Monta el front DESPUÉS de definir el endpoint
        app.mount("/", StaticFiles(directory=conf_dir, html=True), name="wifi_setup")
        return app

    # ---------- NORMAL: API + front principal ----------
    Base.metadata.create_all(bind=engine)  # hasta agregar migraciones

    #inicia el mosquitto 
    start_mqtt_listener()

    app.include_router(lecturas_router,   prefix="/api/v1")
    app.include_router(config_router,     prefix="/api/v1")
    app.include_router(mecanismos_router, prefix="/api/v1")
    app.include_router(system_router,     prefix="/api/v1")
    app.include_router(devices_router,    prefix="/api/v1")
    app.include_router(gemini_router,     prefix="/api/v1")

    @app.get("/health")
    async def health(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Database error: {e}")

    frontend_dir = Path(__file__).parent / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    @app.on_event("startup")
    def _startup():
        try:
            iniciar_lector()
        except Exception as e:
            print(f"[WARN] iniciar_lector(): {e}")

    return app


app = create_app()
