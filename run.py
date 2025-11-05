import os
import socket
import uvicorn
from pathlib import Path

from app.db.session import engine, SQLALCHEMY_DATABASE_URL
from app.db.base import Base
from app.db import models 

def create_db():
    """
    Verifica si la base de datos (app.db) existe.
    Si no existe, la crea con todas las tablas.
    """

    db_path_str = SQLALCHEMY_DATABASE_URL.split("sqlite:///", 1)[-1]
    db_path = Path(db_path_str)

    if not db_path.exists():
        print(f"Base de datos no encontrada en '{db_path}'. Creando...")
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)

            Base.metadata.create_all(bind=engine)
            print("Base de datos y tablas creadas con éxito.")
        except Exception as e:
            print(f"¡ERROR CRÍTICO! No se pudo crear la base de datos: {e}")
            raise
    else:
        print(f"Base de datos encontrada en '{db_path}'. Omitiendo creación.")

def get_ip():
    try:
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
    create_db()

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