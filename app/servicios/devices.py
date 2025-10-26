from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.models import Device, Mecanismos, Config


# ============================================================
# CRUD PRINCIPAL DE DEVICES
# ============================================================

def create_device(db: Session, esp_id: str, nombre: str | None = None) -> Device:
    """Crea un nuevo device y sus registros relacionados (Mecanismos + Config)."""
    d = Device(esp_id=esp_id, nombre=nombre)
    db.add(d)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Ya existe un device con ese esp_id")
    db.refresh(d)
    # crear snapshots 1:1
    db.add(Mecanismos(device_id=d.id))
    db.add(Config(device_id=d.id))
    db.commit()
    db.refresh(d)
    return d


def list_devices(db: Session) -> list[Device]:
    """Devuelve la lista completa de devices registrados."""
    return db.query(Device).order_by(Device.id.asc()).all()


def get_device_by_esp_id(db: Session, esp_id: str) -> Device | None:
    """Devuelve un device por su esp_id, o None si no existe."""
    return db.query(Device).filter(Device.esp_id == esp_id).first()


def update_device(db: Session, esp_id: str, nombre: str | None = None, activo: bool | None = None) -> Device:
    """Actualiza el nombre o estado activo de un device."""
    d = get_device_by_esp_id(db, esp_id)
    if not d:
        raise LookupError("Device no encontrado")
    if nombre is not None:
        d.nombre = nombre
    if activo is not None:
        d.activo = activo
    db.commit()
    db.refresh(d)
    return d


def delete_device(db: Session, esp_id: str) -> None:
    """Elimina un device y sus relaciones."""
    d = get_device_by_esp_id(db, esp_id)
    if not d:
        raise LookupError("Device no encontrado")
    db.delete(d)
    db.commit()


# ============================================================
# AUXILIAR PARA MQTT (auto-creación)
# ============================================================

def get_or_create_device(db: Session, esp_id: str, nombre: str | None = None) -> Device:
    """
    Devuelve el device si existe, o lo crea automáticamente (usado por MQTT).
    """
    d = get_device_by_esp_id(db, esp_id)
    if not d:
        d = create_device(db, esp_id, nombre)
    return d
