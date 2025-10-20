from fastapi import APIRouter, HTTPException, Query
from app.conexiones.conexion_esp32 import get_snapshot, enviar_cmd

router = APIRouter(prefix="/system", tags=["Sistema"])

@router.get("/snapshot")
def snapshot(esp_id: str | None = Query(None)):
    "return a live snapshot of ESP32 state and last data received (optionally by esp_id)"
    try:
        return get_snapshot(esp_id) if esp_id is not None else get_snapshot()
    except TypeError:
        return get_snapshot()

@router.post("/mecanismos/{target}/{value}")
def set_mecanismo(
    target: str,
    value: str,
    esp_id: str | None = Query(None)
):
    "send a SET command to the ESP32 for RIEGO/VENT/LUZ with ON/OFF (optionally by esp_id)"
    target = target.upper()
    value = value.upper()
    if target not in ("RIEGO", "VENT", "LUZ") or value not in ("ON", "OFF"):
        raise HTTPException(status_code=400, detail="target/value inválidos")
    cmd = {"cmd": "SET", "target": target, "value": value}
    if esp_id: cmd["esp_id"] = esp_id
    enviar_cmd(cmd)
    return {"ok": True}

@router.post("/status")
def pedir_status(esp_id: str | None = Query(None)):
    "request a STATUS update from the ESP32 (optionally by esp_id)"
    cmd = {"cmd": "STATUS"}
    if esp_id: cmd["esp_id"] = esp_id
    enviar_cmd(cmd)
    return {"ok": True}
