from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List
from fastapi.responses import StreamingResponse
from datetime import datetime
from sqlalchemy.orm import Session

from app.api.deps import get_db, resolve_esp_id
from app.schemas.lecturas import LecturaIn, LecturaOut
from app.servicios.funciones import (
    agregar_lectura, ultima_lectura, ultimas_lecturas_7d, csv_from_range
)

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

@router.post("", response_model=LecturaOut, status_code=201)
def post_lectura(payload: LecturaIn, db: Session = Depends(get_db)) -> LecturaOut:
    """Recibe y guarda una nueva lectura proveniente del sensor."""
    try:
        return agregar_lectura(**payload.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar Lectura: {e}")

@router.get("/ultima", response_model=LecturaOut | None)
def get_ultima(esp_id: str = Depends(resolve_esp_id), db: Session = Depends(get_db)):
    """Última lectura registrada para esp_id."""
    return ultima_lectura(db, esp_id)

@router.get("", response_model=List[LecturaOut])
def get_ultimas(esp_id: str = Depends(resolve_esp_id), db: Session = Depends(get_db)) -> List[LecturaOut]:
    """Lecturas de los últimos 7 días (desc) para esp_id."""
    return ultimas_lecturas_7d(db, esp_id)

@router.get("/csv")
def get_csv(
    desde: str = Query(..., description="YYYY-MM-DD"),
    hasta: str = Query(..., description="YYYY-MM-DD"),
    esp_id: str = Depends(resolve_esp_id),
):
    """Genera CSV de lecturas para esp_id entre fechas [desde, hasta] (hora local)."""
    try:
        csv_text = csv_from_range(desde, hasta)  # ← ahora sí
        filename = f"{esp_id}_{desde}_a_{hasta}.csv"
        return StreamingResponse(
            iter([csv_text]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el CSV: {e}")
