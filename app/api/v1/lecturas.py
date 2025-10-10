from fastapi import APIRouter, Query
from typing import List
from app.schemas.lecturas import LecturaIn, LecturaOut
from app.servicios.funciones import agregar_lectura, ultima_lectura, ultimas_lecturas

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

@router.post("", response_model=LecturaOut, status_code=201)
def post_lectura(payload: LecturaIn):
    """Recibe una lectura nueva desde el sensor."""
    return agregar_lectura(**payload.model_dump())

@router.get("/ultima", response_model=LecturaOut | None)
def get_ultima():
    """Devuelve la última lectura registrada."""
    return ultima_lectura()

@router.get("", response_model=List[LecturaOut])
def get_ultimas(limit: int = Query(20, ge=1, le=200)):
    """Devuelve las últimas lecturas (por defecto 20)."""
    return ultimas_lecturas(limit=limit)
