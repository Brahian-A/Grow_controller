from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import io, csv

from app.db.session import SessionLocal
from app.db.models import Dispositivo, Lectura, Mecanismos, Config

# ----------------- util db

def guardar(db: Session, obj):
    "agrega un objeto y hace commit"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# ----------------- helper: resolver o crear dispositivo

def get_or_create_device(db: Session, esp_id: str, nombre: Optional[str] = None) -> Dispositivo:
    d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
    if not d:
        d = Dispositivo(esp_id=esp_id, nombre=nombre)
        db.add(d); db.commit(); db.refresh(d)
        db.add(Mecanismos(device_id=d.id))
        db.add(Config(device_id=d.id))
        db.commit(); db.refresh(d)
    return d

# ----------------- helper ESP32 (opcional)

def _get_esp32_connection():
    "Intenta importar y obtener la conexión a la ESP32 sólo cuando se necesite"
    try:
        from app.conexiones.conexion_esp32 import obtener_conexion
    except Exception as e:
        print("[ESP32] módulo no disponible:", e)
        return None
    try:
        return obtener_conexion()
    except Exception as e:
        print("[ESP32] no se pudo abrir conexión:", e)
        return None

# ----------------- configuración (ahora por dispositivo)

def get_config(db: Session, esp_id: str) -> Config:
    d = get_or_create_device(db, esp_id)
    cfg = db.query(Config).filter(Config.device_id == d.id).first()
    if not cfg:
        cfg = guardar(db, Config(device_id=d.id))
    return cfg

def set_config(
    db: Session,
    esp_id: str,
    humedad_suelo: Optional[int] = None,
    temperatura: Optional[int] = None,
    humedad_ambiente: Optional[int] = None,
    margen: Optional[int] = None
) -> Config:
    cfg = get_config(db, esp_id)
    if humedad_suelo is not None:
        cfg.humedad_suelo = humedad_suelo
    if temperatura is not None:
        cfg.temperatura = temperatura
    if humedad_ambiente is not None:
        cfg.humedad_ambiente = humedad_ambiente
    if margen is not None:
        cfg.margen = margen
    return guardar(db, cfg)

# ----------------- mecanismos (snapshot por dispositivo)

def get_status(db: Session, esp_id: str) -> Mecanismos:
    d = get_or_create_device(db, esp_id)
    stat = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first()
    if not stat:
        stat = guardar(db, Mecanismos(device_id=d.id))

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
    return stat

def set_mecanismo(
    db: Session,
    esp_id: str,
    bomba: Optional[bool] = None,
    luz: Optional[bool] = None,
    ventilador: Optional[bool] = None,
) -> Mecanismos:
    d = get_or_create_device(db, esp_id)

    cx = _get_esp32_connection()
    if cx is not None:
        try:
            if bomba is not None:      cx.set_bomba(bool(bomba))
            if ventilador is not None: cx.set_ventilador(bool(ventilador))
            if luz is not None:        cx.set_luz(bool(luz))
        except Exception as e:
            print("[ESP32] set_mecanismo falló:", e)

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first()
    if not mech:
        mech = Mecanismos(device_id=d.id)

    if bomba is not None:      mech.bomba = bool(bomba)
    if luz is not None:        mech.luz = bool(luz)
    if ventilador is not None: mech.ventilador = bool(ventilador)

    return guardar(db, mech)

# ----------------- lecturas (por dispositivo)

def agregar_lectura(
    esp_id: str,
    temperatura: float,
    humedad: float,
    humedad_suelo: float,
    nivel_de_agua: float,
) -> Lectura:
    """
    Inserta lectura para un dispositivo. Maneja su propia sesión
    porque suele ser llamada desde un hilo secundario (puente ESP32).
    """
    db = SessionLocal()
    try:
        d = get_or_create_device(db, esp_id)
        obj = Lectura(
            device_id=d.id,
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

def ultima_lectura(db: Session, esp_id: str) -> Optional[Lectura]:
    d = db.query(Dispositivo).filter_by(esp_id=esp_id).first()
    if not d:
        return None
    stmt = (
        select(Lectura)
        .where(Lectura.device_id == d.id)
        .order_by(desc(Lectura.fecha_hora))
        .limit(1)
    )
    return db.execute(stmt).scalars().first()

def ultimas_lecturas_7d(db: Session, esp_id: str) -> List[Lectura]:
    "devuelve todas las lecturas dentro de los últimos 7 días (orden desc) para una ESP32"
    d = db.query(Dispositivo).filter_by(esp_id=esp_id).first()
    if not d:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(Lectura)
        .where(Lectura.device_id == d.id, Lectura.fecha_hora >= cutoff)
        .order_by(desc(Lectura.fecha_hora))
    )
    return db.execute(stmt).scalars().all()

def csv_from(esp_id: str, days: int) -> str:
    """
    Genera un CSV de lecturas para un dispositivo.
    Abre su propia sesión ya que no es un endpoint estándar de CRUD.
    """
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=days)

    db = SessionLocal()
    try:
        d = db.query(Dispositivo).filter_by(esp_id=esp_id).first()
        if not d:
            rows = []
        else:
            stmt = (
                select(
                    Lectura.fecha_hora,
                    Lectura.temperatura,
                    Lectura.humedad_suelo,
                    Lectura.humedad,
                )
                .where(
                    Lectura.device_id == d.id,
                    Lectura.fecha_hora >= cutoff,
                    Lectura.fecha_hora <= now_utc,
                )
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
        dt_local = dt.astimezone(tz).isoformat()

        temp = f"{temperatura:.1f} °C"
        hum_suelo = f"{humedad_suelo:.1f} %"
        hum = f"{humedad:.1f} %"

        writer.writerow([dt_local, temp, hum_suelo, hum])

    return buf.getvalue()
