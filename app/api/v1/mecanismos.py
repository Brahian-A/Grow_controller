from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db
from app.db.models import Dispositivo
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.servicios.funciones import get_status, set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

def _resolve_esp_id(db: Session, esp_id: Optional[str]) -> str:
    import os
    if esp_id: return esp_id
    env_uid = os.getenv("DEFAULT_ESP_ID")
    if env_uid: return env_uid
    cnt = db.query(Dispositivo).count()
    if cnt == 0:
        from app.db.models import Mecanismos, Config, Dispositivo
        d = Dispositivo(esp_id="default-esp")
        db.add(d); db.commit(); db.refresh(d)
        db.add(Mecanismos(device_id=d.id)); db.add(Config(device_id=d.id)); db.commit()
        return d.esp_id
    if cnt == 1:
        return db.query(Dispositivo).first().esp_id
    raise HTTPException(status_code=422, detail="Falta esp_id y hay múltiples dispositivos. Pasa ?esp_id=...")

@router.get("", response_model=MecanismosOut)
def get_stat(esp_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    esp_id = _resolve_esp_id(db, esp_id)
    return get_status(db, esp_id)

@router.put("", response_model=MecanismosOut)
def put_mech(payload: MecanismosIn, db: Session = Depends(get_db)):
    cambios = payload.model_dump(exclude_none=True)
    esp_id = _resolve_esp_id(db, cambios.pop("esp_id", None))
    return set_mecanismo(db, esp_id, **cambios)
