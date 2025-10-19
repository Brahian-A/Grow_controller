from fastapi import APIRouter, HTTPException
from app.conexiones.conexion_esp32 import get_snapshot, enviar_cmd

router = APIRouter(prefix="/system", tags=["Sistema"])

@router.get("/snapshot")
def snapshot():
    "return a live snapshot of ESP32 state and last data received"
    return get_snapshot()

@router.post("/mecanismos/{target}/{value}")
def set_mecanismo(target: str, value: str):
    "send a SET command to the ESP32 for RIEGO/VENT/LUZ with ON/OFF"
    target = target.upper()
    value = value.upper()
    if target not in ("RIEGO", "VENT", "LUZ") or value not in ("ON", "OFF"):
        raise HTTPException(status_code=400, detail="target/value inválidos")
    enviar_cmd({"cmd": "SET", "target": target, "value": value})
    return {"ok": True}

@router.post("/status")
def pedir_status():
    "request a STATUS update from the ESP32"
    enviar_cmd({"cmd": "STATUS"})
    return {"ok": True}
