from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import List
from app.schemas.lecturas import LecturaIn, LecturaOut
from fastapi.responses import StreamingResponse
from datetime import datetime
from app.api.deps import get_db
from sqlalchemy.orm import Session

from app.servicios.funciones import agregar_lectura, ultima_lectura, ultimas_lecturas_7d, csv_from

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

@router.post("", response_model=LecturaOut, status_code=201)
def post_lectura(payload: LecturaIn, db: Session = Depends(get_db)):
    "receive and store a new reading coming from the sensor"
    try:
        return agregar_lectura(**payload.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar Lectura: {e}")

@router.get("/ultima", response_model=LecturaOut | None)
def get_ultima(db: Session = Depends(get_db)):
    "return the last recorded reading"
    try:
        return ultima_lectura(db)
    except Exception: 
        raise HTTPException(status_code=404, detail="No se pudo encontrar la lectura")

@router.get("", response_model=List[LecturaOut])
def get_ultimas(db: Session = Depends(get_db)):
    "return all readings within the last 7 days (descending by timestamp)"
    return ultimas_lecturas_7d(db)

@router.get("/csv")
def get_csv(days: int = Query(..., ge=1, le=365)):
    "generate and download a CSV file with readings from the last N days"
    try:
        csv_text = csv_from(days)
        filename = f"lecturas_ultimos_{days}_dias_{datetime.now().date().isoformat()}.csv"
        return StreamingResponse(
            iter([csv_text]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e: 
        raise HTTPException(status_code=500, detail=f"No se pudo generar el CSV: {e}")
