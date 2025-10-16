# app/conexiones/conexion_esp32.py
import json, time, threading, logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import serial 

SERIAL_PORT = "/dev/ttyUSB1"
BAUD = 115200
SERIAL_TIMEOUT = 1.0
RETRY_SEC = 2

DB_PERIOD_SEC = 60

@dataclass
class Snapshot:
    last_data: Dict[str, Any] = field(default_factory=dict)
    last_data_ts: float = 0.0
    last_saved_ts: float = 0.0
    riego: bool = False
    vent: bool = False
    luz: bool = False

snap = Snapshot()

_serial: Optional[serial.Serial] = None
_reader_th: Optional[threading.Thread] = None
_stop = False
_write_lock = threading.Lock()


def _on_save_lectura(data: Dict[str, Any]) -> None:
    """
    Mapea JSON de la ESP a tu modelo Lectura y guarda UNA vez por minuto.
    JSON esperado desde la ESP (ej):
      {
        "type":"DATA",
        "raw":3445,
        "suelo_pct":0,
        "hum_amb":72.7,
        "temp_c":23.9,
        "nivel_pct":0, "nivel_estado":"VACIO",
        "v_bajo":0.8, "v_medio":0.7, "v_alto":0.6
      }
    """
    try:
        from app.servicios.funciones import agregar_lectura
        temperatura    = float(data.get("temp_c"))      if data.get("temp_c")   is not None else None
        humedad        = float(data.get("hum_amb"))     if data.get("hum_amb")  is not None else None
        humedad_suelo  = float(data.get("suelo_pct"))   if data.get("suelo_pct") is not None else None
        nivel_de_agua  = float(data.get("nivel_pct"))   if data.get("nivel_pct") is not None else None

        if None in (temperatura, humedad, humedad_suelo, nivel_de_agua):
            logging.warning(f"[ESP32] DATA incompleta, no guardo: {data}")
            return

        agregar_lectura(
            temperatura=temperatura,
            humedad=humedad,
            humedad_suelo=humedad_suelo,
            nivel_de_agua=nivel_de_agua
        )
    except Exception as e:
        logging.exception(f"[ESP32] guardar lectura falló: {e}")

def _open_serial():
    global _serial
    while not _stop:
        try:
            _serial = serial.Serial(SERIAL_PORT, BAUD, timeout=SERIAL_TIMEOUT)
            logging.info(f"[ESP32] Conectado en {SERIAL_PORT}")
            return
        except Exception as e:
            logging.warning(f"[ESP32] No conecta {SERIAL_PORT}: {e} (reintento {RETRY_SEC}s)")
            time.sleep(RETRY_SEC)

def _maybe_save_to_db(data: Dict[str, Any]):
    now = time.time()
    snap.last_data = data
    snap.last_data_ts = now

    if now - snap.last_saved_ts >= DB_PERIOD_SEC:
        _on_save_lectura(data)
        snap.last_saved_ts = now

def _reader_loop():
    global _serial
    buf = ""
    while not _stop:
        if _serial is None or not _serial.is_open:
            _open_serial()
            buf = ""
        try:
            chunk = _serial.read(256).decode(errors="ignore")
            if not chunk:
                continue
            buf += chunk.replace("\r", "\n")
            while "\n" in buf:
                line, _, buf = buf.partition("\n")
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if obj.get("type") == "STATUS":
                    snap.riego = (obj.get("riego") == "ON")
                    snap.vent  = (obj.get("vent")  == "ON")
                    snap.luz   = (obj.get("luz")   == "ON")

                if obj.get("type") == "DATA":
                    if all(k in obj for k in ("suelo_pct", "hum_amb", "temp_c", "nivel_pct")):
                        _maybe_save_to_db(obj)

        except Exception as e:
            logging.warning(f"[ESP32] Serial error: {e}; reabriendo…")
            try:
                _serial.close()
            except:
                pass
            _serial = None
            time.sleep(RETRY_SEC)

def iniciar_lector():
    """Lanza el hilo lector (idempotente). Llamar en startup del servidor."""
    global _reader_th, _stop
    if _reader_th and _reader_th.is_alive():
        return
    _stop = False
    _reader_th = threading.Thread(target=_reader_loop, daemon=True)
    _reader_th.start()
    logging.info("[ESP32] Lector iniciado")

def detener_lector():
    global _stop, _serial
    _stop = True
    try:
        if _serial and _serial.is_open:
            _serial.close()
    except:
        pass

def enviar_cmd(cmd: dict, wait: float = 0.2):
    """Envía un JSON por serie a la ESP (para RIEGO/VENT/LUZ/STATUS)."""
    line = (json.dumps(cmd) + "\n").encode()
    with _write_lock:
        if not _serial or not _serial.is_open:
            raise RuntimeError("Puerto serie no disponible")
        _serial.write(line)
        _serial.flush()
    if cmd.get("cmd") == "SET":
        tgt, val = cmd.get("target"), cmd.get("value")
        on = (val == "ON")
        if tgt == "RIEGO": snap.riego = on
        if tgt == "VENT":  snap.vent  = on
        if tgt == "LUZ":   snap.luz   = on
    time.sleep(wait)

def get_snapshot() -> Dict[str, Any]:
    return {
        "last_data": snap.last_data,
        "last_data_ts": snap.last_data_ts,
        "last_saved_ts": snap.last_saved_ts,
        "riego": snap.riego,
        "vent":  snap.vent,
        "luz":   snap.luz,
        "serial_port": SERIAL_PORT,
    }
