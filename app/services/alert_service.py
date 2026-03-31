from datetime import datetime, timedelta

from app.repositories.device_repository import get_all_user_devices
from app.repositories.energy_repository import (
    get_average_power_last_days,
    get_recent_device_power
)


# =====================================================
# ALERTA — Pico de potência
# =====================================================

def get_peak_power_alert(db, user_id: int, house_id: int):

    threshold = 2500
    days = 7

    devices = get_all_user_devices(db, user_id)

    if not devices:
        return {
            "powerThresholdW": threshold,
            "peakCount": 0,
            "days": days,
            "message": "Não existem dispositivos registados para analisar picos de potência."
        }

    peak_count = 0

    for device in devices:

        power = (
            device.get("power_w")
            or device.get("power")
            or device.get("current_power")
            or 0
        )

        try:
            power = float(power)
        except (TypeError, ValueError):
            power = 0

        if power > threshold:
            peak_count += 1

    if peak_count == 0:
        return {
            "powerThresholdW": threshold,
            "peakCount": 0,
            "days": days,
            "message": (
                f"Não foram detetados picos de potência acima de {threshold}W "
                f"nos últimos {days} dias. O consumo manteve-se estável."
            )
        }

    return {
        "powerThresholdW": threshold,
        "peakCount": peak_count,
        "days": days,
        "message": (
            f"Detetámos picos acima de {threshold}W em {peak_count} ocasiões "
            f"nos últimos {days} dias. Verifique equipamentos como forno, aquecedor "
            f"ou resistências elétricas e considere distribuir os consumos."
        )
    }


# =====================================================
# ALERTA — Consumo fora do padrão
# =====================================================

def get_consumption_pattern_alert(db, user_id: int, house_id: int):

    baseline_days = 30
    analysis_days = 7

    baseline_avg = get_average_power_last_days(
        db,
        house_id,
        baseline_days
    )

    week_avg = get_average_power_last_days(
        db,
        house_id,
        analysis_days
    )

    if not baseline_avg:
        return {
            "percentAboveBaseline": 0,
            "baselineDays": baseline_days,
            "message": "Ainda não existem dados suficientes para analisar o padrão de consumo."
        }

    percent = ((week_avg - baseline_avg) / baseline_avg) * 100
    percent = round(percent)

    if percent <= 10:
        return {
            "percentAboveBaseline": percent,
            "baselineDays": baseline_days,
            "message": (
                f"O consumo desta semana está dentro do padrão normal "
                f"(variação de {percent}% face à média dos últimos {baseline_days} dias)."
            )
        }

    return {
        "percentAboveBaseline": percent,
        "baselineDays": baseline_days,
        "message": (
            f"O consumo desta semana está {percent}% acima da média dos "
            f"últimos {baseline_days} dias. Verifique se algum equipamento "
            f"está ligado durante mais tempo do que o habitual."
        )
    }


# =====================================================
# ALERTA — Aparelho ligado demasiado tempo
# =====================================================

def get_device_on_too_long_alert(db, house_id: int):

    threshold_power = 800
    threshold_minutes = 90

    devices = get_recent_device_power(db, house_id)

    if not devices:
        return {
            "device": None,
            "power": 0,
            "minutes": 0,
            "message": "Não existem dados recentes de dispositivos para analisar."
        }

    for device in devices:

        device_name = device.get("device_name", "Dispositivo")
        avg_power = device.get("avg_power", 0)
        minutes_on = device.get("minutes_on", 0)

        try:
            avg_power = float(avg_power)
        except (TypeError, ValueError):
            avg_power = 0

        if avg_power >= threshold_power and minutes_on >= threshold_minutes:

            return {
                "device": device_name,
                "power": round(avg_power),
                "minutes": minutes_on,
                "message": (
                    f"O dispositivo '{device_name}' está a consumir cerca de "
                    f"{round(avg_power)}W há aproximadamente {minutes_on} minutos. "
                    f"Considere desligá-lo ou automatizar o funcionamento."
                )
            }

    return {
        "device": None,
        "power": 0,
        "minutes": 0,
        "message": (
            "Não foi detetado nenhum dispositivo ligado continuamente "
            "com consumo elevado nas últimas horas."
        )
    }


# =====================================================
# ALERTA — Consumo noturno/anómalo
# =====================================================

def get_night_consumption_alert(db, house_id: int):

    night_start = 0
    night_end = 6
    threshold = 80

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT AVG(er.power_w) AS avg_power
        FROM energy_readings er
        JOIN devices d ON er.id_device = d.id_device
        JOIN rooms r ON d.id_room = r.id_room
        WHERE r.id_house = %s
        AND HOUR(er.recorded_at) BETWEEN %s AND %s
        AND er.recorded_at >= NOW() - INTERVAL 7 DAY
        """,
        (house_id, night_start, night_end)
    )

    row = cursor.fetchone()
    cursor.close()

    avg_power = row["avg_power"] if row and row["avg_power"] else 0

    try:
        avg_power = float(avg_power)
    except (TypeError, ValueError):
        avg_power = 0

    avg_power = round(avg_power)

    if avg_power <= threshold:
        return {
            "nightStart": "00:00",
            "nightEnd": "06:00",
            "avgPower": avg_power,
            "message": (
                f"O consumo médio noturno está dentro do normal "
                f"({avg_power}W entre 00:00 e 06:00)."
            )
        }

    return {
        "nightStart": "00:00",
        "nightEnd": "06:00",
        "avgPower": avg_power,
        "message": (
            f"O consumo médio noturno foi de {avg_power}W entre 00:00 e 06:00, "
            f"acima do valor esperado. Isto pode indicar equipamentos em standby "
            f"com consumo elevado ou algum aparelho esquecido ligado."
        )
    }


# =====================================================
# ALERTA — Qualidade de dados / dispositivo offline
# =====================================================

def get_data_quality_alert(db, house_id: int):

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT MAX(er.recorded_at) AS last_data
        FROM energy_readings er
        JOIN devices d ON er.id_device = d.id_device
        JOIN rooms r ON d.id_room = r.id_room
        WHERE r.id_house = %s
        """,
        (house_id,)
    )

    row = cursor.fetchone()
    cursor.close()

    last_data = row["last_data"] if row else None

    if not last_data:
        return {
            "message": "Ainda não existem dados energéticos registados para esta casa."
        }

    now = datetime.utcnow()
    diff = now - last_data

    minutes_without_data = int(diff.total_seconds() / 60)

    if minutes_without_data > 15:
        return {
            "minutesWithoutData": minutes_without_data,
            "message": (
                f"O dispositivo deixou de enviar dados há {minutes_without_data} minutos. "
                f"Verifique a ligação Wi-Fi ou se o Shelly está ligado."
            )
        }

    return {
        "minutesWithoutData": minutes_without_data,
        "message": "Os dados do dispositivo estão a ser recebidos normalmente."
    }