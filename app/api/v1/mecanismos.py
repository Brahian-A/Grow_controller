from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import asyncio

from app.api.deps import get_db, resolve_esp_id
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.servicios.funciones import get_status, set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

@router.get("", response_model=MecanismosOut)
def get_stat(esp_id: str = Depends(resolve_esp_id), db: Session = Depends(get_db)):
    """Obtiene el estado actual de los mecanismos (leído desde la DB)."""
    # Esta función sigue siendo síncrona ya que solo lee.
    return get_status(db, esp_id)

@router.put("", response_model=MecanismosOut)
async def put_mech(payload: MecanismosIn, db: Session = Depends(get_db)): 
    """
    Establece el estado de uno o más mecanismos.
    Envía comandos SET por MQTT y espera la confirmación en la DB antes de responder.
    """
    cambios = payload.model_dump(exclude_none=True)
    esp_id = resolve_esp_id(db=db, esp_id=cambios.pop("esp_id", None))

    mech_intermedio = set_mecanismo(db, esp_id, **cambios)

    if getattr(mech_intermedio, "_serial_ok", True) is False:
        raise HTTPException(status_code=503, detail="ESP32 no disponible (serial/MQTT no disponible)")
    
    await asyncio.sleep(0.3) 
    
    mech_final = get_status(db, esp_id) 

    return mech_final