from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import io, csv

from app.db.session import SessionLocal
from app.db.models import Lectura, Mecanismos, Config

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

# ----------------- Helper ESP32 (import perezoso y tolerante) -----------------
def _get_esp32_connection():
    "Intenta importar y obtener la conexión a la ESP32 sólo cuando se necesite"
    try:
        from app.conexiones.conexion_esp32 import obtener_conexion
    except Exception as e:
        # No rompas el server por esto
        print("[ESP32] módulo no disponible:", e)
        return None

    try:
        return obtener_conexion()
    except Exception as e:
        print("[ESP32] no se pudo abrir conexión:", e)
        return None

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
    "Devuelve estado de mecanismos. Si hay ESP32, sincroniza con snapshot();"
    stat = db.query(Mecanismos).first()
    if not stat:
        stat = guardar(db, Mecanismos())

    cx = _get_esp32_connection()
    if cx is not None:
        try:
            snap = cx.snapshot()  # debe devolver dict con keys conocidos
            # Campos esperados del snapshot (ajustá si tu driver usa otros nombres)
            if "bomba" in snap:       stat.bomba = bool(snap["bomba"])
            if "ventilador" in snap:  stat.ventilador = bool(snap["ventilador"])
            if "lamparita" in snap:   stat.lamparita = bool(snap["lamparita"])
            if "nivel_agua" in snap:  stat.nivel_agua = int(snap["nivel_agua"])
            # Persistimos espejo en BD para que el front vea el estado
            stat = guardar(db, stat)
        except Exception as e:
            print("[ESP32] snapshot falló:", e)
            # devolvemos lo que tengamos en BD

    return stat

def set_mecanismo(
    bomba: Optional[bool] = None,
    lamparita: Optional[bool] = None,
    ventilador: Optional[bool] = None,
    nivel_agua: Optional[int] = None,
) -> Mecanismos:
    "Intenta mandar el cambio a la ESP32 si está disponible"
    cx = _get_esp32_connection()
    if cx is not None:
        try:
            if bomba is not None:      cx.set_bomba(bool(bomba))
            if ventilador is not None: cx.set_ventilador(bool(ventilador))
            if lamparita is not None:  cx.set_lamparita(bool(lamparita))
        except Exception as e:
            print("[ESP32] set_mecanismo falló", e)

    with _with_session() as db:
        mech = db.query(Mecanismos).first()
        if not mech:
            mech = Mecanismos()

        if bomba is not None:      mech.bomba = bool(bomba)
        if lamparita is not None:  mech.lamparita = bool(lamparita)
        if ventilador is not None: mech.ventilador = bool(ventilador)
        if nivel_agua is not None: mech.nivel_agua = int(nivel_agua)

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

def ultimas_lecturas_7d() -> List[Lectura]:
    "devuelve todas las lecturas dentro de los últimos 7 días (orden desc)"
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    with _with_session() as db:
        stmt = (
            select(Lectura)
            .where(Lectura.fecha_hora >= cutoff)
            .order_by(desc(Lectura.fecha_hora))
        )
        return db.execute(stmt).scalars().all()

def csv_from(days: int) -> str:
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=days)

    with _with_session() as db:
        stmt = (
            select(
                Lectura.fecha_hora,
                Lectura.temperatura,
                Lectura.humedad_suelo,
                Lectura.humedad,
            )
            .where(Lectura.fecha_hora >= cutoff, Lectura.fecha_hora <= now_utc)
            .order_by(desc(Lectura.fecha_hora))
        )
        rows = db.execute(stmt).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["fecha_hora", "temperatura", "humedad_suelo", "humedad"])

    tz = ZoneInfo("America/Montevideo")
    for dt, temperatura, humedad_suelo, humedad in rows:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        'fecha/hora'
        dt_local = dt.astimezone(tz).isoformat()

        'formateo con simbolos'
        temp = f"{temperatura:.1f} °C"
        hum_suelo = f"{humedad_suelo:.1f} %"
        hum = f"{humedad:.1f} %"

        writer.writerow([dt_local, temp, hum_suelo, hum])

    return buf.getvalue()