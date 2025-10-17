from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.lecturas import LecturaIn, LecturaOut
from app.servicios.funciones import agregar_lectura, ultima_lectura, ultimas_lecturas

router = APIRouter(prefix="/lecturas", tags=["lecturas"])

@router.post("", response_model=LecturaOut, status_code=201)
def post_lectura(payload: LecturaIn, db: Session = Depends(get_db)):
    "Recibe una lectura nueva desde el sensor"
    try:
        return agregar_lectura(db, **payload.model_dump())
    except Exception as e:
        print(f"[ERROR] No se pudo guardar la lectura: {e}")
        raise HTTPException(status_code=500, detail="No se pudo guardar la lectura")

@router.get("/ultima", response_model=LecturaOut)
def get_ultima(db: Session = Depends(get_db)):
    "devuelve la última lectura registrada"
    data = ultima_lectura(db)
    if not data:
        raise HTTPException(status_code=404, detail="No hay lecturas registradas")
    return data

@router.get("", response_model=List[LecturaOut])
def get_ultimas(limit: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    "devuelve las ultimas lecturas (por defecto 20)"
    try:
        return ultimas_lecturas(db, limit=limit)
    except Exception as e:
        print(f"[ERROR] No se pudieron obtener las lecturas: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener las lecturas")
