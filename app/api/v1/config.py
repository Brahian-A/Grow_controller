from fastapi import APIRouter
from app.schemas.config import ConfigIn, ConfigOut
from app.db.session import SessionLocal
from app.servicios.funciones import get_config, set_config

router = APIRouter(prefix="/config", tags=["config"])

@router.get("", response_model=ConfigOut)
def get_cfg():
    with SessionLocal() as db:
        return get_config(db)

@router.put("", response_model=ConfigOut)
def put_cfg(payload: ConfigIn):
    return set_config(**payload.model_dump(exclude_none=True))
