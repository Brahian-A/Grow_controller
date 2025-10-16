# app/conexiones/conexion_esp32.py
import os

ESP32_ENABLED = os.getenv("ESP32_ENABLED", "true").lower() == "true"

def obtener_conexion(port="/dev/ttyUSB0", baudrate=115200, timeout=1):
    if not ESP32_ENABLED:
        raise RuntimeError("ESP32_ENABLED=false: conexión serie deshabilitada")
    try:
        import serial  # import perezoso: no rompe si pyserial no está instalado hasta que realmente lo llames
    except Exception as e:
        raise RuntimeError("pyserial no está instalado: pip install pyserial") from e
    return serial.Serial(port, baudrate, timeout=timeout)

def leer_linea(ser):
    """Lee una línea del puerto serie, devuelve str o None si timeout."""
    if ser is None:
        return None
    try:
        raw = ser.readline()
        if not raw:
            return None
        return raw.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None
