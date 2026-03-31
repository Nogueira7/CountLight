import json
from datetime import datetime
from data_ingestion.logger import logger


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_message(topic, payload):
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        return None

    shelly_id = topic.split("/")[0]
    ts = datetime.utcnow()

    if "params" in data:
        sw = data["params"].get("switch:0", {})
    else:
        sw = data

    power_w = to_float(sw.get("apower"))
    energy_total_wh = (
        to_float((sw.get("aenergy") or {}).get("total"))
        if sw.get("aenergy")
        else None
    )

    energy_kwh = (
        energy_total_wh / 1000 if energy_total_wh is not None else None
    )

    if power_w is None or energy_kwh is None:
        logger.debug("Mensagem ignorada (dados incompletos)")
        return None

    return {
        "shelly_id": shelly_id,
        "recorded_at": ts,
        "power_w": power_w,
        "energy_kwh": energy_kwh,
        "voltage_v": to_float(sw.get("voltage")),
        "current_a": to_float(sw.get("current")),
    }
