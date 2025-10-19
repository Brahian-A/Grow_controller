from fastapi import APIRouter, HTTPException
from app.conexiones.conexion_esp32 import get_snapshot, enviar_cmd

router = APIRouter(prefix="/system", tags=["Sistema"])

@router.get("/snapshot")
def snapshot():
    return get_snapshot()

@router.post("/mecanismos/{target}/{value}")
def set_mecanismo(target: str, value: str):
    target = target.upper()
    value = value.upper()
    if target not in ("RIEGO", "VENT", "LUZ") or value not in ("ON", "OFF"):
        raise HTTPException(status_code=400, detail="target/value inválidos")
    enviar_cmd({"cmd": "SET", "target": target, "value": value})
    return {"ok": True}

@router.post("/status")
def pedir_status():
    enviar_cmd({"cmd": "STATUS"})
    return {"ok": True}
