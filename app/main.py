import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
import subprocess
import time
from typing import Optional

from app.api.deps import get_db
from app.core.config import config  # (config del venv para después)

APP_MODE = os.getenv("APP_MODE", "NORMAL").upper()  # "NORMAL" | "CONFIGURATION"

# ========= Helpers (solo usados en CONFIGURATION) =========
def _have_nmcli() -> bool:
    try:
        subprocess.check_output(["which", "nmcli"])
        return True
    except Exception:
        return False

def _scan_nmcli():
    """
    Devuelve [{ssid, rssi, secure}] usando nmcli si existe,
    si no, devuelve lista vacía (o podrías simular).
    """
    if not _have_nmcli():
        return []
    out = subprocess.check_output(
        ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
        text=True
    )
    redes = []
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue
        ssid, signal, security = parts
        # SIGNAL es 0-100; aproximamos a dBm para mostrar algo coherente con el front
        try:
            rssi_dbm = int(signal) - 100
        except:
            rssi_dbm = -90
        redes.append({
            "ssid": ssid or "(oculta)",
            "rssi": rssi_dbm,
            "secure": security not in ("", "NONE")
        })
    return redes

def _connect_nmcli(ssid: str, password: Optional[str], is_open: bool = False):
    if not _have_nmcli():
        raise HTTPException(status_code=500, detail="nmcli no disponible en este sistema")
    try:
        if is_open or not password:
            subprocess.run(["nmcli", "dev", "wifi", "connect", ssid], check=True)
        else:
            subprocess.run(["nmcli", "dev", "wifi", "connect", ssid, "password", password], check=True)
        # pequeña espera para que asigne IP
        time.sleep(2)
        # obtener estado
        status = subprocess.check_output(
            ["nmcli", "-t", "-f", "NAME,DEVICE,STATE,IP4.ADDRESS", "con", "show", "--active"],
            text=True
        ).strip()
        if not status:
            return {"status": "connecting"}
        parts = status.split(":")
        ip = parts[3].split("/")[0] if len(parts) > 3 and parts[3] else None
        return {"status": "ok", "ssid": ssid, "ip": ip}
    except subprocess.CalledProcessError:
        return {"status": "error", "message": "Fallo de conexión (contraseña incorrecta o red inalcanzable)"}

def _status_nmcli():
    if not _have_nmcli():
        return {"connected": False, "message": "nmcli no disponible"}
    out = subprocess.check_output(
        ["nmcli", "-t", "-f", "NAME,DEVICE,STATE,IP4.ADDRESS", "con", "show", "--active"],
        text=True
    ).strip()
    if not out:
        return {"connected": False, "message": "No conectado"}
    parts = out.split(":")
    ssid = parts[0] if parts else None
    ip = parts[3].split("/")[0] if len(parts) > 3 and parts[3] else None
    return {"connected": True, "ssid": ssid, "ip": ip}

def _test_ping():
    try:
        start = time.time()
        subprocess.check_output(["ping", "-c", "1", "-W", "2", "8.8.8.8"])
        latency = round((time.time() - start) * 1000)
        return {"ok": True, "latency_ms": latency}
    except subprocess.CalledProcessError:
        return {"ok": False, "message": "Sin conectividad a Internet"}


# ========= Imports de modo NORMAL =========
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
    """application factory: setup middlewares, routes and optional config mode UI"""
    app = FastAPI(title="Greenhouse API", version="1.0.0")

    # -------- Middlewares --------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # si restringes, pon tus dominios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # =========================================================
    #                     MODO CONFIGURATION
    # =========================================================
    if APP_MODE == "CONFIGURATION":
        conf_dir = Path(__file__).parent / "frontend" / "conf_mode"
        if not conf_dir.exists():
            raise RuntimeError(f"No existe la carpeta de front de configuración: {conf_dir}")

        # Front del portal cautivo (sirve index.html del canvas)
        app.mount("/", StaticFiles(directory=conf_dir, html=True), name="wifi_setup")

        # Endpoints que espera el front (sin prefijo)
        @app.get("/scan")
        async def scan_networks():
            return _scan_nmcli()

        @app.post("/connect")
        async def connect_wifi(payload: dict):
            ssid = (payload.get("ssid") or "").strip()
            password = payload.get("password") or ""
            if not ssid:
                raise HTTPException(status_code=400, detail="SSID requerido")
            return _connect_nmcli(ssid, password, is_open=(password == ""))

        @app.get("/status")
        async def wifi_status():
            return _status_nmcli()

        @app.post("/test")
        async def test_connection():
            return _test_ping()

        # Compatibilidad con tu endpoint previo
        @app.post("/api/v1/wifi")
        async def setup_wifi(credentials: dict):
            ssid = (credentials.get("ssid") or "").strip()
            password = credentials.get("password") or ""
            if not ssid:
                raise HTTPException(status_code=400, detail="Nombre (SSID) requerido.")
            # puedes reutilizar nmcli para que sea consistente
            res = _connect_nmcli(ssid, password, is_open=(password == ""))
            if res.get("status") == "ok":
                # si querés reiniciar tras configurar:
                # os.system("sudo reboot &")
                return {"status": "ok", "message": "Conectado. (No se reinició automáticamente)"}
            elif res.get("status") == "connecting":
                return {"status": "connecting", "message": "Intentando conectar"}
            raise HTTPException(status_code=500, detail=res.get("message", "Error al conectar"))

        return app

    # =========================================================
    #                        MODO NORMAL
    # =========================================================
    # creacion de las tablas de la db (hasta agregar migraciones)
    Base.metadata.create_all(bind=engine)

    # Routers API
    app.include_router(lecturas_router,   prefix="/api/v1")
    app.include_router(config_router,     prefix="/api/v1")
    app.include_router(mecanismos_router, prefix="/api/v1")
    app.include_router(system_router,     prefix="/api/v1")
    app.include_router(devices_router,    prefix="/api/v1")

    # Healthcheck
    @app.get("/health")
    async def health_check(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

    # Front principal de la app
    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    @app.on_event("startup")
    def _startup():
        """Inicia el lector serie de la(s) ESP32 al arrancar el servidor"""
        try:
            iniciar_lector()
        except Exception as e:
            # Evitar que crashee todo si no hay ESP conectada en ese momento
            print(f"[WARN] iniciar_lector() no se pudo iniciar: {e}")

    return app


app = create_app()
