from app.db.session import engine
from app.db.base import Base
import os
import socket
import uvicorn

def init_db():
    """Crea todas las tablas si no existen."""
    print("Base de datos verificada/creada (idempotente).")

def get_ip():
    try:
        # Método simple y sin dependencias extra
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass
    return ip

def main():
    init_db()

    host = "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    ip_for_msg = get_ip()
    app_mode = os.getenv("APP_MODE", "NORMAL")
    reload_flag = os.getenv("RELOAD", "0") == "1"

    print(f"[APP_MODE={app_mode}] Iniciando FastAPI en http://{ip_for_msg}:{port} (host={host})")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_flag,
        workers=1,           
        proxy_headers=False, 
    )

if __name__ == "__main__":
    main()
