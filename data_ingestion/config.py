import os
from dotenv import load_dotenv

load_dotenv()

# MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPICS = ["+/events/rpc", "+/status/switch:0"]

# DB
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

# intervalo mínimo entre inserções (segundos)
INSERT_INTERVAL = int(os.getenv("INSERT_INTERVAL", 120))
