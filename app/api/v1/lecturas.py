from fastapi import APIRouter, Query
from typing import List
from app.schemas.lecturas import LecturaIn, LecturaOut
from fastapi.responses import StreamingResponse
from datetime import datetime
from app.servicios.funciones import agregar_lectura, ultima_lectura, ultimas_lecturas_7d, csv_from

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

@router.post("", response_model=LecturaOut, status_code=201)
def post_lectura(payload: LecturaIn):
    "Recibe una lectura nueva desde el sensor"
    return agregar_lectura(**payload.model_dump())

@router.get("/ultima", response_model=LecturaOut | None)
def get_ultima():
    "devuelve la última lectura registrada"
    return ultima_lectura()

@router.get("", response_model=List[LecturaOut])
def get_ultimas():
    "devuelve las ultimas lecturas (por defecto 20)"
    return ultimas_lecturas_7d()

@router.get("/csv")
def get_csv(days: int = Query(..., ge=1, le=365)):
    csv_text = csv_from(days)
    filename = f"lecturas_ultimos_{days}_dias_{datetime.now().date().isoformat()}.csv"
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )