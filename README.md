# Grow Controller

[](https://opensource.org/licenses/MIT)
[](https://www.python.org/)
[](https://fastapi.tiangolo.com/)
[](https://www.eclipse.org/paho/)

Una plataforma full-stack de código abierto para monitorear y automatizar invernaderos, con configuración asistida por IA de Google Gemini.

Este repositorio contiene el **software del servidor** (Backend FastAPI, Frontend JS y listener MQTT) diseñado para ejecutarse en un host (como una Raspberry Pi o un VPS) y gestionar uno o más dispositivos de hardware (ESP32).


## 🎯 El Problema

Gestionar un invernadero, ya sea pequeño o mediano, requiere un monitoreo constante de las condiciones ambientales. Mantener manualmente la temperatura, la humedad del suelo y la luz es ineficiente y propenso a errores. Las soluciones comerciales suelen ser caras y de "caja negra", sin flexibilidad.

## ✨ La Solución

**Grow Controller** es una plataforma modular que te da control total sobre tu invernadero.

1.  **Hardware (ESP32):** Un dispositivo de bajo costo en tu invernadero lee los sensores y controla los actuadores (luces, bomba de riego, ventilador).
2.  **Servidor (Este Repo):** Un servidor central recibe los datos del ESP32 vía MQTT, los almacena en una base de datos, te presenta un dashboard en tiempo real y utiliza **IA (Gemini)** para aplicar configuraciones óptimas.

-----

## 🚀 Características Principales

  * **Dashboard en Tiempo Real:** Visualiza la temperatura, humedad ambiente, humedad del suelo y nivel de agua al instante.
  * **🤖 Autoconfiguración con IA:** ¿No sabes las condiciones óptimas para tus tomates? Pregúntale a la IA. El sistema consulta la API de Gemini y aplica los umbrales de temperatura y humedad automáticamente.
  * **Control de Actuadores:** Enciende o apaga la bomba de riego, la ventilación o las luces manualmente desde el dashboard.
  * **Arquitectura Modular (MQTT):** Conecta múltiples dispositivos ESP32 a un solo servidor. La comunicación es ligera y en tiempo real usando MQTT.
  * **Historial y Exportación de Datos:** Revisa gráficos históricos de los últimos 7 días y exporta rangos de fechas personalizados a CSV.
  * **Host con Portal Cautivo (Modo Configuración):** Diseñado para hosts Linux (como Raspberry Pi). Si no detecta una red Wi-Fi, crea su propio Hotspot (`GrowController`) y sirve un portal para que puedas configurar las credenciales de tu Wi-Fi desde el móvil.

-----

## 🏗️ Arquitectura del Sistema

El sistema se divide en dos componentes principales que se comunican vía MQTT.

PlaceHolder para diagrama de arquitectura.

-----

## 🛠️ Stack Tecnológico

| Área | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ | Lenguaje principal |
| | FastAPI | API web asíncrona de alto rendimiento |
| | SQLAlchemy | ORM para la base de datos |
| | Uvicorn | Servidor ASGI para FastAPI |
| **Frontend** | Vanilla JavaScript (ESM) | Lógica del dashboard y llamadas API |
| | HTML5 / CSS3 | Estructura y estilos |
| **Comunicación** | Paho-MQTT | Cliente MQTT para Python (listener y publicador) |
| | Mosquitto | Broker MQTT |
| **Base de Datos** | SQLAlchemy | Almacenamiento de lecturas y configuraciones |
| **IA** | Google Gemini | Generación de umbrales óptimos de cultivo |
| **Host** | Linux (Raspberry Pi) | El `start.sh` incluye `hostapd` y `dnsmasq` para el modo portal |

-----

## 🔌 Interfaz MQTT (El Contrato del Hardware)

Tu ESP32 debe comunicarse usando los siguientes tópicos y formatos JSON. Reemplaza `{esp_id}` por el ID único de tu dispositivo.

### 1\. ESP32 al Servidor (Telemetría)

El ESP32 debe publicar un JSON con *todas* las lecturas en este tópico.

  * **Tópico:** `invernaderos/{esp_id}/telemetria`
  * **Payload Ejemplo:**
    ```json
    {
      "temp_c": 24.5,
      "hum_amb": 60.1,
      "suelo_pct": 55.0,
      "nivel_pct": 80.0,
      "riego": "OFF",
      "vent": "ON",
      "luz": "OFF"
    }
    ```

### 2\. ESP32 al Servidor (Status Online)

Se recomienda que el ESP32 publique un mensaje (preferiblemente retenido) para indicar que está online.

  * **Tópico:** `invernaderos/{esp_id}/status`
  * **Payload Ejemplo:** `"online"`

### 3\. Servidor al ESP32 (Comandos)

El ESP32 debe suscribirse a este tópico para recibir comandos desde el dashboard.

  * **Tópico:** `invernaderos/{esp_id}/cmd`
  * **Payload Ejemplo:**
    ```json
    // Para encender el riego
    {"cmd": "SET", "target": "RIEGO", "value": "ON"}

    // Para solicitar un reporte de estado
    {"cmd": "STATUS"}

    // Para reiniciar el dispositivo
    {"cmd": "REBOOT"}
    ```

-----

## 🤝 Cómo Contribuir

¡Estamos abiertos a contribuciones de la comunidad! Si quieres ayudar a mejorar Grow Controller, ¡eres bienvenido!

Ya sea que encuentres un error (bug), tengas una idea para una nueva característica o quieras mejorar la documentación, tu ayuda es valiosa.

1.  **Forkea** el repositorio.
2.  Crea una nueva rama (`git checkout -b feature/MiMejora`).
3.  Haz tus cambios.
4.  Haz un **Pull Request** explicando qué hace tu cambio.

Para contribuciones más grandes, por favor abre un **Issue** primero para que podamos discutir la idea.

## 🚀 Instalación y Puesta en Marcha

Este servidor está diseñado para correr en un host Linux (ej. Raspberry Pi) que tenga acceso a Python y a un broker MQTT.

### Requisitos Previos

  * Python 3.10+
  * `git`
  * Un broker MQTT (como Mosquitto) corriendo en `localhost:1883`.
  * Una clave de API de Google Gemini.

### Pasos de Instalación

1.  **Clonar el repositorio:**

    ```bash
    git clone https://github.com/Brahian-A/Grow_controller.git
    cd Grow_controller
    ```

2.  **Crear y activar un entorno virtual:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar variables de entorno:**
    Crea un archivo `.env` en la raíz del proyecto (mira el `.gitignore`).

    ```ini
    # Archivo .env
    # Clave de API para la autoconfiguración de plantas
    GEMINI_API_KEY="AIzaSy...tu_clave_aqui"

    # (Opcional) ID de dispositivo por defecto si la API no recibe uno
    DEFAULT_ESP_ID="default-esp"
    ```

5.  **Iniciar el servidor:**
    Puedes usar `run.py` (que usa Uvicorn) o el script `start.sh` si estás en un host tipo Pi.

      * **Modo simple (desarrollo):**

        ```bash
        python run.py
        ```

      * **Modo Producción (con portal cautivo en Linux):**
        El script `start.sh` gestionará el modo de configuración automáticamente.

        ```bash
        chmod +x start.sh
        sudo ./start.sh
        ```

6.  **Acceder a la aplicación:**
    Abre tu navegador y ve a `http://<ip_del_servidor>:8000`.

-----

## 👥 Sobre el Equipo

Este proyecto fue diseñado y construido por un equipo multidisciplinario de 4 profesionales:

  * **Bruno Dos Santos:** Q\&A Engineer / Backend Developer
  * **Brahian Amaral:** Hardware Engineer / Backend Developer
  * **Agustín Lahalo:** Full Stack Developer
  * **Juan Diego Aedo:** Frontend Developer