from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import resolve_esp_id
from app.servicios.mqtt_funciones import enviar_cmd_mqtt

router = APIRouter(prefix="/system", tags=["system"])

@router.put("/mecanismos/{target}/{value}")
def set_mechanism_direct(
    target: str,
    value: str,
    esp_id: str = Depends(resolve_esp_id)
):
    """
    Establece el estado de un mecanismo directamente (e.g., /system/mecanismos/LUZ/ON).
    """
    target = target.upper()
    value = value.upper()

    if target not in ["RIEGO", "VENT", "LUZ"]:
        raise HTTPException(status_code=400, detail="Target inválido.")

    if value not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Value inválido (debe ser ON o OFF).")

    cmd = {"cmd": "SET", "target": target, "value": value}
    
    if not enviar_cmd_mqtt(cmd, esp_id=esp_id):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ESP32 no disponible (MQTT no pudo publicar el comando)")
    
    return {"message": f"Comando SET {target}={value} enviado a {esp_id} por MQTT."}

@router.post("/status")
def request_status_update(esp_id: str = Depends(resolve_esp_id)):
    """
    Solicita al ESP32 que envíe su estado (telemetría) inmediatamente.
    """
    cmd = {"cmd": "STATUS"}
    if not enviar_cmd_mqtt(cmd, esp_id=esp_id):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ESP32 no disponible (MQTT no pudo publicar el comando)")
    
    return {"message": f"Comando STATUS enviado a {esp_id} por MQTT. Esperando telemetría..."}

@router.post("/reboot")
def reboot_esp32(esp_id: str = Depends(resolve_esp_id)):
    """
    Envía el comando de reinicio al ESP32.
    """
    cmd = {"cmd": "REBOOT"}
    if not enviar_cmd_mqtt(cmd, esp_id=esp_id):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ESP32 no disponible (MQTT no pudo publicar el comando)")
    
    return {"message": f"Comando REBOOT enviado a {esp_id} por MQTT."}