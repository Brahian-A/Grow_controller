import json
import math
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.db.models import Lectura, Device, Mecanismos
from app.servicios.mqtt_funciones import setup_mqtt_client
from app.servicios.devices import get_or_create_device
from app.servicios.autocontrol import procesar_umbrales

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("mqtt-listener")

MQTT_BASE_TOPIC = "invernaderos/+/telemetria"
MQTT_STATUS_TOPIC = "invernaderos/+/status"


def _update_mecanismos_from_telemetria(db: Session, esp_id: str, data: dict):
    """Persiste el estado REAL de los mecanismos reportado por el ESP32 en la DB."""
    d = db.query(Device).filter(Device.esp_id == esp_id).first()
    if not d:
        log.warning("DISPOSITIVO no encontrado para actualizar mecanismos: %s", esp_id)
        return

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first()
    if not mech:
        mech = Mecanismos(device_id=d.id)
        db.add(mech)

    new_bomba = (str(data.get("riego")).upper() == "ON")
    new_vent = (str(data.get("vent")).upper() == "ON")
    new_luz = (str(data.get("luz")).upper() == "ON")

    if mech.bomba != new_bomba or mech.ventilador != new_vent or mech.luz != new_luz:
        log.info("SINCRONIZANDO estado de Mecanismos para %s.", esp_id)
        mech.bomba = new_bomba
        mech.ventilador = new_vent
        mech.luz = new_luz

def _is_num(x):
    """Verifica si el valor es un número válido."""
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode(errors="ignore").strip()
        parts = msg.topic.split("/")
        esp_id = parts[1] if len(parts) >= 2 else None
        
        if not esp_id:
            log.error("No se pudo extraer esp_id del tópico: %s", msg.topic)
            return

        # Inicia la sesión de DB. Se cerrará automáticamente al salir del bloque 'with'.
        with SessionLocal() as db:
            # 1. ACTUALIZAR CONTACTO DEL DISPOSITIVO
            d = get_or_create_device(db, esp_id) 
            d.ultimo_contacto = datetime.now(timezone.utc)
            
            # Si el payload no es JSON, solo guarda el contacto y termina.
            if not payload_str or not payload_str.startswith("{"):
                if parts[-1] == "status":
                    log.info("STATUS (simple) %s: %s", esp_id, payload_str)
                db.commit()
                return

            # 2. PROCESAMIENTO DE JSON
            data = json.loads(payload_str)
            esp_id = data.get("esp_id") or esp_id 

            # A. Actualizar Mecanismos (si los datos vienen en el payload)
            if all(k in data for k in ("riego", "vent", "luz")):
                _update_mecanismos_from_telemetria(db, esp_id, data)

            # B. Guardar Lectura y Ejecutar Autocontrol (Solo para /telemetria)
            if parts[-1] == "telemetria":
                t, h, s, n = data.get("temp_c"), data.get("hum_amb"), data.get("suelo_pct"), data.get("nivel_pct")
                valid_sensores = (_is_num(t) and _is_num(h) and _is_num(s) and _is_num(n))

                if valid_sensores:
                    try:
                        nueva_lectura = Lectura(
                            device_id=d.id,
                            temperatura=float(t),
                            humedad=float(h),
                            humedad_suelo=float(s),
                            nivel_de_agua=float(n),
                            fecha_hora=datetime.now(timezone.utc)
                        )
                        db.add(nueva_lectura)
                        
                        log.info(f"Lectura válida ({t}°C/{s}%). Ejecutando Autocontrol...")
                        
                        procesar_umbrales(db, esp_id, nueva_lectura)

                    except Exception:
                        log.error("CRÍTICO: Fallo al persistir lectura/autocontrol.")
                        log.exception("Detalles del ERROR de DB:")
                else:
                    log.info("Skip lectura %s: Datos de sensor inválidos.", esp_id)
            
            # Commit final de todas las operaciones dentro de la sesión
            db.commit()
            
    except json.JSONDecodeError:
        log.error("JSON INVÁLIDO. Topic: %s", msg.topic)
    except SQLAlchemyError:
        # En caso de error de DB, hace rollback antes de loguear
        if 'db' in locals() and db.is_active:
             db.rollback()
        log.error("FALLO CRÍTICO DE DB. Se realizó ROLLBACK.")
        log.exception("Detalles del error:")
    except Exception as e:
        log.exception("ERROR inesperado en on_message: %s", e)


def _on_connect(client, userdata, flags, rc):
    """Maneja el evento de conexión MQTT."""
    if rc == 0:
        log.info("Conectado a MQTT (rc=0). Suscripción a tópicos...")
        client.subscribe(MQTT_BASE_TOPIC, qos=1)
        client.subscribe(MQTT_STATUS_TOPIC, qos=1)
    else:
        log.warning("Conexión MQTT fallida con rc=%s", rc)


def start_mqtt_listener():
    """Inicializa el cliente MQTT y comienza el loop de escucha."""
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = _on_connect

    setup_mqtt_client(client) # Configuración adicional (si la hay)

    try:
        client.connect("localhost", 1883, keepalive=25)
    except ConnectionRefusedError:
        log.warning("No se pudo conectar a Mosquitto en localhost:1883.")
        return

    client.loop_start()
