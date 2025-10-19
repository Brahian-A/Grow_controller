from app.db.session import engine
from app.db.base import Base
from app.db.models import Lectura, Mecanismos, Config, Evento
import uvicorn

def init_db():
    """Crea todas las tablas si no existen."""
    Base.metadata.create_all(bind=engine)
    print("Base de datos creada e inicializada correctamente")

def main():
    init_db()

    print("Iniciando servidor FastAPI en http://127.0.0.1:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
