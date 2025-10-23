import json
import paho.mqtt.client as mqtt
from app.db.session import SessionLocal
from app.db.models import Lectura

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print("MQTT mensaje:", data)

    db = SessionLocal()
    lectura = Lectura(
        temperatura=data.get("temp_c"),
        humedad=data.get("hum_amb"),
        humedad_suelo=data.get("suelo_pct"),
        nivel_de_agua=data.get("nivel_pct"),
    )
    db.add(lectura)
    db.commit()
    db.close()

def start_mqtt_listener():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("localhost", 1883)
    client.subscribe("invernadero/lecturas")
    client.loop_start()
