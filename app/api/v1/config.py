from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, resolve_esp_id
from app.schemas.config import ConfigIn, ConfigOut
from app.servicios.funciones import get_config, set_config

router = APIRouter(prefix="/config", tags=["config"])

@router.get("", response_model=ConfigOut)
def get_cfg(esp_id: str = Depends(resolve_esp_id), db: Session = Depends(get_db)):
    return get_config(db, esp_id)

@router.put("", response_model=ConfigOut)
def put_cfg(payload: ConfigIn, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    esp_id = data.pop("esp_id", None)
    esp_id = resolve_esp_id(db=db, esp_id=esp_id)
    return set_config(db, esp_id, **data)
