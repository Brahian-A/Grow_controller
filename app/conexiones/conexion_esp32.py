import json, time, threading, serial
from app.servicios.funciones import agregar_lectura

PUERTO = "/dev/ttyACM0"
BAUDIOS = 115200
GUARDAR_CADA = 60

class ConexionESP32:
    def __init__(self):
        self.serial = None
        self.buffer = bytearray()
        self.bomba = False
        self.ventilador = False
        self.lamparita = False
        self.nivel_agua = 0
        self.ultima = None
        self.ultimo_guardado = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def _abrir_serial(self):
        while True:
            try:
                self.serial = serial.Serial(PUERTO, BAUDIOS, timeout=0.2)
                return
            except:
                time.sleep(2)

    def _loop(self):
        self._abrir_serial()
        while True:
            if not self.serial or not self.serial.is_open:
                self._abrir_serial()
                self.buffer.clear()
                continue
            datos = self.serial.read(256)
            if not datos:
                continue
            for b in datos:
                if b in (10, 13):  # salto de línea
                    if self.buffer:
                        try:
                            obj = json.loads(self.buffer.decode().strip())
                            self._procesar(obj)
                        except:
                            pass
                        self.buffer.clear()
                else:
                    if len(self.buffer) < 512:
                        self.buffer.append(b)
                    else:
                        self.buffer.clear()

    def _procesar(self, obj):
        t = obj.get("type")
        if t == "DATA":
            self._actualizar(obj)
        elif t == "STATUS":
            self.bomba = obj.get("riego") == "ON"
            self.ventilador = obj.get("vent") == "ON"
            self.lamparita = obj.get("luz") == "ON"
        elif obj.get("ack"):
            a = obj["ack"]
            s = obj.get("state") == "ON"
            if a == "RIEGO": self.bomba = s
            if a == "VENT": self.ventilador = s
            if a == "LUZ": self.lamparita = s

    def _actualizar(self, obj):
        temp = float(obj.get("temp_c", 0))
        hum = float(obj.get("hum_amb", 0))
        suelo = float(obj.get("suelo_pct", 0))
        nivel = int(float(obj.get("nivel_pct", 0)))
        self.nivel_agua = max(0, min(100, nivel))
        self.ultima = dict(
            temperatura=max(0, min(45, temp)),
            humedad=max(0, min(100, hum)),
            humedad_suelo=max(0, min(100, suelo)),
            nivel_de_agua=self.nivel_agua
        )
        if time.time() - self.ultimo_guardado >= GUARDAR_CADA:
            agregar_lectura(**self.ultima)
            self.ultimo_guardado = time.time()

    def _enviar(self, cmd, target, value=None):
        if not self.serial or not self.serial.is_open:
            self._abrir_serial()
        data = {"cmd": cmd, "target": target}
        if value is not None: data["value"] = value
        self.serial.write((json.dumps(data) + "\n").encode())

    def set_bomba(self, on):      self._enviar("SET", "RIEGO", "ON" if on else "OFF")
    def set_ventilador(self, on): self._enviar("SET", "VENT",  "ON" if on else "OFF")
    def set_lamparita(self, on):  self._enviar("SET", "LUZ",   "ON" if on else "OFF")
    def pedir_status(self):       self._enviar("STATUS", "")

    def snapshot(self):
        return {
            "bomba": self.bomba,
            "ventilador": self.ventilador,
            "lamparita": self.lamparita,
            "nivel_agua": self.nivel_agua
        }

conexion_esp32 = ConexionESP32()
def obtener_conexion(): return conexion_esp32
