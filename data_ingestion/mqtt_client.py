import time
import paho.mqtt.client as mqtt
from data_ingestion.config import MQTT_BROKER, MQTT_PORT, MQTT_TOPICS, INSERT_INTERVAL
from data_ingestion.logger import logger
from data_ingestion.parser import parse_message
from data_ingestion.mysql_repository import get_device_id, insert_energy_reading
from data_ingestion.database import get_db_conn

_last_insert_time = 0


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT conectado")
        for topic in MQTT_TOPICS:
            client.subscribe(topic)
            logger.info(f"Subscrito a {topic}")
    else:
        logger.error(f"Falha MQTT (rc={rc})")


def on_message(client, userdata, msg):
    global _last_insert_time

    if time.time() - _last_insert_time < INSERT_INTERVAL:
        return

    parsed = parse_message(msg.topic, msg.payload)
    if not parsed:
        return

    device_id = get_device_id(parsed["shelly_id"])
    if not device_id:
        return

    insert_energy_reading(device_id, parsed)
    _last_insert_time = time.time()


def start():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    try:
        client.loop_forever()

    except KeyboardInterrupt:
        logger.info("Serviço de ingestão parado manualmente")

    finally:
        client.disconnect()
        logger.info("MQTT desligado")


