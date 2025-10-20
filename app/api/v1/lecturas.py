from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from fastapi.responses import StreamingResponse
from datetime import datetime
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Dispositivo, Mecanismos, Config
from app.schemas.lecturas import LecturaIn, LecturaOut
from app.servicios.funciones import (
    agregar_lectura, ultima_lectura, ultimas_lecturas_7d, csv_from
)

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

def _resolve_esp_id(db: Session, esp_id: Optional[str]) -> str:
    import os
    if esp_id:
        return esp_id
    env_uid = os.getenv("DEFAULT_ESP_ID")
    if env_uid:
        return env_uid
    count = db.query(Dispositivo).count()
    if count == 0:
        d = Dispositivo(esp_id="default-esp")
        db.add(d); db.commit(); db.refresh(d)
        db.add(Mecanismos(device_id=d.id)); db.add(Config(device_id=d.id)); db.commit()
        return d.esp_id
    if count == 1:
        return db.query(Dispositivo).first().esp_id
    raise HTTPException(
        status_code=422,
        detail="Falta esp_id y hay múltiples dispositivos. Pasa ?esp_id=..."
    )

@router.post("", response_model=LecturaOut, status_code=201)
def post_lectura(payload: LecturaIn, db: Session = Depends(get_db)) -> LecturaOut:
    "receive and store a new reading coming from the sensor"
    try:
        return agregar_lectura(**payload.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar Lectura: {e}")

@router.get("/ultima", response_model=LecturaOut | None)
def get_ultima(
    esp_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> LecturaOut | None:
    "return the last recorded reading (for a given esp_id)"
    try:
        esp_id = _resolve_esp_id(db, esp_id)
        return ultima_lectura(db, esp_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No se pudo encontrar la lectura: {e}")

@router.get("", response_model=List[LecturaOut])
def get_ultimas(
    esp_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> List[LecturaOut]:
    "return all readings within the last 7 days (descending by timestamp) for esp_id"
    esp_id = _resolve_esp_id(db, esp_id)
    return ultimas_lecturas_7d(db, esp_id)

@router.get("/csv")
def get_csv(
    days: int = Query(..., ge=1, le=365),
    esp_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    "generate and download a CSV file with readings from the last N days for esp_id"
    esp_id = _resolve_esp_id(db, esp_id)
    try:
        csv_text = csv_from(esp_id, days)
        filename = f"{esp_id}_ultimos_{days}_dias_{datetime.now().date().isoformat()}.csv"
        return StreamingResponse(
            iter([csv_text]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el CSV: {e}")
