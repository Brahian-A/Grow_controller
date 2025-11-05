import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models import Device, Config, Mecanismos, Lectura 
from app.servicios.mqtt_funciones import enviar_cmd_mqtt

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Variables Globales y Función de Cooldown ---
_COOLDOWN_S = 30
_ultimo_cambio = {}

def _puede_cambiar(clave_mecanismo: str) -> bool:
    """
    Verifica si ha pasado suficiente tiempo (_COOLDOWN_S) desde el último cambio 
    para un mecanismo específico (ej: "esp_id:riego"). 
    Si puede cambiar, actualiza el tiempo y retorna True.
    """
    ahora = datetime.utcnow()
    t = _ultimo_cambio.get(clave_mecanismo)
    
    if t is None or (ahora - t) >= timedelta(seconds=_COOLDOWN_S):
        _ultimo_cambio[clave_mecanismo] = ahora
        logging.debug(f"Permitido cambio para {clave_mecanismo}.")
        return True
        
    logging.debug(f"Negado cambio para {clave_mecanismo}. Cooldown activo.")
    return False

def procesar_umbrales(db: Session, esp_id: str, lectura: Lectura):
    """
    Aplica la lógica de control automático (umbral + histéresis de margen y tiempo)
    basada en la última lectura de telemetría y la configuración del dispositivo.
    """
    device = db.query(Device).filter(Device.esp_id == esp_id).first()
    if not device:
        logging.warning(f"[AUTO] Dispositivo {esp_id} no encontrado.")
        return

    cfg = db.query(Config).filter(Config.device_id == device.id).first()
    if not cfg:
        logging.warning(f"[AUTO] Configuración no encontrada para {esp_id}.")
        return

    # Obtener/Crear estado de Mecanismos
    mech = db.query(Mecanismos).filter(Mecanismos.device_id == device.id).first()
    if not mech:
        mech = Mecanismos(device_id=device.id)
        db.add(mech)
        db.commit()
        db.refresh(mech)

    try:
        margen_base = float(cfg.margen or 0)
    except ValueError:
        logging.error(f"[AUTO] El margen '{cfg.margen}' no es un número válido.")
        margen_base = 0.0

    margen_temp = min(margen_base, 2.0)  # Máximo 2.0°C de margen
    margen_suelo = max(margen_base, 5.0) # Mínimo 5.0% de margen

    cambios = {}

    # --- RIEGO (humedad de suelo) ---
    if lectura.humedad_suelo is not None and cfg.humedad_suelo is not None:
        try:
            suelo = float(lectura.humedad_suelo)
            set_suelo = float(cfg.humedad_suelo)
            low_suelo  = set_suelo - margen_suelo
            high_suelo = set_suelo + margen_suelo
            
            mecanismo_key = f"{esp_id}:riego"

            if suelo < low_suelo:
                # El suelo está seco y la bomba está apagada -> ENCENDER
                if not mech.bomba and _puede_cambiar(mecanismo_key):
                    # CORREGIDO: cmd dict primero, esp_id segundo
                    enviar_cmd_mqtt({"cmd": "SET", "target": "RIEGO", "value": "ON"}, esp_id)
                    mech.bomba = True
                    cambios["riego"] = "ON"
                    logging.info(f"[AUTO-RIEGO] Humedad ({suelo:.1f}%) < LOW ({low_suelo:.1f}%). ON.")
            elif suelo > high_suelo:
                # El suelo está muy húmedo y la bomba está encendida -> APAGAR
                if mech.bomba and _puede_cambiar(mecanismo_key):
                    # CORREGIDO: cmd dict primero, esp_id segundo
                    enviar_cmd_mqtt({"cmd": "SET", "target": "RIEGO", "value": "OFF"}, esp_id)
                    mech.bomba = False
                    cambios["riego"] = "OFF"
                    logging.info(f"[AUTO-RIEGO] Humedad ({suelo:.1f}%) > HIGH ({high_suelo:.1f}%). OFF.")
        except ValueError as e:
            logging.error(f"[AUTO-RIEGO] Error de valor: {e}")


    # --- temperatura (ventilador / luz calor) ---
    if lectura.temperatura is not None and cfg.temperatura is not None:
        try:
            temp = float(lectura.temperatura)
            set_temp = float(cfg.temperatura)
            low_temp  = set_temp - margen_temp
            high_temp = set_temp + margen_temp

            key_vent = f"{esp_id}:vent"
            key_luz = f"{esp_id}:luz"

            if temp > high_temp:
                # hace calor: ventilador ON, luz OFF
                logging.debug(f"[AUTO-TEMP] Temp ({temp:.1f}°C) > HIGH ({high_temp:.1f}°C). Enfriando...")
                hizo_cambio = False
                
                if not mech.ventilador and _puede_cambiar(key_vent):
                    # CORREGIDO: cmd dict primero, esp_id segundo
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "ON"}, esp_id)
                    mech.ventilador = True
                    cambios["ventilador"] = "ON"
                    hizo_cambio = True
                    logging.info("[AUTO-TEMP] VENT ON.")
                    
                if mech.luz and _puede_cambiar(key_luz):
                    # CORREGIDO: cmd dict primero, esp_id segundo
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "OFF"}, esp_id)
                    mech.luz = False
                    cambios["luz"] = "OFF"
                    hizo_cambio = True
                    logging.info("[AUTO-TEMP] LUZ OFF.")
                
                if not hizo_cambio and (not mech.ventilador and not mech.luz):
                    _ultimo_cambio[key_vent] = datetime.utcnow()
                    _ultimo_cambio[key_luz] = datetime.utcnow()

            elif temp < low_temp:
                # hace frio: ventilador OFF, luz ON
                logging.debug(f"[AUTO-TEMP] Temp ({temp:.1f}°C) < LOW ({low_temp:.1f}°C). Calentando...")
                hizo_cambio = False
                
                if mech.ventilador and _puede_cambiar(key_vent):
                    # CORREGIDO: cmd dict primero, esp_id segundo
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "OFF"}, esp_id)
                    mech.ventilador = False
                    cambios["ventilador"] = "OFF"
                    hizo_cambio = True
                    logging.info("[AUTO-TEMP] VENT OFF.")
                    
                if not mech.luz and _puede_cambiar(key_luz):
                    # CORREGIDO: cmd dict primero, esp_id segundo
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "ON"}, esp_id)
                    mech.luz = True
                    cambios["luz"] = "ON"
                    hizo_cambio = True
                    logging.info("[AUTO-TEMP] LUZ ON.")
                    
                if not hizo_cambio and (mech.ventilador and mech.luz):
                    _ultimo_cambio[key_vent] = datetime.utcnow()
                    _ultimo_cambio[key_luz] = datetime.utcnow()

            
        except ValueError as e:
            logging.error(f"[AUTO-TEMP] Error de valor: {e}")

    if cambios:
        db.commit()
        logging.info(f"[AUTO CONTROL] {esp_id} → CAMBIOS EFECTUADOS: {cambios}")
    else:
        logging.debug(f"[AUTO CONTROL] {esp_id} → No se requirieron cambios de estado.")
