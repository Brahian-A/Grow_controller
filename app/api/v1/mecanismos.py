from fastapi import APIRouter
from app.schemas.mecanismos import MecanismosIn, MecanismosOut
from app.db.session import SessionLocal
from app.servicios.funciones import get_mecanismos, set_mecanismo

router = APIRouter(prefix="/mecanismos", tags=["mecanismos"])

@router.get("", response_model=MecanismosOut)
def get_mech():
    with SessionLocal() as db:
        return get_mecanismos(db)

@router.put("", response_model=MecanismosOut)
def put_mech(payload: MecanismosIn):
    return set_mecanismo(**payload.model_dump(exclude_none=True))
