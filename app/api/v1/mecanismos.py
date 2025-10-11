from fastapi import APIRouter
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.db.session import SessionLocal
from app.servicios.funciones import get_status, set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

@router.get("", response_model=MecanismosOut)
def get_stat():
    "devuelve el estado actual de la bomba, ventilador, luz y nivel de agua"
    with SessionLocal() as db:
        return get_status(db)

@router.put("", response_model=MecanismosOut)
def put_mech(payload: MecanismosIn):
    "modifica el estado de los mecanismos ej: ventilador: on"
    return set_mecanismo(**payload.model_dump(exclude_none=True))


