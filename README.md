- **`platformio.ini`** → Define la placa, framework, dependencias y opciones de compilación.  
- **`partitions.csv`** → Permite manejar particiones personalizadas de memoria (firmware, LittleFS, OTA).  
- **`include/secrets.h.example`** → Ejemplo de archivo de credenciales WiFi (`WIFI_SSID` y `WIFI_PASS`).  
- **`src/`** → Lógica principal del firmware:
  - `main.cpp` → inicialización y bucle principal.  
  - `sensors/` → drivers para sensores (ej. AHT20 y humedad de suelo).  
  - `control/` → controladores de actuadores (ej. bomba de agua).  
  - `api/` → API REST con rutas y configuración.  
- **`data/`** → Archivos para la interfaz web servida desde el ESP32 con LittleFS.  
- **`test/`** → Pruebas unitarias con Unity (ejecutables desde PlatformIO).  
- **`tools/`** → Utilidades o scripts auxiliares.  
- **`postman_collection.json`** → Conjunto de pruebas de API para Postman.  

Comandos útiles

Compilar: pio run

Subir: pio run -t upload

Monitor serie: pio device monitor

Subir UI a LittleFS: pio run -t uploadfs