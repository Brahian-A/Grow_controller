from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.session import SessionLocal
from app.db.models import Lectura, Mecanismos, Config

from app.conexiones.conexion_esp32 import obtener_conexion


# ----------------- Sesión y utilidad guardar -----------------
def _with_session():
    "abrir y cerrar una sesion"
    class _Ctx:
        def __enter__(self):
            self.db = SessionLocal()
            return self.db
        def __exit__(self, exc_type, exc, tb):
            try:
                if exc:
                    self.db.rollback()
                else:
                    self.db.commit()
            finally:
                self.db.close()
    return _Ctx()


def guardar(db: Session, obj):
    "agrega un objeto y hace commit "
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ----------------- Configuración -----------------
def get_config(db: Session) -> Config:
    cfg = db.query(Config).first()
    if not cfg:
        cfg = guardar(db, Config())
    return cfg


def set_config(
    humedad_suelo_umbral_alto: Optional[int] = None,
    humedad_suelo_umbral_bajo: Optional[int] = None,
    temperatura_umbral_alto: Optional[int] = None,
    temperatura_umbral_bajo: Optional[int] = None,
    humedad_umbral_alto: Optional[int] = None,
    humedad_umbral_bajo: Optional[int] = None,
) -> Config:
    with _with_session() as db:
        cfg = get_config(db)
        if humedad_suelo_umbral_alto is not None:
            cfg.humedad_suelo_umbral_alto = humedad_suelo_umbral_alto
        if humedad_suelo_umbral_bajo is not None:
            cfg.humedad_suelo_umbral_bajo = humedad_suelo_umbral_bajo
        if temperatura_umbral_alto is not None:
            cfg.temperatura_umbral_alto = temperatura_umbral_alto
        if temperatura_umbral_bajo is not None:
            cfg.temperatura_umbral_bajo = temperatura_umbral_bajo
        if humedad_umbral_alto is not None:
            cfg.humedad_umbral_alto = humedad_umbral_alto
        if humedad_umbral_bajo is not None:
            cfg.humedad_umbral_bajo = humedad_umbral_bajo
        return guardar(db, cfg)


# ----------------- Mecanismos -----------------
def get_status(db: Session) -> Mecanismos:
   
    stat = db.query(Mecanismos).first()
    if not stat:
        stat = guardar(db, Mecanismos())

    cx = obtener_conexion()
    snap = cx.snapshot()

    stat.bomba = snap["bomba"]
    stat.ventilador = snap["ventilador"]
    stat.lamparita = snap["lamparita"]
    stat.nivel_agua = snap["nivel_agua"]

    return stat


def set_mecanismo(
    bomba: Optional[bool] = None,
    lamparita: Optional[bool] = None,
    ventilador: Optional[bool] = None,
    nivel_agua: Optional[int] = None,
) -> Mecanismos:
    
    cx = obtener_conexion()
    if bomba is not None:
        cx.set_bomba(bool(bomba))
    if ventilador is not None:
        cx.set_ventilador(bool(ventilador))
    if lamparita is not None:
        cx.set_lamparita(bool(lamparita))

    # Persistir espejo en BD   tal como ya lo hacías
    with _with_session() as db:
        mech = get_status(db)

        if bomba is not None:
            mech.bomba = bool(bomba)
        if lamparita is not None:
            mech.lamparita = bool(lamparita)
        if ventilador is not None:
            mech.ventilador = bool(ventilador)
        if nivel_agua is not None:
            mech.nivel_agua = int(nivel_agua)

        return guardar(db, mech)


# ----------------- Lecturas -----------------
def agregar_lectura(
    temperatura: float,
    humedad: float,
    humedad_suelo: float,
    nivel_de_agua: float,
) -> Lectura:
    with _with_session() as db:
        obj = Lectura(
            temperatura=temperatura,
            humedad=humedad,
            humedad_suelo=humedad_suelo,
            nivel_de_agua=nivel_de_agua,
        )
        return guardar(db, obj)


def ultima_lectura() -> Optional[Lectura]:
    with _with_session() as db:
        lecturas = select(Lectura).order_by(desc(Lectura.fecha_hora)).limit(1)
        return db.execute(lecturas).scalars().first()


def ultimas_lecturas(limit: int = 20) -> List[Lectura]:
    with _with_session() as db:
        lecturas = select(Lectura).order_by(desc(Lectura.fecha_hora)).limit(limit)
        return list(db.execute(lecturas).scalars().all())
