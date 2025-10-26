from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.models import Device, Mecanismos, Config

def create_device(db: Session, esp_id: str, nombre: str | None = None) -> Device:
    d = Device(esp_id=esp_id, nombre=nombre)
    db.add(d)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Ya existe un dispositivo con ese esp_id")
    db.refresh(d)
    # crear snapshots 1:1
    db.add(Mecanismos(device_id=d.id))
    db.add(Config(device_id=d.id))
    db.commit()
    db.refresh(d)
    return d

def list_devices(db: Session) -> list[Device]:
    return db.query(Device).order_by(Device.id.asc()).all()

def get_device_by_esp_id(db: Session, esp_id: str) -> Device | None:
    return db.query(Device).filter(Device.esp_id == esp_id).first()

def update_device(db: Session, esp_id: str, nombre: str | None = None, activo: bool | None = None) -> Device:
    d = get_device_by_esp_id(db, esp_id)
    if not d:
        raise LookupError("Dispositivo no encontrado")
    if nombre is not None:
        d.nombre = nombre
    if activo is not None:
        d.activo = activo
    db.commit()
    db.refresh(d)
    return d

def delete_device(db: Session, esp_id: str) -> None:
    d = get_device_by_esp_id(db, esp_id)
    if not d:
        raise LookupError("Dispositivo no encontrado")
    db.delete(d)
    db.commit()
