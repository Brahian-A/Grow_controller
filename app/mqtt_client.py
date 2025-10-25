import json
import paho.mqtt.client as mqtt
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Lectura, Dispositivo, Mecanismos
from app.servicios.funciones import agregar_lectura
from app.servicios.mqtt_funciones import setup_mqtt_client # para que el API pueda publicar comandos

# configuracion basica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MQTT_BASE_TOPIC = "invernaderos/+/telemetria"
MQTT_STATUS_TOPIC = "invernaderos/+/status"

def _update_mecanismos_from_telemetria(db: Session, esp_id: str, data: dict):
    """
    persiste el estado real de los mecanismos reportado por el ESP32 directamente en la db
    """
    d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
    if not d:
        logging.warning(f"Dispositivo {esp_id} no encontrado para actualizar mecanismos.")
        return

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first()
    if not mech:
        mech = Mecanismos(device_id=d.id)
        db.add(mech)
    
    # actualización directa del estado real
    mech.bomba = (str(data["riego"]).upper() == "ON")
    mech.ventilador = (str(data["vent"]).upper() == "ON")
    mech.luz = (str(data["luz"]).upper() == "ON")

    db.commit()

def on_message(client, userdata, msg):
    """
    manejo de mensajes MQTT, procesa telemetria y estado
    """
    try:
        payload_str = msg.payload.decode(errors="ignore").strip()
        parts = msg.topic.split('/')
        data = json.loads(payload_str) if payload_str else {}
        esp_id = data.get("esp_id") or (parts[1] if len(parts) >= 2 else None)
        
        if not esp_id:
            logging.error("ERROR: Mensaje sin esp_id en payload o tópico.")
            return

        # online/offline
        if parts[-1] == "status":
            with SessionLocal() as db:
                d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
                if d:
                    d.ultimo_contacto = datetime.now(timezone.utc)
                    db.commit()
            return

        # telemetria (lecturas de sensores + estado de mecanismos)
        if parts[-1] == "telemetria" and all(k in data for k in ("temp_c","hum_amb","suelo_pct","nivel_pct")):
            
            # guarda Lectura de sensores
            agregar_lectura(
                esp_id=esp_id,
                temperatura=data["temp_c"],
                humedad=data["hum_amb"],
                humedad_suelo=data["suelo_pct"],
                nivel_de_agua=data["nivel_pct"],
            )

            # actualiza estado de mecanismos en la db
            if all(k in data for k in ("riego","vent","luz")):
                with SessionLocal() as db:
                    _update_mecanismos_from_telemetria(db, esp_id, data)
            return

    except json.JSONDecodeError:
        logging.error("ERROR: Payload de MQTT no es JSON válido.")
    except Exception as e:
        logging.error(f"ERROR inesperado en on_message: {e}")

def start_mqtt_listener():
    """
    inicializa el cliente MQTT, lo configura para recibir mensajes y comienza el loop
    """
    client = mqtt.Client()
    # almacena el cliente: Esto es clave para que los endpoints puedan publicar comandos.
    setup_mqtt_client(client)
    client.on_message = on_message
    
    # Intenta conectarse al broker
    try:
        client.connect("localhost", 1883)
    except ConnectionRefusedError:
        logging.warning("ADVERTENCIA: No se pudo conectar a Mosquitto en localhost:1883. El listener no se iniciará.")
        return

    client.subscribe(MQTT_BASE_TOPIC)
    logging.info(f"Suscrito a: {MQTT_BASE_TOPIC}")
    
    client.subscribe(MQTT_STATUS_TOPIC)
    logging.info(f"Suscrito a: {MQTT_STATUS_TOPIC}")
    
    client.loop_start()