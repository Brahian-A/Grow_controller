from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db

from app.schemas.config import ConfigIn, ConfigOut
from app.servicios.funciones import get_config, set_config

router = APIRouter(prefix="/config", tags=["config"])

@router.get("", response_model=ConfigOut)
def get_cfg(db: Session = Depends(get_db)):
    "return current configuration thresholds"
    try:
        return get_config(db)
    except Exception as e:
        print(f"[ERROR] No se pudo obtener configuración: {e}")
        raise HTTPException(status_code=500, detail="No se pudo obtener la configuración")

@router.put("", response_model=ConfigOut)
def put_cfg(payload: ConfigIn, db: Session = Depends(get_db)):
    "modify one or more configuration thresholds"
    data = payload.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un campo para modificar")

    try:
        return set_config(db, **data)
    except Exception as e:
        print(f"[ERROR] No se pudo actualizar configuración: {e}")
        raise HTTPException(status_code=500, detail="No se pudo actualizar la configuración")
