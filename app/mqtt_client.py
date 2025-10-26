import json
import math
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Lectura, Dispositivo, Mecanismos
from app.servicios.funciones import agregar_lectura
from app.servicios.mqtt_funciones import setup_mqtt_client 

# configuracion basica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("mqtt-listener")

MQTT_BASE_TOPIC = "invernaderos/+/telemetria"
MQTT_STATUS_TOPIC = "invernaderos/+/status"


def _update_mecanismos_from_telemetria(db: Session, esp_id: str, data: dict):
    """
    Persiste el estado real de los mecanismos reportado por el ESP32 directamente en la DB.
    """
    d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
    if not d:
        log.warning("Dispositivo %s no encontrado para actualizar mecanismos.", esp_id)
        return

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first()
    if not mech:
        mech = Mecanismos(device_id=d.id)
        db.add(mech)

    # Actualización directa del estado real
    mech.bomba = (str(data.get("riego")).upper() == "ON")
    mech.ventilador = (str(data.get("vent")).upper() == "ON")
    mech.luz = (str(data.get("luz")).upper() == "ON")

    db.commit()


def _is_num(x):
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode(errors="ignore").strip()
        data = json.loads(payload_str) if payload_str else {}
        parts = msg.topic.split("/")
        esp_id = data.get("esp_id") or (parts[1] if len(parts) >= 2 else None)
        if not esp_id:
            log.error("Mensaje sin esp_id en payload o tópico. topic=%s payload=%s", msg.topic, payload_str)
            return

        # STATUS online/offline (retained)
        if parts[-1] == "status":
            with SessionLocal() as db:
                d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
                if d:
                    d.ultimo_contacto = datetime.now(timezone.utc)
                    db.commit()
            log.info("STATUS %s: %s", esp_id, payload_str)
            return

        # TELEMETRÍA
        if parts[-1] == "telemetria" and all(k in data for k in ("temp_c", "hum_amb", "suelo_pct", "nivel_pct")):
            t = data.get("temp_c")
            h = data.get("hum_amb")
            s = data.get("suelo_pct")
            n = data.get("nivel_pct")

            # sellar último contacto aunque no guardemos lectura
            with SessionLocal() as db:
                d = db.query(Dispositivo).filter(Dispositivo.esp_id == esp_id).first()
                if d:
                    d.ultimo_contacto = datetime.now(timezone.utc)
                    db.commit()

            # si temp/hum vienen null (o NaN), NO persistir (evita NOT NULL fail)
            if not (_is_num(t) and _is_num(h)):
                log.info("Skip lectura %s: temp/hum inválidos (t=%s, h=%s)", esp_id, t, h)
                # igual podemos reflejar estado de mecanismos si viene en la telemetría
                if all(k in data for k in ("riego", "vent", "luz")):
                    with SessionLocal() as db:
                        _update_mecanismos_from_telemetria(db, esp_id, data)
                return

            # suelo y nivel deben ser números también
            if not (_is_num(s) and _is_num(n)):
                log.info("Skip lectura %s: suelo/nivel inválidos (s=%s, n=%s)", esp_id, s, n)
                if all(k in data for k in ("riego", "vent", "luz")):
                    with SessionLocal() as db:
                        _update_mecanismos_from_telemetria(db, esp_id, data)
                return

            agregar_lectura(
                esp_id=esp_id,
                temperatura=float(t),
                humedad=float(h),
                humedad_suelo=float(s),
                nivel_de_agua=float(n),
            )
            log.info("Lectura guardada para %s", esp_id)

            # Si vienen flags de actuadores, sincronizamos DB con el estado real
            if all(k in data for k in ("riego", "vent", "luz")):
                with SessionLocal() as db:
                    _update_mecanismos_from_telemetria(db, esp_id, data)
            return

        # Otros tópicos que no manejamos
        log.debug("Mensaje ignorado topic=%s payload=%s", msg.topic, payload_str)

    except json.JSONDecodeError:
        log.error("Payload de MQTT no es JSON válido. topic=%s payload=%s", msg.topic, msg.payload[:200])
    except Exception as e:
        log.exception("ERROR inesperado en on_message: %s", e)


def _on_connect(client, userdata, flags, rc):
    # rc == 0 ok. En reconexión, hay que re-suscribirse.
    if rc == 0:
        log.info("Conectado a MQTT (rc=0). Re-suscribiendo...")
        client.subscribe(MQTT_BASE_TOPIC, qos=1)
        client.subscribe(MQTT_STATUS_TOPIC, qos=1)
    else:
        log.warning("Conexión MQTT con rc=%s", rc)


def start_mqtt_listener():
    """
    Inicializa el cliente MQTT, lo configura para recibir mensajes y comienza el loop.
    """
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = _on_connect

    # Registrar cliente global para que los endpoints puedan publicar por MQTT
    setup_mqtt_client(client)

    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.max_inflight_messages_set(20)

    try:
        client.connect("localhost", 1883, keepalive=25)
    except ConnectionRefusedError:
        log.warning("No se pudo conectar a Mosquitto en localhost:1883. El listener no se iniciará.")
        return

    # Primera suscripción (por si el on_connect no dispara por algún motivo)
    client.subscribe(MQTT_BASE_TOPIC, qos=1)
    log.info("Suscrito a: %s (QoS 1)", MQTT_BASE_TOPIC)

    client.subscribe(MQTT_STATUS_TOPIC, qos=1)
    log.info("Suscrito a: %s (QoS 1)", MQTT_STATUS_TOPIC)

    client.loop_start()
