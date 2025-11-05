import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models import Device, Config, Mecanismos, Lectura 
from app.servicios.mqtt_funciones import enviar_cmd_mqtt

# configuración del logging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- variables globales y función de cooldown ---
_COOLDOWN_S = 30 # segundos mínimos entre cambios de estado.
_ultimo_cambio = {}

def _puede_cambiar(clave_mecanismo: str) -> bool:
    """verifica si ha pasado el tiempo de cooldown desde el último cambio."""
    ahora = datetime.utcnow()
    t = _ultimo_cambio.get(clave_mecanismo)
    
    if t is None or (ahora - t) >= timedelta(seconds=_COOLDOWN_S):
        _ultimo_cambio[clave_mecanismo] = ahora
        logging.debug(f"permitido cambio para {clave_mecanismo}.")
        return True
        
    logging.debug(f"negado cambio para {clave_mecanismo}. cooldown activo.")
    return False

def procesar_umbrales(db: Session, esp_id: str, lectura: Lectura):
    """aplica la lógica de control automático (histéresis y cooldown)."""
    device = db.query(Device).filter(Device.esp_id == esp_id).first()
    if not device:
        logging.warning(f"[auto] dispositivo {esp_id} no encontrado.")
        return

    cfg = db.query(Config).filter(Config.device_id == device.id).first()
    if not cfg:
        logging.warning(f"[auto] configuración no encontrada para {esp_id}.")
        return

    # obtener o crear estado de mecanismos
    mech = db.query(Mecanismos).filter(Mecanismos.device_id == device.id).first()
    if not mech:
        mech = Mecanismos(device_id=device.id)
        db.add(mech)
        # el commit lo maneja el mqtt_listener

    try:
        # margen de histéresis base
        margen_base = float(cfg.margen or 0)
    except ValueError:
        logging.error(f"[auto] el margen '{cfg.margen}' no es un número válido.")
        margen_base = 0.0

    # márgenes específicos
    margen_temp = min(margen_base, 1.5)  # max 2.0°c
    margen_suelo = max(margen_base, 5.0) # min 5.0%

    cambios = {}

    # --- riego (humedad de suelo) ---
    if lectura.humedad_suelo is not None and cfg.humedad_suelo is not None:
        try:
            suelo = float(lectura.humedad_suelo)
            set_suelo = float(cfg.humedad_suelo)
            
            # cálculo de umbrales con histéresis
            low_suelo  = set_suelo - margen_suelo # umbral inferior para encender
            high_suelo = set_suelo + margen_suelo # umbral superior para apagar
            
            mecanismo_key = f"{esp_id}:riego"

            logging.info(f"[auto-riego] l: {suelo:.1f}%. set: {set_suelo:.1f}%. umbrales: low={low_suelo:.1f}%, high={high_suelo:.1f}%. actual: {'on' if mech.bomba else 'off'}")


            if suelo < low_suelo:
                # suelo seco -> encender bomba
                if not mech.bomba and _puede_cambiar(mecanismo_key):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "RIEGO", "value": "ON"}, esp_id)
                    mech.bomba = True
                    cambios["riego"] = "ON"
                    logging.info(f"[auto-riego] acción: humedad ({suelo:.1f}%) < low ({low_suelo:.1f}%). se ha encendido riego.")
                else:
                    logging.info(f"[auto-riego] no acción: requiere on, pero ya estaba on o en cooldown.")
            elif suelo > high_suelo:
                # suelo muy húmedo -> apagar bomba
                if mech.bomba and _puede_cambiar(mecanismo_key):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "RIEGO", "value": "OFF"}, esp_id)
                    mech.bomba = False
                    cambios["riego"] = "OFF"
                    logging.info(f"[auto-riego] acción: humedad ({suelo:.1f}%) > high ({high_suelo:.1f}%). se ha apagado riego.")
                else:
                    logging.info(f"[auto-riego] no acción: requiere off, pero ya estaba off o en cooldown.")
            else:
                 logging.info(f"[auto-riego] no acción: humedad está dentro del margen de histéresis ({low_suelo:.1f}% - {high_suelo:.1f}%).")
        except ValueError as e:
            logging.error(f"[auto-riego] error de valor: {e}")


    # --- temperatura (ventilador / luz calor) ---
    if lectura.temperatura is not None and cfg.temperatura is not None:
        try:
            temp = float(lectura.temperatura)
            set_temp = float(cfg.temperatura)
            
            # cálculo de umbrales con histéresis
            low_temp  = set_temp - margen_temp # umbral inferior para calentar (luz on)
            high_temp = set_temp + margen_temp # umbral superior para enfriar (ventilador on)

            key_vent = f"{esp_id}:vent"
            key_luz = f"{esp_id}:luz"

            logging.info(f"[auto-temp] l: {temp:.1f}°c. set: {set_temp:.1f}°c. umbrales: low={low_temp:.1f}°c, high={high_temp:.1f}°c. actual: v={'on' if mech.ventilador else 'off'}, l={'on' if mech.luz else 'off'}")


            if temp > high_temp:
                # hace calor: objetivo enfriar -> ventilador on, luz off
                logging.info(f"[auto-temp] enfriando. temp ({temp:.1f}°c) > high ({high_temp:.1f}°c).")
                
                # accion ventilador
                if not mech.ventilador and _puede_cambiar(key_vent):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "ON"}, esp_id)
                    mech.ventilador = True
                    cambios["ventilador"] = "ON"
                    logging.info("[auto-temp] acción: vent on.")
                elif mech.ventilador:
                     logging.info("[auto-temp] no acción: vent ya estaba on.")
                    
                # accion luz (para calentar)
                if mech.luz and _puede_cambiar(key_luz):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "OFF"}, esp_id)
                    mech.luz = False
                    cambios["luz"] = "OFF"
                    logging.info("[auto-temp] acción: luz off.")
                elif not mech.luz:
                     logging.info("[auto-temp] no acción: luz ya estaba off.")

            elif temp < low_temp:
                # hace frio: objetivo calentar -> ventilador off, luz on
                logging.info(f"[auto-temp] calentando. temp ({temp:.1f}°c) < low ({low_temp:.1f}°c).")
                
                # accion ventilador
                if mech.ventilador and _puede_cambiar(key_vent):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "OFF"}, esp_id)
                    mech.ventilador = False
                    cambios["ventilador"] = "OFF"
                    logging.info("[auto-temp] acción: vent off.")
                elif not mech.ventilador:
                    logging.info("[auto-temp] no acción: vent ya estaba off.")
                    
                # accion luz
                if not mech.luz and _puede_cambiar(key_luz):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "ON"}, esp_id)
                    mech.luz = True
                    cambios["luz"] = "ON"
                    logging.info("[auto-temp] acción: luz on.")
                elif mech.luz:
                    logging.info("[auto-temp] no acción: luz ya estaba on.")

            else:
                # zona de histéresis: no hacer nada (mantener estado)
                logging.info("[auto-temp] no acción: temperatura está dentro del margen de histéresis ({low_temp:.1f}°c - {high_temp:.1f}°c).")

            
        except ValueError as e:
            logging.error(f"[auto-temp] error de valor: {e}")

    # notificar si hubo cambios
    if cambios:
        # nota: el commit se hará en el mqtt_listener.py
        logging.info(f"[auto control] {esp_id} → cambios propuestos: {cambios}")
    else:
        logging.info(f"[auto control] {esp_id} → no se requirieron cambios de estado.")
