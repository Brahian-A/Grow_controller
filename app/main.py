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

# ===== Helper para modo CONFIGURATION (Método wpa_supplicant) =====
def _write_wifi_credentials(ssid: str, password: str):
    """
    Escribe las credenciales, detiene el hotspot,
    fuerza la reconexión de wpa_supplicant y reinicia el servicio.
    """
    try:
        # Formatea el bloque de configuración de red
        network_config = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
        # 1. Escribir las nuevas credenciales
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
            f.write(network_config)

        # 2. Detener los servicios del hotspot INMEDIATAMENTE
        # (check=False para que no falle si ya estaban detenidos)
        print("[WIFI_CONFIG] Deteniendo servicios de hotspot...")
        subprocess.run(["killall", "hostapd"], check=False)
        subprocess.run(["systemctl", "stop", "dnsmasq"], check=False)

        # 3. Forzar a wpa_supplicant a releer el archivo y conectarse
        # ESTA ES LA PIEZA CLAVE QUE FALTABA
        print("[WIFI_CONFIG] Forzando reconexión de wpa_supplicant...")
        subprocess.run(["wpa_cli", "-i", "wlan0", "reconfigure"], check=True)
        
        # 4. Darle 10 segundos para que intente establecer la conexión
        print("[WIFI_CONFIG] Esperando 10s para que se establezca la conexión...")
        time.sleep(10) 
        
        # 5. Reiniciar el servicio. 
        # El start.sh ahora verá la IP y entrará en modo NORMAL.
        print("[WIFI_CONFIG] Reiniciando servicio grow_controller...")
        subprocess.run(["systemctl", "restart", "grow_controller.service"], check=True)
        
        return {"status": "ok"}
    
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="No se encontró /etc/wpa_supplicant/wpa_supplicant.conf")
    except subprocess.CalledProcessError as e:
        # Esto es clave: si 'wpa_cli' falla, lo sabremos.
        print(f"Error en subprocess: {e}")
        raise HTTPException(status_code=500, detail=f"Error al ejecutar comando del sistema: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=f"No se pudo escribir la configuración: {e}")

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
            
            # --- ¡AQUÍ USAMOS LA NUEVA FUNCIÓN! ---
            res = _write_wifi_credentials(ssid, password)
            
            if res.get("status") == "ok":
                # El reinicio ya lo maneja la función _write_wifi_credentials
                return {"status": "ok", "message": "Configuración guardada. Reiniciando para conectar..."}
            
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