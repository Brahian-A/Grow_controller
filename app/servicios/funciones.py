# app/servicios/funciones.py
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.models import Lectura, Mecanismos, Config

ALERTA_NIVEL_UMBRAL = 15 


# ===== Helper ESP32  =====
def _get_esp32_connection():
    try:
        from app.conexiones.conexion_esp32 import obtener_conexion
    except Exception as e:
        print("[ESP32] módulo no disponible:", e)
        return None
    try:
        return obtener_conexion()
    except Exception as e:
        print("[ESP32] no se pudo abrir conexión:", e)
        return None


# ================= CONFIG =================
def get_config(db: Session) -> Config:
    cfg = db.query(Config).first()
    if not cfg:
        cfg = Config()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def set_config(
    db: Session,
    humedad_suelo_umbral_alto: Optional[int] = None,
    humedad_suelo_umbral_bajo: Optional[int] = None,
    temperatura_umbral_alto: Optional[int] = None,
    temperatura_umbral_bajo: Optional[int] = None,
    humedad_umbral_alto: Optional[int] = None,
    humedad_umbral_bajo: Optional[int] = None,
) -> Config:
    try:
        cfg = get_config(db)
        if humedad_suelo_umbral_alto is not None:
            cfg.humedad_suelo_umbral_alto = humedad_suelo_umbral_alto
        if humedad_suelo_umbral_bajo is not None:
            cfg.humedad_suelo_umbral_bajo = humedad_suelo_umbral_bajo
        if temperatura_umbral_alto is not None:
            cfg.temperatura_umbral_alto = temperatura_umbral_alto
        if temperatura_umbral_bajo is not None:
            cfg.temperatura_umbral_bajo = temperatura_umbral_bajo
        if humedad_umbral_alto is not None:
            cfg.humedad_umbral_alto = humedad_umbral_alto
        if humedad_umbral_bajo is not None:
            cfg.humedad_umbral_bajo = humedad_umbral_bajo

        db.commit()
        db.refresh(cfg)
        return cfg
    except Exception:
        db.rollback()
        raise


# =============== MECANISMOS ===============
def get_status(db: Session) -> dict:
    mech = db.query(Mecanismos).first()
    created_or_changed = False
    if not mech:
        mech = Mecanismos()
        db.add(mech)
        created_or_changed = True

    # Sincronía opcional con ESP32
    snapshot_nivel = None
    cx = _get_esp32_connection()
    if cx is not None:
        try:
            snap = cx.snapshot()
            if "bomba" in snap and mech.bomba != bool(snap["bomba"]):
                mech.bomba = bool(snap["bomba"]); created_or_changed = True
            if "ventilador" in snap and mech.ventilador != bool(snap["ventilador"]):
                mech.ventilador = bool(snap["ventilador"]); created_or_changed = True
            if "lamparita" in snap and mech.lamparita != bool(snap["lamparita"]):
                mech.lamparita = bool(snap["lamparita"]); created_or_changed = True
            # Fallback de alerta si no hay lecturas aún:
            if "nivel_agua" in snap:
                try:
                    snapshot_nivel = float(snap["nivel_agua"])
                except Exception:
                    snapshot_nivel = None
        except Exception as e:
            print("[ESP32] snapshot falló:", e)

    if created_or_changed:
        db.commit()
        db.refresh(mech)

    ultima = ultima_lectura(db)
    if ultima is not None:
        alerta_agua = (ultima.nivel_de_agua <= ALERTA_NIVEL_UMBRAL)
    else:
        alerta_agua = (snapshot_nivel is not None and snapshot_nivel <= ALERTA_NIVEL_UMBRAL)

    return {
        "id": mech.id,
        "bomba": mech.bomba,
        "lamparita": mech.lamparita,
        "ventilador": mech.ventilador,
        "alerta_agua": alerta_agua,
    }


def set_mecanismo(
    db: Session,
    bomba: Optional[bool] = None,
    lamparita: Optional[bool] = None,
    ventilador: Optional[bool] = None,
) -> dict:
    cx = _get_esp32_connection()
    if cx is not None:
        try:
            if bomba is not None:      cx.set_bomba(bool(bomba))
            if ventilador is not None: cx.set_ventilador(bool(ventilador))
            if lamparita is not None:  cx.set_lamparita(bool(lamparita))
        except Exception as e:
            print("[ESP32] set_mecanismo falló:", e)

    try:
        mech = db.query(Mecanismos).first()
        if not mech:
            mech = Mecanismos()
            db.add(mech)

        if bomba is not None:      mech.bomba = bool(bomba)
        if lamparita is not None:  mech.lamparita = bool(lamparita)
        if ventilador is not None: mech.ventilador = bool(ventilador)

        db.commit()
        db.refresh(mech)

        ultima = ultima_lectura(db)
        alerta_agua = (ultima.nivel_de_agua <= ALERTA_NIVEL_UMBRAL) if ultima else None

        return {
            "id": mech.id,
            "bomba": mech.bomba,
            "lamparita": mech.lamparita,
            "ventilador": mech.ventilador,
            "alerta_agua": alerta_agua,
        }
    except Exception:
        db.rollback()
        raise


# ================= LECTURAS =================
def agregar_lectura(
    db: Session,
    temperatura: float,
    humedad: float,
    humedad_suelo: float,
    nivel_de_agua: float,
) -> Lectura:
    """
    Inserta una lectura completa (incluye nivel_de_agua proveniente de la ESP).
    """
    try:
        obj = Lectura(
            temperatura=temperatura,
            humedad=humedad,
            humedad_suelo=humedad_suelo,
            nivel_de_agua=nivel_de_agua,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except Exception:
        db.rollback()
        raise


def ultima_lectura(db: Session) -> Optional[Lectura]:
    stmt = select(Lectura).order_by(desc(Lectura.fecha_hora)).limit(1)
    return db.execute(stmt).scalars().first()


def ultimas_lecturas(db: Session, limit: int = 20) -> List[Lectura]:
    stmt = select(Lectura).order_by(desc(Lectura.fecha_hora)).limit(limit)
    return list(db.execute(stmt).scalars().all())
