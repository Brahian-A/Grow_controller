from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import io, csv

from app.db.models import Lectura, Mecanismos, Config

# ----------------- Utilidades de persistencia -----------------
def guardar(db: Session, obj):
    """
    Agrega o actualiza un objeto y sincroniza su estado con la sesión.
    NO hace commit (el commit lo maneja get_db en la capa API).
    """
    db.add(obj)
    # flush para asegurar PKs y defaults server-side
    db.flush()
    db.refresh(obj)
    return obj

# ----------------- Helper ESP32 (import perezoso y tolerante) -----------------
def _get_esp32_connection():
    "Intenta importar y obtener la conexión a la ESP32 sólo cuando se necesite"
    try:
        from app.conexiones.conexion_esp32 import obtener_conexion  # si existe
    except Exception as e:
        print("[ESP32] módulo no disponible:", e)
        return None

    try:
        return obtener_conexion()
    except Exception as e:
        print("[ESP32] no se pudo abrir conexión:", e)
        return None

# ----------------- Configuración -----------------
def get_config(db: Session, *, create_if_missing: bool = False) -> Optional[Config]:
    cfg = db.query(Config).first()
    if not cfg and create_if_missing:
        cfg = guardar(db, Config())
    return cfg

def _validar_config_parcial(
    *,
    humedad_suelo_umbral_alto: Optional[int] = None,
    humedad_suelo_umbral_bajo: Optional[int] = None,
    temperatura_umbral_alto: Optional[int] = None,
    temperatura_umbral_bajo: Optional[int] = None,
    humedad_umbral_alto: Optional[int] = None,
    humedad_umbral_bajo: Optional[int] = None,
) -> None:
    # Rango básico
    def _chk_pct(x: Optional[int], nombre: str):
        if x is not None and not (0 <= x <= 100):
            raise ValueError(f"{nombre} debe estar entre 0 y 100")

    def _chk_temp(x: Optional[int], nombre: str):
        # Ajustá a tu caso; pongo -10..60 como rangos razonables
        if x is not None and not (-10 <= x <= 60):
            raise ValueError(f"{nombre} debe estar entre -10 y 60 °C")

    _chk_pct(humedad_suelo_umbral_alto, "humedad_suelo_umbral_alto")
    _chk_pct(humedad_suelo_umbral_bajo, "humedad_suelo_umbral_bajo")
    _chk_pct(humedad_umbral_alto, "humedad_umbral_alto")
    _chk_pct(humedad_umbral_bajo, "humedad_umbral_bajo")
    _chk_temp(temperatura_umbral_alto, "temperatura_umbral_alto")
    _chk_temp(temperatura_umbral_bajo, "temperatura_umbral_bajo")

    # Relaciones alto > bajo si se informan ambos
    if (humedad_suelo_umbral_alto is not None and
        humedad_suelo_umbral_bajo is not None and
        not (humedad_suelo_umbral_alto > humedad_suelo_umbral_bajo)):
        raise ValueError("humedad_suelo_umbral_alto debe ser > humedad_suelo_umbral_bajo")

    if (temperatura_umbral_alto is not None and
        temperatura_umbral_bajo is not None and
        not (temperatura_umbral_alto > temperatura_umbral_bajo)):
        raise ValueError("temperatura_umbral_alto debe ser > temperatura_umbral_bajo")

    if (humedad_umbral_alto is not None and
        humedad_umbral_bajo is not None and
        not (humedad_umbral_alto > humedad_umbral_bajo)):
        raise ValueError("humedad_umbral_alto debe ser > humedad_umbral_bajo")

