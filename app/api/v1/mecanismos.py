from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, resolve_esp_id
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.servicios.funciones import get_status, set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

@router.get("", response_model=MecanismosOut)
def get_stat(esp_id: str = Depends(resolve_esp_id), db: Session = Depends(get_db)):
    """Obtiene el estado actual de los mecanismos (leído desde la DB)."""
    return get_status(db, esp_id)

@router.put("", response_model=MecanismosOut)
def put_mech(payload: MecanismosIn, db: Session = Depends(get_db)):
    """
    Establece el estado de uno o más mecanismos.
    Envía comandos SET por MQTT y persiste el estado en la DB.
    """
    cambios = payload.model_dump(exclude_none=True)
    
    # 1. Resuelve el esp_id (desde query, env o default)
    esp_id = resolve_esp_id(db=db, esp_id=cambios.pop("esp_id", None))

    # 2. Intenta enviar por MQTT y actualiza la DB
    mech = set_mecanismo(db, esp_id, **cambios)

    # 3. Verifica si el comando MQTT se pudo enviar (usando el flag _serial_ok)
    if getattr(mech, "_serial_ok", True) is False:
        # Esto atrapa el error de enviar_cmd_mqtt si el broker no está disponible.
        raise HTTPException(status_code=503, detail="ESP32 no disponible (serial/MQTT no disponible)")

    return mech