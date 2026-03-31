import mysql.connector
from data_ingestion.config import DB_CONFIG
from data_ingestion.logger import logger

_conn = None
_device_cache = {}


def get_db_conn():
    global _conn
    if _conn is None or not _conn.is_connected():
        _conn = mysql.connector.connect(**DB_CONFIG)
        logger.info("MySQL ligado")
    return _conn


def get_device_id(shelly_id: str):
    if shelly_id in _device_cache:
        return _device_cache[shelly_id]

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id_device FROM devices WHERE shelly_id=%s AND is_active=1",
        (shelly_id,),
    )
    row = cur.fetchone()
    cur.close()

    device_id = row[0] if row else None
    _device_cache[shelly_id] = device_id

    if device_id is None:
        logger.warning(f"Shelly {shelly_id} não existe em devices")

    return device_id


def insert_energy_reading(device_id, data: dict):
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO energy_readings
        (id_device, power_w, energy_kwh, voltage_v, current_a, recorded_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            device_id,
            data["power_w"],
            data["energy_kwh"],
            data["voltage_v"],
            data["current_a"],
            data["recorded_at"],
        ),
    )

    conn.commit()
    cur.close()
    logger.info(f"Leitura gravada (device {device_id})")
