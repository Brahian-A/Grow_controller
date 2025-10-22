from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import io, csv

from app.conexiones.conexion_esp32 import get_snapshot, enviar_cmd
from app.db.session import SessionLocal
from app.db.models import Dispositivo, Lectura, Mecanismos, Config

def guardar(db: Session, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_or_create_device(db: Session, esp_id: str, nombre: Optional[str] = None) -> Dispositivo:
    d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
    if not d:
        d = Dispositivo(esp_id=esp_id, nombre=nombre)
        db.add(d); db.commit(); db.refresh(d)
        db.add(Mecanismos(device_id=d.id))
        db.add(Config(device_id=d.id))
        db.commit(); db.refresh(d)
    return d

# ----------------- configuración (por dispositivo)

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
    if humedad_suelo is not None:    cfg.humedad_suelo = humedad_suelo
    if temperatura is not None:      cfg.temperatura = temperatura
    if humedad_ambiente is not None: cfg.humedad_ambiente = humedad_ambiente
    if margen is not None:           cfg.margen = margen
    return guardar(db, cfg)

# ----------------- mecanismos (usa snapshot global)

def get_status(db: Session, esp_id: str) -> Mecanismos:
    d = get_or_create_device(db, esp_id)
    stat = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first() or Mecanismos(device_id=d.id)
    snap = get_snapshot()
    stat.bomba = bool(snap.get("riego"))
    stat.ventilador = bool(snap.get("vent"))
    stat.luz = bool(snap.get("luz"))
    return guardar(db, stat)

def set_mecanismo(db: Session, esp_id: str, bomba=None, luz=None, ventilador=None) -> Mecanismos:
    d = get_or_create_device(db, esp_id)

    serial_ok = True
    # Intentar enviar a la ESP pero no fallar si no hay puerto
    if bomba is not None:
        serial_ok = enviar_cmd({"cmd":"SET","target":"RIEGO","value":"ON" if bomba else "OFF"}) and serial_ok
    if ventilador is not None:
        serial_ok = enviar_cmd({"cmd":"SET","target":"VENT","value":"ON" if ventilador else "OFF"}) and serial_ok
    if luz is not None:
        serial_ok = enviar_cmd({"cmd":"SET","target":"LUZ","value":"ON" if luz else "OFF"}) and serial_ok

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first() or Mecanismos(device_id=d.id)
    if bomba is not None:      mech.bomba = bool(bomba)
    if luz is not None:        mech.luz = bool(luz)
    if ventilador is not None: mech.ventilador = bool(ventilador)

    mech = guardar(db, mech)

    mech._warning = None if serial_ok else "serial_unavailable"
    return mech


# ----------------- lecturas (por dispositivo)

def agregar_lectura(esp_id: str, temperatura: float, humedad: float, humedad_suelo: float, nivel_de_agua: float) -> Lectura:
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
        writer.writerow([dt_local, f"{temperatura:.1f} °C", f"{humedad_suelo:.1f} %", f"{humedad:.1f} %"])
    return buf.getvalue()

# ----------------- Gemini

import json
import logging
import google.generativeai as genai
from app.core.config import config

# Configura el modelo una sola vez al cargar el módulo
try:
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    logging.error(f"Error al configurar Gemini: {e}")
    model = None

def get_plant_conditions(plant_name: str) -> dict:
    """
    Consulta a Gemini las condiciones óptimas para una planta y devuelve un dict.
    """
    if not model:
        raise ConnectionError("El modelo de Gemini no está disponible.")

    prompt = f"""
    Para la planta llamada "{plant_name}", genera sus condiciones óptimas de crecimiento.
    Devuelve EXCLUSIVAMENTE un objeto JSON con las siguientes tres claves:
    - "temperatura": el valor numérico óptimo en grados Celsius.
    - "humedad_tierra": el valor numérico del porcentaje de humedad óptima en la tierra.
    - "humedad_ambiente": el valor numérico del porcentaje de humedad óptima en el ambiente.

    No agregues ninguna explicación, texto introductorio, ni la palabra "json".
    Tu respuesta debe ser únicamente el objeto JSON.
    """

    try:
        response = model.generate_content(prompt)
        
        # Limpiamos la respuesta de la IA
        clean_response = response.text.strip()
        
        # Quitamos el formato Markdown si existe
        if clean_response.startswith("```json"):
            clean_response = clean_response.replace("```json", "", 1).strip()
        if clean_response.endswith("```"):
            clean_response = clean_response.rsplit("```", 1)[0].strip()

        # Parseamos el JSON
        data = json.loads(clean_response)
        return data

    except json.JSONDecodeError:
        logging.error(f"Respuesta de Gemini no es un JSON válido para '{plant_name}': {response.text}")
        raise ValueError("La respuesta de la IA no pudo ser procesada como JSON.")
    except Exception as e:
        logging.error(f"Error en la llamada a Gemini para '{plant_name}': {e}")
        raise ConnectionError(f"Ocurrió un error al contactar el servicio de IA: {e}")