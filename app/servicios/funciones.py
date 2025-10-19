from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import io, csv

from app.db.session import SessionLocal
from app.db.models import Lectura, Mecanismos, Config

# ----------------- db

def guardar(db: Session, obj):
    "agrega un objeto y hace commit"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# ----------------- helper ESP32
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

# ----------------- configuracion
def get_config(db: Session) -> Config:
    # Esta función recibe 'db' de FastAPI y lo usa directamente.
    cfg = db.query(Config).first()
    if not cfg:
        cfg = guardar(db, Config())
    return cfg

def set_config(db: Session,
    humedad_suelo_umbral_alto: Optional[int] = None,
    humedad_suelo_umbral_bajo: Optional[int] = None,
    temperatura_umbral_alto: Optional[int] = None,
    temperatura_umbral_bajo: Optional[int] = None,
    humedad_umbral_alto: Optional[int] = None,
    humedad_umbral_bajo: Optional[int] = None,
) -> Config:
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

# ----------------- mecanismos 
def get_status(db: Session) -> Mecanismos:
    "Devuelve estado de mecanismos. Si hay ESP32, sincroniza con snapshot();"
    stat = db.query(Mecanismos).first()
    if not stat:
        stat = guardar(db, Mecanismos())

    cx = _get_esp32_connection()
    if cx is not None:
        try:
            
            snap = cx.snapshot()
            if "bomba" in snap:       stat.bomba = bool(snap["bomba"])
            if "ventilador" in snap:  stat.ventilador = bool(snap["ventilador"])
            if "luz" in snap:         stat.luz = bool(snap["luz"])
            stat = guardar(db, stat)
        except Exception as e:
            print("[ESP32] snapshot falló:", e)
            # devolvemos lo que tengamos en db

    return stat

def set_mecanismo(
    db: Session,
    bomba: Optional[bool] = None,
    luz: Optional[bool] = None,
    ventilador: Optional[bool] = None,
) -> Mecanismos:
    cx = _get_esp32_connection()
    if cx is not None:
        try:
            if bomba is not None:      cx.set_bomba(bool(bomba))
            if ventilador is not None: cx.set_ventilador(bool(ventilador))
            if luz is not None:        cx.set_luz(bool(luz))
        except Exception as e:
            print("[ESP32] set_mecanismo fallo", e)

    mech = db.query(Mecanismos).first()
    if not mech:
        mech = Mecanismos()

    if bomba is not None:      mech.bomba = bool(bomba)
    if luz is not None:        mech.luz = bool(luz)
    if ventilador is not None: mech.ventilador = bool(ventilador)

    return guardar(db, mech)

# ----------------- lecturas
def agregar_lectura(
    temperatura: float,
    humedad: float,
    humedad_suelo: float,
    nivel_de_agua: float,
) -> Lectura:
    """Maneja su propia sesión porque es llamada desde un hilo secundario (ESP32)."""
    db = SessionLocal()
    try:
        obj = Lectura(
            temperatura=temperatura,
            humedad=humedad,
            humedad_suelo=humedad_suelo,
            nivel_de_agua=nivel_de_agua, 
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def ultima_lectura(db: Session) -> Optional[Lectura]:
    """devuelve la última lectura registrada (recibe 'db' de FastAPI)."""
    lecturas = select(Lectura).order_by(desc(Lectura.fecha_hora)).limit(1)
    return db.execute(lecturas).scalars().first()

def ultimas_lecturas_7d(db: Session) -> List[Lectura]:
    "devuelve todas las lecturas dentro de los últimos 7 días (orden desc)"
    # Esta función recibe 'db' de FastAPI y lo usa directamente.
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(Lectura)
        .where(Lectura.fecha_hora >= cutoff)
        .order_by(desc(Lectura.fecha_hora))
    )
    return db.execute(stmt).scalars().all()

def csv_from(days: int) -> str:
    """Genera un CSV de lecturas. Abre su propia sesión ya que no es un endpoint estándar de CRUD."""
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=days)

    db = SessionLocal() # Usa SessionLocal ya que no depende de FastAPI Depends
    try:
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
    finally:
        db.close()
        
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