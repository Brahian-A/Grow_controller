from app.db.session import SessionLocal
from app.servicios.funciones import guardar_lectura, ultima_lectura

class Facade:
    def agregar_lectura(self, temperatura, humedad, humedad_suelo, nivel_de_agua):
        with SessionLocal() as db:
            return guardar_lectura(db, temperatura, humedad, humedad_suelo, nivel_de_agua)

    def obtener_ultima(self):
        with SessionLocal() as db:
            return ultima_lectura(db)
