import paho.mqtt.client as mqtt
import logging
import json
from typing import Optional

# topico base para comandos
CMD_TOPIC_BASE = "invernaderos/{esp_id}/cmd"

# asume un ID por defecto para comandos si no se especifica.
DEFAULT_ESP_ID = "main" 

# almacenamiento global del cliente
_mqtt_client = None

def setup_mqtt_client(client: mqtt.Client):
    global _mqtt_client
    _mqtt_client = client

def get_mqtt_client() -> Optional[mqtt.Client]:
    return _mqtt_client

def _resolve_default_esp_id() -> Optional[str]:
    return DEFAULT_ESP_ID

def enviar_cmd_mqtt(cmd: dict, esp_id: Optional[str] = None) -> bool:
    """
    publica un comando JSON al topico CMD específico del dispositivo
    """
    client = get_mqtt_client()
    if not client or not client.is_connected():
        logging.warning("enviar_cmd_mqtt: Cliente MQTT no conectado.")
        return False
        
    final_esp_id = esp_id
    if not final_esp_id:
        final_esp_id = _resolve_default_esp_id()
        
    if not final_esp_id:
        logging.error("enviar_cmd_mqtt: No se pudo resolver un esp_id para enviar el comando.")
        return False

    topic = CMD_TOPIC_BASE.format(esp_id=final_esp_id)
    payload = json.dumps(cmd)
    
    try:
        result = client.publish(topic, payload, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logging.error(f"Fallo al publicar MQTT (rc: {result.rc}) a {topic}")
            return False
        return True
    except Exception as e:
        logging.error(f"Excepción al publicar MQTT: {e}")
        return False