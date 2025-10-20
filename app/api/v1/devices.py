from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.device import DeviceIn, DeviceOut, DeviceUpdate
from app.servicios.devices import (
    create_device, list_devices, get_device_by_esp_id, update_device, delete_device
)

router = APIRouter(prefix="/dispositivos", tags=["dispositivos"])

@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def add_device(payload: DeviceIn, db: Session = Depends(get_db)):
    try:
        d = create_device(db, payload.esp_id, payload.nombre)
        return d
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el dispositivo: {e}")

@router.get("", response_model=list[DeviceOut])
def get_devices(db: Session = Depends(get_db)):
    return list_devices(db)

@router.get("/{esp_id}", response_model=DeviceOut)
def get_device(esp_id: str, db: Session = Depends(get_db)):
    d = get_device_by_esp_id(db, esp_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return d

@router.put("/{esp_id}", response_model=DeviceOut)
def edit_device(esp_id: str, payload: DeviceUpdate, db: Session = Depends(get_db)):
    try:
        return update_device(db, esp_id, nombre=payload.nombre, activo=payload.activo)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{esp_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_device(esp_id: str, db: Session = Depends(get_db)):
    try:
        delete_device(db, esp_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return
