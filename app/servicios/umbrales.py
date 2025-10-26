from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Device, Config, Mecanismos, Lectura
from app.servicios.mqtt_funciones import enviar_cmd_mqtt

_COOLDOWN_S = 30
_ultimo_cambio = {}

def _puede_cambiar(esp_id: str) -> bool:
    ahora = datetime.utcnow()
    t = _ultimo_cambio.get(esp_id)
    if t is None or (ahora - t) >= timedelta(seconds=_COOLDOWN_S):
        _ultimo_cambio[esp_id] = ahora
        return True
    return False

def procesar_umbrales(db: Session, esp_id: str, lectura: Lectura):
    device = db.query(Device).filter(Device.esp_id == esp_id).first()
    if not device:
        return

    cfg = db.query(Config).filter(Config.device_id == device.id).first()
    if not cfg:
        return

    mech = db.query(Mecanismos).filter(Mecanismos.device_id == device.id).first()
    if not mech:
        mech = Mecanismos(device_id=device.id)
        db.add(mech)
        db.commit()
        db.refresh(mech)

    # márgenes dinámicos a partir de cfg.margen
    margen_temp = min(float(cfg.margen or 0), 2.0)
    margen_suelo = max(float(cfg.margen or 0), 5.0)

    cambios = {}

    # --- RIEGO (humedad de suelo) ---
    if lectura.humedad_suelo is not None and cfg.humedad_suelo is not None:
        suelo = float(lectura.humedad_suelo)
        set_suelo = float(cfg.humedad_suelo)
        low_suelo  = set_suelo - margen_suelo
        high_suelo = set_suelo + margen_suelo

        if suelo < low_suelo:
            if not mech.bomba and _puede_cambiar(f"{esp_id}:riego"):
                enviar_cmd_mqtt({"cmd": "SET", "target": "RIEGO", "value": "ON"})
                mech.bomba = True
                cambios["riego"] = "ON"
        elif suelo > high_suelo:
            if mech.bomba and _puede_cambiar(f"{esp_id}:riego"):
                enviar_cmd_mqtt({"cmd": "SET", "target": "RIEGO", "value": "OFF"})
                mech.bomba = False
                cambios["riego"] = "OFF"

    # --- TEMPERATURA (ventilador / luz calefactora) ---
    if lectura.temperatura is not None and cfg.temperatura is not None:
        temp = float(lectura.temperatura)
        set_temp = float(cfg.temperatura)
        low_temp  = set_temp - margen_temp
        high_temp = set_temp + margen_temp

        if temp > high_temp:
            # hace calor: ventilador ON, luz OFF
            hizo_cambio = False
            if not mech.ventilador and _puede_cambiar(f"{esp_id}:vent"):
                enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "ON"})
                mech.ventilador = True
                cambios["ventilador"] = "ON"
                hizo_cambio = True
            if mech.luz and _puede_cambiar(f"{esp_id}:luz"):
                enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "OFF"})
                mech.luz = False
                cambios["luz"] = "OFF"
                hizo_cambio = True
            if not hizo_cambio:
                _ultimo_cambio[f"{esp_id}:vent"] = datetime.utcnow()
                _ultimo_cambio[f"{esp_id}:luz"] = datetime.utcnow()

        elif temp < low_temp:
            # hace frío: ventilador OFF, luz ON
            hizo_cambio = False
            if mech.ventilador and _puede_cambiar(f"{esp_id}:vent"):
                enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "OFF"})
                mech.ventilador = False
                cambios["ventilador"] = "OFF"
                hizo_cambio = True
            if not mech.luz and _puede_cambiar(f"{esp_id}:luz"):
                enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "ON"})
                mech.luz = True
                cambios["luz"] = "ON"
                hizo_cambio = True
            if not hizo_cambio:
                _ultimo_cambio[f"{esp_id}:vent"] = datetime.utcnow()
                _ultimo_cambio[f"{esp_id}:luz"] = datetime.utcnow()
        # si está dentro de [low_temp, high_temp], no hacer nada (histeresis)

    if cambios:
        db.commit()
        print(f"[AUTO CONTROL] {esp_id} → {cambios}")
