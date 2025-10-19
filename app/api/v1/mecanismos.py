from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.servicios.funciones import get_status, set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

@router.get("", response_model=MecanismosOut)
def get_stat(db: Session = Depends(get_db)):
    "returns the current status of the pump, fan and light"
    try:
        data = get_status(db)
        return data
    except Exception as e:
        print(f"[ERROR] No se pudo obtener estado de mecanismos: {e}")
        raise HTTPException(status_code=500, detail="No se pudo obtener el estado de mecanismos")

@router.put("", response_model=MecanismosOut)
def put_mech(payload: MecanismosIn, db: Session = Depends(get_db)):
    "modify the state of the mechanisms, Example: fan: on"
    cambios = payload.model_dump(exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un campo para actualizar")

    try:
        return set_mecanismo(db, **cambios)
    except Exception as e:
        print(f"[ERROR] No se pudo actualizar mecanismos: {e}")
        raise HTTPException(status_code=500, detail="No se pudo actualizar los mecanismos")