def set_config(
    db: Session,
    *,
    humedad_suelo_umbral_alto: Optional[int] = None,
    humedad_suelo_umbral_bajo: Optional[int] = None,
    temperatura_umbral_alto: Optional[int] = None,
    temperatura_umbral_bajo: Optional[int] = None,
    humedad_umbral_alto: Optional[int] = None,
    humedad_umbral_bajo: Optional[int] = None,
) -> Config:
    # Validación de entradas
    _validar_config_parcial(
        humedad_suelo_umbral_alto=humedad_suelo_umbral_alto,
        humedad_suelo_umbral_bajo=humedad_suelo_umbral_bajo,
        temperatura_umbral_alto=temperatura_umbral_alto,
        temperatura_umbral_bajo=temperatura_umbral_bajo,
        humedad_umbral_alto=humedad_umbral_alto,
        humedad_umbral_bajo=humedad_umbral_bajo,
    )

    cfg = get_config(db, create_if_missing=True)
    # Asignaciones parciales
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
    "Devuelve estado de mecanismos. Si hay ESP32, sincroniza con snapshot()."
    stat = db.query(Mecanismos).first()
    if not stat:
        stat = guardar(db, Mecanismos())

    cx = _get_esp32_connection()
    if cx is not None:
        try:
            snap = cx.snapshot()  # dict con keys conocidos
            if "bomba" in snap:       stat.bomba = bool(snap["bomba"])
            if "ventilador" in snap:  stat.ventilador = bool(snap["ventilador"])
            if "lamparita" in snap:   stat.lamparita = bool(snap["lamparita"])
            if "nivel_agua" in snap and hasattr(stat, "nivel_agua"):
                stat.nivel_agua = int(snap["nivel_agua"])
            stat = guardar(db, stat)
        except Exception as e:
            print("[ESP32] snapshot falló:", e)

    return stat

def set_mecanismo(
    db: Session,
    *,
    bomba: Optional[bool] = None,
    lamparita: Optional[bool] = None,
    ventilador: Optional[bool] = None,
    nivel_agua: Optional[int] = None,
) -> Mecanismos:
    "Intenta mandar el cambio a la ESP32 si está disponible y persiste espejo."
    cx = _get_esp32_connection()
    if cx is not None:
        try:
            if bomba is not None:      cx.set_bomba(bool(bomba))
            if ventilador is not None: cx.set_ventilador(bool(ventilador))
            if lamparita is not None:  cx.set_lamparita(bool(lamparita))
        except Exception as e:
            print("[ESP32] set_mecanismo falló", e)

    mech = db.query(Mecanismos).first()
    if not mech:
        mech = Mecanismos()

    if bomba is not None:      mech.bomba = bool(bomba)
    if lamparita is not None:  mech.lamparita = bool(lamparita)
    if ventilador is not None: mech.ventilador = bool(ventilador)
    if nivel_agua is not None and hasattr(mech, "nivel_agua"):
        mech.nivel_agua = int(nivel_agua)

    return guardar(db, mech)

# ----------------- Lecturas -----------------
def agregar_lectura(
    db: Session,
    *,
    temperatura: float,
    humedad: float,
    humedad_suelo: float,
    nivel_de_agua: float,
) -> Lectura:
    obj = Lectura(
        temperatura=temperatura,
        humedad=humedad,
        humedad_suelo=humedad_suelo,
        nivel_de_agua=nivel_de_agua,
    )
    return guardar(db, obj)

def ultima_lectura(db: Session) -> Optional[Lectura]:
    stmt = select(Lectura).order_by(desc(Lectura.fecha_hora)).limit(1)
    return db.execute(stmt).scalars().first()

def ultimas_lecturas_7d(db: Session) -> List[Lectura]:
    "Devuelve todas las lecturas dentro de los últimos 7 días (orden desc)."
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(Lectura)
        .where(Lectura.fecha_hora >= cutoff)
        .order_by(desc(Lectura.fecha_hora))
    )
    return db.execute(stmt).scalars().all()

def csv_from(db: Session, days: int) -> str:
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=days)

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
        dt_local = dt.astimezone(tz).isoformat()  # <-- FALTABAN PARÉNTESIS
        writer.writerow([dt_local, temperatura, humedad_suelo, humedad])

    return buf.getvalue()
