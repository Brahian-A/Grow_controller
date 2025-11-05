import json
import math
import logging
from datetime import datetime, timezone
from typing import Optional # No usado, pero mantenido si se usa en otros helpers

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.db.models import Lectura, Device, Mecanismos
from app.servicios.mqtt_funciones import setup_mqtt_client
from app.servicios.devices import get_or_create_device
from app.servicios.umbrales import procesar_umbrales

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("mqtt-listener")

MQTT_BASE_TOPIC = "invernaderos/+/telemetria"
MQTT_STATUS_TOPIC = "invernaderos/+/status"


def _update_mecanismos_from_telemetria(db: Session, esp_id: str, data: dict):
    """
    Persiste el estado REAL de los mecanismos reportado por el ESP32 en la DB
    usando la sesión de DB existente.
    """
    d = db.query(Device).filter(Device.esp_id == esp_id).first()
    if not d:
        log.warning("DISPOSITIVO no encontrado para actualizar mecanismos: %s", esp_id)
        return

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == d.id).first()
    if not mech:
        log.info("CREANDO registro Mecanismos para %s", esp_id)
        mech = Mecanismos(device_id=d.id)
        db.add(mech)
        # No hacemos commit aquí, se hará al final de on_message

    new_bomba = (str(data.get("riego")).upper() == "ON")
    new_vent = (str(data.get("vent")).upper() == "ON")
    new_luz = (str(data.get("luz")).upper() == "ON")

    if mech.bomba == new_bomba and mech.ventilador == new_vent and mech.luz == new_luz:
        log.debug("Mecanismos de %s sin cambios", esp_id)
        return
        
    log.info("SINCRONIZANDO estado de Mecanismos para %s. B:%s -> %s", 
              esp_id, mech.bomba, new_bomba)

    mech.bomba = new_bomba
    mech.ventilador = new_vent
    mech.luz = new_luz
    # No hacemos commit, se propaga al commit final

def _is_num(x):
    """Verifica si el valor es un número válido (no NaN)."""
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode(errors="ignore").strip()
        parts = msg.topic.split("/")
        
        esp_id = parts[1] if len(parts) >= 2 else None
        if not esp_id:
            log.error("No se pudo extraer esp_id del tópico: %s", msg.topic)
            return

        # ============================================================
        # 1. MANEJO DE SESIÓN DB y CONTACTO
        # Se usa una única sesión para todo el procesamiento
        # ============================================================
        with SessionLocal() as db:
            # Obtener/Crear Dispositivo (d) y actualizar el contacto
            d = get_or_create_device(db, esp_id) 
            d.ultimo_contacto = datetime.now(timezone.utc)
            # El objeto 'd' ahora tiene el ID necesario para las lecturas
            
            # Si no es un JSON (ej. "online", "offline")
            if not payload_str or not payload_str.startswith("{"):
                if parts[-1] == "status":
                    log.info("STATUS (simple) %s: %s", esp_id, payload_str)
                else:
                    log.warning("Payload no-JSON ignorado. Topic: %s", msg.topic)
                db.commit() # Solo commitamos el ultimo_contacto
                return

            # ============================================================
            # 2. PROCESAMIENTO DE JSON
            # ============================================================
            data = json.loads(payload_str)
            # Re-extraemos esp_id por si viene en el payload
            esp_id = data.get("esp_id") or esp_id 

            # A. Actualizar Mecanismos (si el payload los trae)
            has_actuator_data = all(k in data for k in ("riego", "vent", "luz"))
            if has_actuator_data:
                log.info("Actualizando mecanismos desde Topic: %s", parts[-1])
                _update_mecanismos_from_telemetria(db, esp_id, data)

            # B. Guardar Lectura y Ejecutar Autocontrol (Solo si es /telemetria)
            if parts[-1] == "telemetria":
                t = data.get("temp_c")
                h = data.get("hum_amb")
                s = data.get("suelo_pct")
                n = data.get("nivel_pct")

                valid_sensores = (_is_num(t) and _is_num(h) and _is_num(s) and _is_num(n))
                nueva_lectura = None

                if valid_sensores:
                    try:
                        # ----------------------------------------------------
                        # ESTA ES LA LÓGICA REEMPLAZADA DE _save_lectura
                        # ----------------------------------------------------
                        nueva_lectura = Lectura(
                            device_id=d.id, # Reutilizamos el ID del dispositivo 'd'
                            temperatura=float(t),
                            humedad=float(h),
                            humedad_suelo=float(s),
                            nivel_de_agua=float(n),
                            timestamp=datetime.now(timezone.utc)
                        )
                        db.add(nueva_lectura)
                        # ----------------------------------------------------

                        log.info("Lectura guardada. Ejecutando Autocontrol...")
                        
                        # --- LLAMADA CRÍTICA AL AUTOCONTROL ---
                        # Se pasa la sesión activa y el objeto Lectura recién creado.
                        procesar_umbrales(db, esp_id, nueva_lectura)

                    except Exception as db_err:
                        log.error("CRÍTICO: Fallo al persistir lectura/autocontrol.")
                        log.exception("Detalles del ERROR de DB:")
                        # Si hay un error aquí, el commit fallará y se hará rollback más abajo
                else:
                    log.info("Skip lectura %s: Datos de sensor inválidos.", esp_id)
            
            # Commit final de todas las operaciones (contacto, mecanismos, lectura, autocontrol)
            db.commit()
            log.debug("Commit de sesión completado.")
            
    except json.JSONDecodeError:
        log.error("JSON INVÁLIDO. Topic: %s, Payload: %s", msg.topic, payload_str[:200])
    except SQLAlchemyError:
        # En caso de error de DB, hacemos rollback y logueamos
        if 'db' in locals() and db.is_active:
             db.rollback()
        log.error("FALLO CRÍTICO DE DB. Se realizó ROLLBACK.")
        log.exception("Detalles del error:")
    except Exception as e:
        log.exception("ERROR inesperado en on_message: %s", e)


def _on_connect(client, userdata, flags, rc):
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

    setup_mqtt_client(client)

    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.max_inflight_messages_set(20)

    try:
        client.connect("localhost", 1883, keepalive=25)
    except ConnectionRefusedError:
        log.warning("No se pudo conectar a Mosquitto en localhost:1883. El listener no se iniciará.")
        return

    client.subscribe(MQTT_BASE_TOPIC, qos=1)
    log.info("Suscrito a: %s (QoS 1)", MQTT_BASE_TOPIC)

    client.subscribe(MQTT_STATUS_TOPIC, qos=1)
    log.info("Suscrito a: %s (QoS 1)", MQTT_STATUS_TOPIC)

    client.loop_start()
