from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone, timedelta, date, time
from zoneinfo import ZoneInfo
import io, csv
import logging
import json

from app.servicios.mqtt_funciones import enviar_cmd_mqtt # Se usa para enviar comandos
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

# ----------------- mecanismos (usa DB/MQTT)

def get_status(db: Session, esp_id: str) -> Mecanismos:
    d = get_or_create_device(db, esp_id)
    # El estado se lee directamente de la DB (actualizado por el listener MQTT).
    stat = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first() or Mecanismos(device_id=d.id)
    # Se eliminó la lógica de snapshot
    return guardar(db, stat)

def set_mecanismo(db: Session, esp_id: str, bomba=None, luz=None, ventilador=None) -> Mecanismos:
    d = get_or_create_device(db, esp_id)

    mqtt_ok = True
    # Envío de comandos SET por MQTT
    if bomba is not None:
        mqtt_ok = enviar_cmd_mqtt({"cmd":"SET","target":"RIEGO","value":"ON" if bomba else "OFF"}, esp_id=esp_id) and mqtt_ok
    if ventilador is not None:
        mqtt_ok = enviar_cmd_mqtt({"cmd":"SET","target":"VENT","value":"ON" if ventilador else "OFF"}, esp_id=esp_id) and mqtt_ok
    if luz is not None:
        mqtt_ok = enviar_cmd_mqtt({"cmd":"SET","target":"LUZ","value":"ON" if luz else "OFF"}, esp_id=esp_id) and mqtt_ok

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first() or Mecanismos(device_id=d.id)
    if bomba is not None:      mech.bomba = bool(bomba)
    if luz is not None:        mech.luz = bool(luz)
    if ventilador is not None: mech.ventilador = bool(ventilador)

    mech = guardar(db, mech)

    # El flag de error se mantiene para compatibilidad con el endpoint /mecanismos
    mech._warning = None if mqtt_ok else "serial_unavailable"
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

def csv_from_range(db: Session, esp_id: str, desde: str, hasta: str) -> str:
    d = db.query(Dispositivo).filter_by(esp_id=esp_id).first()
    if not d:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(["fecha_hora", "temperatura", "humedad_suelo", "humedad"])
        return buf.getvalue()

    tz_local = ZoneInfo("America/Montevideo")
    d0 = datetime.strptime(desde, "%Y-%m-%d").date()
    d1 = datetime.strptime(hasta, "%Y-%m-%d").date()
    if d0 > d1:
        raise ValueError("La fecha 'desde' no puede ser posterior a 'hasta'.")

    start_local = datetime.combine(d0, time.min).replace(tzinfo=tz_local)
    end_local   = datetime.combine(d1, time.max).replace(tzinfo=tz_local)

    start_utc = start_local.astimezone(timezone.utc)
    end_utc   = end_local.astimezone(timezone.utc)

    stmt = (
        select(
            Lectura.fecha_hora,
            Lectura.temperatura,
            Lectura.humedad_suelo,
            Lectura.humedad,
        )
        .where(
            Lectura.device_id == d.id,
            Lectura.fecha_hora >= start_utc,
            Lectura.fecha_hora <= end_utc,
        )
        .order_by(desc(Lectura.fecha_hora))
    )
    rows = db.execute(stmt).all()

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["fecha_hora", "temperatura", "humedad_suelo", "humedad"])

    for dt, temperatura, humedad_suelo, humedad in rows:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(tz_local).strftime("%Y-%m-%d %H:%M:%S")

        temp_str = f"{float(temperatura):.1f} °C"
        soil_str = f"{float(humedad_suelo):.1f} %"
        hum_str  = f"{float(humedad):.1f} %"

        writer.writerow([dt_local, temp_str, soil_str, hum_str])

    return buf.getvalue()

# ----------------- Gemini

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