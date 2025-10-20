import json, time, threading, logging, os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import serial

SERIAL_PORT = "/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_DC:DA:0C:58:08:84-if00"
BAUD = 115200
SERIAL_TIMEOUT = 1.0
RETRY_SEC = 2

DB_PERIOD_SEC = 60  # persistir 1 vez por minuto

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

_last_esp_id: Optional[str] = None  # se actualiza al recibir HELLO/DATA

def _on_save_lectura(data: Dict[str, Any]) -> None:
    try:
        from app.servicios.funciones import agregar_lectura
        temperatura    = float(data["temp_c"])
        humedad        = float(data["hum_amb"])
        humedad_suelo  = float(data["suelo_pct"])
        nivel_de_agua  = float(data["nivel_pct"])
    except Exception:
        logging.warning(f"[ESP32] DATA incompleta, no guardo: {data}")
        return

    esp_id = data.get("esp_id") or _last_esp_id or os.getenv("DEFAULT_ESP_ID") or "default-esp"

    try:
        agregar_lectura(
            esp_id=esp_id,
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
    global _serial, _last_esp_id
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

                # Capturar ID si viene
                _last_esp_id = obj.get("esp_id") or _last_esp_id
                if "hello" in obj and isinstance(obj["hello"], dict):
                    _last_esp_id = obj["hello"].get("esp_id") or _last_esp_id

                # Estados
                if obj.get("type") == "STATUS":
                    snap.riego = (obj.get("riego") == "ON")
                    snap.vent  = (obj.get("vent")  == "ON")
                    snap.luz   = (obj.get("luz")   == "ON")

                # Datos
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
        "esp_id": _last_esp_id,
    }
