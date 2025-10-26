from fastapi import Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.db.session import SessionLocal
from app.db.models import Device, Mecanismos, Config

# ---- Sesión
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- Resolver esp_id centralizado
def resolve_esp_id(
    db: Session = Depends(get_db),
    esp_id: Optional[str] = Query(None)
) -> str:
    if esp_id:
        return esp_id

    env_uid = os.getenv("DEFAULT_ESP_ID")
    if env_uid:
        return env_uid

    count = db.query(Device).count()

    if count == 0:
        d = Device(esp_id="default-esp")
        db.add(d); db.commit(); db.refresh(d)
        db.add(Mecanismos(device_id=d.id))
        db.add(Config(device_id=d.id))
        db.commit()
        return d.esp_id

    if count == 1:
        return db.query(Device).first().esp_id

    raise HTTPException(
        status_code=422,
        detail="Falta esp_id y hay múltiples dispositivos. Pasa ?esp_id=..."
    )
