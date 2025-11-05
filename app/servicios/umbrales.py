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
        logging.info(f"[cooldown] permitido cambio para {clave_mecanismo}.") # Cambio a INFO para mejor visibilidad
        return True
        
    logging.info(f"[cooldown] negado cambio para {clave_mecanismo}. cooldown activo.") # Cambio a INFO para mejor visibilidad
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
    margen_temp = min(margen_base, 2.0)     # margen de temperatura, max 2.0°C
    margen_suelo = max(margen_base, 5.0)    # margen de suelo, min 5.0%
    margen_hum_amb = max(margen_base, 5.0)  # MARGEN NUEVO para humedad ambiental

    cambios = {}

    # --- 1. RIEGO (Humedad de Suelo) ---
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

    # --- 2. HUMEDAD AMBIENTAL (Ventilador) ---
    # Lógica: Si la humedad ambiente es muy alta, forzar encendido del ventilador.
    if lectura.humedad_ambiente is not None and cfg.humedad is not None:
        try:
            hum_amb = float(lectura.humedad_ambiente)
            set_hum_amb = float(cfg.humedad_ambiente)
            
            high_hum_amb = set_hum_amb + margen_hum_amb # Umbral superior para encender ventilador
            
            key_vent = f"{esp_id}:vent" # Reusamos la misma clave de cooldown
            
            logging.info(f"[auto-hum] l: {hum_amb:.1f}%. set: {set_hum_amb:.1f}%. umbral: high={high_hum_amb:.1f}%. actual: {'on' if mech.ventilador else 'off'}")

            if hum_amb > high_hum_amb:
                # Humedad ambiental alta -> forzar ventilador ON (sin apagar luz)
                if not mech.ventilador and _puede_cambiar(key_vent):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "ON"}, esp_id)
                    mech.ventilador = True
                    cambios["ventilador"] = "ON"
                    logging.info(f"[auto-hum] acción: humedad ambiente ({hum_amb:.1f}%) > high ({high_hum_amb:.1f}%). se ha encendido ventilador.")
                else:
                    logging.info(f"[auto-hum] no acción: requiere vent on, pero ya estaba on o en cooldown.")

            # Nota: El apagado por humedad ambiente lo maneja indirectamente la lógica de temperatura 
            # cuando la temperatura baja y ya no necesita enfriar.
            
        except ValueError as e:
            logging.error(f"[auto-hum] error de valor: {e}")

    # --- 3. TEMPERATURA (Ventilador y Luz-Calor) ---
    # Lógica: Maximizar la Luz (ON) para el crecimiento. Solo apagar la luz si la temperatura es crítica.
    if lectura.temperatura is not None and cfg.temperatura is not None:
        try:
            temp = float(lectura.temperatura)
            set_temp = float(cfg.temperatura)
            
            # cálculo de umbrales con histéresis
            low_temp  = set_temp - margen_temp # umbral inferior para calentar (luz on)
            high_temp = set_temp + margen_temp # umbral superior para enfriar (ventilador on/luz off)

            key_vent = f"{esp_id}:vent"
            key_luz = f"{esp_id}:luz"

            logging.info(f"[auto-temp] l: {temp:.1f}°c. set: {set_temp:.1f}°c. umbrales: low={low_temp:.1f}°c, high={high_temp:.1f}°c. actual: v={'on' if mech.ventilador else 'off'}, l={'on' if mech.luz else 'off'}")


            if temp > high_temp:
                # 1. HACE CALOR: Objetivo enfriar -> Vent ON, Luz OFF (solo si es necesario)
                logging.info(f"[auto-temp] enfriando. temp ({temp:.1f}°c) > high ({high_temp:.1f}°c).")
                
                # Accion Ventilador: debe estar ON (si no lo activó ya la humedad)
                if not mech.ventilador and _puede_cambiar(key_vent):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "ON"}, esp_id)
                    mech.ventilador = True
                    cambios["ventilador"] = "ON"
                    logging.info("[auto-temp] acción: Vent ON.")
                elif mech.ventilador:
                    logging.info("[auto-temp] no acción: Vent ya estaba ON.")
                    
                # Accion Luz: Se APAGA SOLO AQUÍ para evitar el sobrecalentamiento.
                if mech.luz and _puede_cambiar(key_luz):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "OFF"}, esp_id)
                    mech.luz = False
                    cambios["luz"] = "OFF"
                    logging.info("[auto-temp] acción: Luz OFF para enfriar.")
                elif not mech.luz:
                    logging.info("[auto-temp] no acción: Luz ya estaba OFF.")

            elif temp < low_temp:
                # 2. HACE FRÍO: Objetivo calentar -> Vent OFF, Luz ON
                logging.info(f"[auto-temp] calentando. temp ({temp:.1f}°c) < low ({low_temp:.1f}°c).")
                
                # Accion Ventilador: Se APAGA para calentar (o si lo activó la humedad ambiente, se apaga aquí si ya no se necesita)
                if mech.ventilador and _puede_cambiar(key_vent):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "VENT", "value": "OFF"}, esp_id)
                    mech.ventilador = False
                    cambios["ventilador"] = "OFF"
                    logging.info("[auto-temp] acción: Vent OFF para calentar.")
                elif not mech.ventilador:
                    logging.info("[auto-temp] no acción: Vent ya estaba OFF.")
                    
                # Accion Luz: Se ENCIENDE para calentar y para el crecimiento.
                if not mech.luz and _puede_cambiar(key_luz):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "ON"}, esp_id)
                    mech.luz = True
                    cambios["luz"] = "ON"
                    logging.info("[auto-temp] acción: Luz ON para calentar y crecer.")
                elif mech.luz:
                    logging.info("[auto-temp] no acción: Luz ya estaba ON.")

            else:
                # 3. ZONA DE HISTÉRESIS (low_temp <= temp <= high_temp): Prioridad a la Luz
                logging.info("[auto-temp] zona ideal. mantener luz ON para crecimiento.")

                # Accion Luz: SIEMPRE debe estar ON en este rango (a menos que ya esté ON).
                if not mech.luz and _puede_cambiar(key_luz):
                    enviar_cmd_mqtt({"cmd": "SET", "target": "LUZ", "value": "ON"}, esp_id)
                    mech.luz = True
                    cambios["luz"] = "ON"
                    logging.info("[auto-temp] acción: Luz ON (crecimiento).")
                
                # Accion Ventilador: Mantiene el estado que tenía al entrar en la histéresis (se apaga SOLO si cae a < low_temp).
                logging.info(f"[auto-temp] no acción: vent mantiene estado ('{'on' if mech.ventilador else 'off'}).")
                logging.info(f"[auto-temp] no acción: temp dentro del margen de histéresis ({low_temp:.1f}°c - {high_temp:.1f}°c).")
            
        except ValueError as e:
            logging.error(f"[auto-temp] error de valor: {e}")

    # notificar si hubo cambios
    if cambios:
        # nota: el commit se hará en el mqtt_listener.py
        logging.info(f"[auto control] {esp_id} → cambios propuestos: {cambios}")
    else:
        logging.info(f"[auto control] {esp_id} → no se requirieron cambios de estado.")