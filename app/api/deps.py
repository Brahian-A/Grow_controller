from app.db.session import SessionLocal
from fastapi import Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.db.models import Dispositivo  # importa el modelo

# ---------------- sesion

def get_db():
    """FastAPI dependency that yields a database session and ensures it is closed afterward"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------ resuelve la esp id

def resolve_esp_id(
    esp_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> str:
    if esp_id:
        return esp_id

    env_uid = os.getenv("DEFAULT_ESP_ID")
    if env_uid:
        return env_uid

    total = db.query(Dispositivo).count()
    if total == 0:
        raise HTTPException(
            status_code=422,
            detail="No hay dispositivos registrados.",
        )
    if total == 1:
        return db.query(Dispositivo).first().esp_id

    raise HTTPException(
        status_code=422,
        detail="Falta esp_id y hay múltiples dispositivos.",
    )
