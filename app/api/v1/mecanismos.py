from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import asyncio

from app.api.deps import get_db, resolve_esp_id
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.db.models import Mecanismos, Device
from app.servicios.funciones import set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

def _get_status_pure_db(db: Session, esp_id: str) -> Mecanismos:
    device = db.query(Device).filter(Device.esp_id == esp_id).first()
    if not device:
         raise HTTPException(status_code=404, detail=f"Device con esp_id {esp_id} no encontrado")

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == device.id).first()
    
    if not mech:
         raise HTTPException(status_code=404, detail=f"Mecanismos no encontrados para el device_id {device.id}")
    
    return mech

@router.get("", response_model=MecanismosOut)
def get_stat(esp_id: str = Depends(resolve_esp_id), db: Session = Depends(get_db)):
    """Obtiene el estado actual de los mecanismos (leído desde la DB)."""
    return _get_status_pure_db(db, esp_id)

@router.put("", response_model=MecanismosOut)
async def put_mech(payload: MecanismosIn, db: Session = Depends(get_db)): 
    """
    Establece el estado de uno o más mecanismos.
    Envía comandos SET por MQTT y persiste el estado en la DB.
    """
    cambios = payload.model_dump(exclude_none=True)
    
    esp_id = resolve_esp_id(db=db, esp_id=cambios.pop("esp_id", None))

    mech_intermedio = set_mecanismo(db, esp_id, **cambios)

    if getattr(mech_intermedio, "_serial_ok", True) is False:
        raise HTTPException(status_code=503, detail="ESP32 no disponible (serial/MQTT no disponible)")

    db.commit()

    await asyncio.sleep(1.0) 
    
    db.expire_all()
    
    mech_final = _get_status_pure_db(db, esp_id) 

    return mech_final
