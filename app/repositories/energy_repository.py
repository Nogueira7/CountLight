# backend/app/repositories/energy_repository.py
from __future__ import annotations
import calendar
from datetime import date


from typing import Literal



# GET — leituras por device

def get_energy_by_device(
    db,
    id_device: int,
    limit: int | None = None,
):
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            id_energy_reading,
            id_device,
            power_w,
            energy_kwh,
            voltage_v,
            current_a,
            recorded_at
        FROM energy_readings
        WHERE id_device = %s
        ORDER BY recorded_at DESC
    """

    params = [id_device]

    if limit:
        sql += " LIMIT %s"
        params.append(limit)

    cursor.execute(sql, tuple(params))
    readings = cursor.fetchall()
    cursor.close()

    return readings



# GET — última leitura de um device

def get_latest_energy_by_device(
    db,
    id_device: int,
):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id_energy_reading,
            id_device,
            power_w,
            energy_kwh,
            voltage_v,
            current_a,
            recorded_at
        FROM energy_readings
        WHERE id_device = %s
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        (id_device,),
    )

    reading = cursor.fetchone()
    cursor.close()

    return reading



# GET — leituras por divisão

def get_energy_by_room(
    db,
    id_room: int,
    user_id: int,
):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            er.id_energy_reading,
            er.id_device,
            d.name AS device_name,
            er.power_w,
            er.energy_kwh,
            er.voltage_v,
            er.current_a,
            er.recorded_at
        FROM energy_readings er
        INNER JOIN devices d ON d.id_device = er.id_device
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE r.id_room = %s
          AND h.id_user = %s
        ORDER BY er.recorded_at DESC
        """,
        (id_room, user_id),
    )

    readings = cursor.fetchall()
    cursor.close()

    return readings



# DASHBOARD — consumo por divisão (MÊS ATUAL), (MAX(energy_kwh)-MIN(energy_kwh) por device dentro do mês, somado por divisão)

def get_energy_summary_by_room(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            r.name AS label,
            COALESCE(SUM(t.consumed_kwh), 0) AS value
        FROM rooms r
        INNER JOIN houses h ON h.id_house = r.id_house
        LEFT JOIN devices d ON d.id_room = r.id_room

        LEFT JOIN (
            SELECT
                id_device,
                (MAX(energy_kwh) - MIN(energy_kwh)) AS consumed_kwh
            FROM energy_readings
            WHERE recorded_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
              AND recorded_at <  DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 1 MONTH)
            GROUP BY id_device
        ) t ON t.id_device = d.id_device

        WHERE h.id_user = %s
        GROUP BY r.id_room
        ORDER BY r.name ASC
        """,
        (user_id,),
    )

    data = cursor.fetchall()
    cursor.close()

    has_data = any(float(item["value"] or 0) > 0 for item in data)

    return {"data": data, "has_data": has_data}



# DASHBOARD — consumo por tipo

def get_energy_summary_by_device_type(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.device_type AS label,
            COALESCE(SUM(t.consumed_kwh), 0) AS value
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house

        LEFT JOIN (
            SELECT
                id_device,
                (MAX(energy_kwh) - MIN(energy_kwh)) AS consumed_kwh
            FROM energy_readings
            WHERE recorded_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
              AND recorded_at <  DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 1 MONTH)
            GROUP BY id_device
        ) t ON t.id_device = d.id_device

        WHERE h.id_user = %s
        GROUP BY d.device_type
        ORDER BY d.device_type ASC
        """,
        (user_id,),
    )

    data = cursor.fetchall()
    cursor.close()
    return data



# DASHBOARD — consumo por dispositivo

def get_energy_summary_by_device(
    db,
    user_id: int,
):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.name AS label,
            COALESCE(
                MAX(er.energy_kwh) - MIN(er.energy_kwh),
                0
            ) AS value
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        LEFT JOIN energy_readings er
            ON er.id_device = d.id_device
            AND DATE(er.recorded_at) = CURDATE()
        WHERE h.id_user = %s
        GROUP BY d.id_device
        ORDER BY d.name ASC
        """,
        (user_id,),
    )

    data = cursor.fetchall()
    cursor.close()

    return data



# DASHBOARD — consumo total por periodo

def get_total_consumption_for_period(
    db, user_id: int, period: Literal["today", "month", "year"]
):
    cursor = db.cursor(dictionary=True)

    if period == "today":
        date_filter = "DATE(er.recorded_at) = CURDATE()"

    elif period == "month":
        date_filter = """
            er.recorded_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
            AND er.recorded_at < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 1 MONTH)
        """

    elif period == "year":
        date_filter = "YEAR(er.recorded_at) = YEAR(CURDATE())"

    else:
        cursor.close()
        return 0.0

    cursor.execute(
        f"""
        SELECT
            COALESCE(SUM(device_consumption), 0) AS total_kwh
        FROM (
            SELECT
                d.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            INNER JOIN energy_readings er ON er.id_device = d.id_device
            WHERE h.id_user = %s
              AND {date_filter}
            GROUP BY d.id_device
        ) t
        """,
        (user_id,),
    )

    result = cursor.fetchone()
    cursor.close()

    return float(result["total_kwh"] or 0)


def get_estimated_month_cost(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    month_kwh = get_total_consumption_for_period(db, user_id, "month")

    cursor.execute(
        """
        SELECT price_per_kwh
        FROM houses
        WHERE id_user = %s
          AND is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )

    house = cursor.fetchone()
    cursor.close()

    if not house or not house.get("price_per_kwh"):
        return 0

    return round(month_kwh * float(house["price_per_kwh"]), 2)



def get_daily_consumption_in_month(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            day_label,
            SUM(consumed_kwh) AS value
        FROM (
            SELECT
                DAY(er.recorded_at) AS day_label,
                d.id_device,
                (MAX(er.energy_kwh) - MIN(er.energy_kwh)) AS consumed_kwh
            FROM energy_readings er
            INNER JOIN devices d ON d.id_device = er.id_device
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            
            WHERE h.id_user = %s
              AND YEAR(er.recorded_at) = YEAR(CURDATE())
              AND MONTH(er.recorded_at) = MONTH(CURDATE())
            
            GROUP BY DAY(er.recorded_at), d.id_device
        ) daily_per_device
        GROUP BY day_label
        ORDER BY day_label ASC
        """,
        (user_id,),
    )

    rows = cursor.fetchall()
    cursor.close()

    # Dias do mês atual
    cursor2 = db.cursor(dictionary=True)
    cursor2.execute("SELECT DAY(LAST_DAY(CURDATE())) AS days_in_month")
    dim = int(cursor2.fetchone()["days_in_month"])
    cursor2.close()

    # Agrupar por dia
    by_day = {int(r["day_label"]): float(r["value"] or 0) for r in rows}

    data = [
        {"label": str(day), "value": round(by_day.get(day, 0.0), 3)}
        for day in range(1, dim + 1)
    ]

    has_data = any(d["value"] > 0 for d in data)

    return {"data": data, "has_data": has_data}



def get_hourly_consumption_today(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            HOUR(curr.recorded_at) AS hour_label,
            SUM(curr.energy_kwh - prev.energy_kwh) AS value
        FROM energy_readings curr

        INNER JOIN energy_readings prev
            ON prev.id_device = curr.id_device
           AND prev.recorded_at = (
                SELECT MAX(p2.recorded_at)
                FROM energy_readings p2
                WHERE p2.id_device = curr.id_device
                  AND p2.recorded_at < curr.recorded_at
           )

        INNER JOIN devices d ON d.id_device = curr.id_device
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house

        WHERE h.id_user = %s
          AND DATE(curr.recorded_at) = (
                SELECT MAX(DATE(er2.recorded_at))
                FROM energy_readings er2
                INNER JOIN devices d2 ON d2.id_device = er2.id_device
                INNER JOIN rooms r2 ON r2.id_room = d2.id_room
                INNER JOIN houses h2 ON h2.id_house = r2.id_house
                WHERE h2.id_user = %s
          )
          -- 🔥 IMPORTANTE: evitar deltas absurdos
          AND curr.energy_kwh >= prev.energy_kwh
          AND (curr.energy_kwh - prev.energy_kwh) < 50

        GROUP BY HOUR(curr.recorded_at)
        ORDER BY hour_label ASC
        """,
        (user_id, user_id),
    )

    rows = cursor.fetchall()
    cursor.close()

    by_hour = {int(r["hour_label"]): float(r["value"] or 0) for r in rows}

    data = [
        {"label": f"{h:02d}:00", "value": round(by_hour.get(h, 0.0), 3)}
        for h in range(24)
    ]

    has_data = any(d["value"] > 0 for d in data)

    return {"data": data, "has_data": has_data}




def get_daily_consumption_month_comparison(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    # -------------------------------------------------
    # 📅 Datas importantes
    # -------------------------------------------------
    today = date.today()

    current_year = today.year
    current_month = today.month

    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_year = current_year

    days_current_month = calendar.monthrange(current_year, current_month)[1]
    days_previous_month = calendar.monthrange(previous_year, previous_month)[1]


    cursor.execute(
        """
        SELECT MAX(DATE(er.recorded_at)) as last_date
        FROM energy_readings er
        INNER JOIN devices d ON d.id_device = er.id_device
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE h.id_user = %s
          AND YEAR(er.recorded_at) = %s
          AND MONTH(er.recorded_at) = %s
        """,
        (user_id, current_year, current_month),
    )

    last_result = cursor.fetchone()
    last_day_with_data = (
        last_result["last_date"].day if last_result and last_result["last_date"] else 0
    )


    cursor.execute(
        """
        WITH daily AS (
            SELECT
                DATE(er.recorded_at) AS day_date,
                DAY(er.recorded_at)  AS day_label,
                d.id_device,
                (MAX(er.energy_kwh) - MIN(er.energy_kwh)) AS consumed_kwh
            FROM energy_readings er
            INNER JOIN devices d ON d.id_device = er.id_device
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            WHERE h.id_user = %s
              AND (
                    (YEAR(er.recorded_at) = %s AND MONTH(er.recorded_at) = %s)
                 OR (YEAR(er.recorded_at) = %s AND MONTH(er.recorded_at) = %s)
              )
            GROUP BY DATE(er.recorded_at), DAY(er.recorded_at), d.id_device
        )
        SELECT
            YEAR(day_date) as y,
            MONTH(day_date) as m,
            day_label,
            SUM(consumed_kwh) AS value
        FROM daily
        GROUP BY y, m, day_label
        ORDER BY day_label ASC
        """,
        (user_id, current_year, current_month, previous_year, previous_month),
    )

    rows = cursor.fetchall()
    cursor.close()


    current_map = {}
    previous_map = {}

    for r in rows:
        day = int(r["day_label"])
        value = float(r["value"] or 0)

        if r["y"] == current_year and r["m"] == current_month:
            current_map[day] = value
        elif r["y"] == previous_year and r["m"] == previous_month:
            previous_map[day] = value




    labels = [str(d) for d in range(1, days_current_month + 1)]


    previous_data = [
        round(previous_map.get(d, 0.0), 3) if d <= days_previous_month else None
        for d in range(1, days_current_month + 1)
    ]


    current_data = []
    for d in range(1, days_current_month + 1):
        if d <= last_day_with_data:
            current_data.append(round(current_map.get(d, 0.0), 3))
        else:
            current_data.append(None)  # 👈 evita barras falsas

    has_data = any(v for v in (current_data + previous_data) if v not in (0, None))

    return {
        "labels": labels,
        "current_month": current_data,
        "previous_month": previous_data,
        "has_data": has_data,
    }


def get_room_consumption_today(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            r.name AS label,
            COALESCE(
                SUM(t.device_consumption),
                0
            ) AS value
        FROM rooms r
        INNER JOIN houses h ON h.id_house = r.id_house
        LEFT JOIN devices d ON d.id_room = r.id_room

        LEFT JOIN (
            SELECT
                er.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM energy_readings er
            WHERE DATE(er.recorded_at) = CURDATE()
            GROUP BY er.id_device
        ) t ON t.id_device = d.id_device

        WHERE h.id_user = %s
        GROUP BY r.id_room
        ORDER BY r.name ASC
        """,
        (user_id,),
    )

    data = cursor.fetchall()
    cursor.close()

    has_data = any(float(item["value"] or 0) > 0 for item in data)

    return {"data": data, "has_data": has_data}


# consumo total para data específica

def get_total_consumption_for_date(db, user_id: int, target_date):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(device_consumption), 0) AS total_kwh
        FROM (
            SELECT
                d.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            INNER JOIN energy_readings er ON er.id_device = d.id_device
            WHERE h.id_user = %s
              AND DATE(er.recorded_at) = %s
            GROUP BY d.id_device
        ) t
        """,
        (user_id, target_date),
    )

    result = cursor.fetchone()
    cursor.close()

    return float(result["total_kwh"] or 0)


# consumo total mês anterior

def get_total_consumption_previous_month(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(device_consumption), 0) AS total_kwh
        FROM (
            SELECT
                d.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            INNER JOIN energy_readings er ON er.id_device = d.id_device
            WHERE h.id_user = %s
              AND YEAR(er.recorded_at) = YEAR(CURDATE() - INTERVAL 1 MONTH)
              AND MONTH(er.recorded_at) = MONTH(CURDATE() - INTERVAL 1 MONTH)
            GROUP BY d.id_device
        ) t
        """,
        (user_id,),
    )

    result = cursor.fetchone()
    cursor.close()

    return float(result["total_kwh"] or 0)


# obter preço por kWh da casa ativa

def get_price_per_kwh(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT price_per_kwh
        FROM houses
        WHERE id_user = %s
          AND is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )

    house = cursor.fetchone()
    cursor.close()

    if not house or not house.get("price_per_kwh"):
        return 0.0

    return float(house["price_per_kwh"])


# consumo por dispositivo (HOJE)

def get_device_consumption_today(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.name AS label,
            COALESCE(
                MAX(er.energy_kwh) - MIN(er.energy_kwh),
                0
            ) AS value
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        LEFT JOIN energy_readings er
            ON er.id_device = d.id_device
            AND DATE(er.recorded_at) = CURDATE()
        WHERE h.id_user = %s
        GROUP BY d.id_device
        ORDER BY value DESC
        """,
        (user_id,),
    )

    data = cursor.fetchall()
    cursor.close()

    return data


# média horária últimos 7 dias

def get_hourly_average_last_7_days(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            HOUR(er.recorded_at) AS hour_label,
            AVG(device_consumption) AS avg_value
        FROM (
            SELECT
                er.id_device,
                er.recorded_at,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM energy_readings er
            INNER JOIN devices d ON d.id_device = er.id_device
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            WHERE h.id_user = %s
              AND er.recorded_at >= CURDATE() - INTERVAL 7 DAY
            GROUP BY DATE(er.recorded_at), HOUR(er.recorded_at), er.id_device
        ) t
        GROUP BY hour_label
        ORDER BY hour_label ASC
        """,
        (user_id,),
    )

    rows = cursor.fetchall()
    cursor.close()

    return {
        int(r["hour_label"]): float(r["avg_value"] or 0)
        for r in rows
    }


# consumo total por período

def get_room_total_consumption_for_period(
    db,
    user_id: int,
    id_room: int,
    period: Literal["today", "month", "year"]
):
    cursor = db.cursor(dictionary=True)

    if period == "today":
        date_filter = "DATE(er.recorded_at) = CURDATE()"

    elif period == "month":
        date_filter = """
            er.recorded_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
            AND er.recorded_at < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 1 MONTH)
        """

    elif period == "year":
        date_filter = "YEAR(er.recorded_at) = YEAR(CURDATE())"

    else:
        cursor.close()
        return 0.0

    cursor.execute(
        f"""
        SELECT
            COALESCE(SUM(device_consumption), 0) AS total_kwh
        FROM (
            SELECT
                d.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            INNER JOIN energy_readings er ON er.id_device = d.id_device
            WHERE h.id_user = %s
              AND r.id_room = %s
              AND {date_filter}
            GROUP BY d.id_device
        ) t
        """,
        (user_id, id_room),
    )

    result = cursor.fetchone()
    cursor.close()

    return float(result["total_kwh"] or 0)


# custo estimado mês atual 

def get_room_estimated_month_cost(
    db,
    user_id: int,
    id_room: int,
):
    cursor = db.cursor(dictionary=True)

    # consumo da divisão no mês
    month_kwh = get_room_total_consumption_for_period(
        db,
        user_id,
        id_room,
        "month"
    )

    # preço da casa ativa
    cursor.execute(
        """
        SELECT price_per_kwh
        FROM houses
        WHERE id_user = %s
          AND is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )

    house = cursor.fetchone()
    cursor.close()

    if not house or not house.get("price_per_kwh"):
        return 0

    return round(month_kwh * float(house["price_per_kwh"]), 2)

def get_room_consumption_by_device_type(db, id_room: int):
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT 
            COALESCE(d.device_type, 'Outros') AS label,
            COALESCE(SUM(t.consumed_kwh), 0) AS value
        FROM devices d
        LEFT JOIN (
            SELECT 
                id_device,
                (MAX(energy_kwh) - MIN(energy_kwh)) AS consumed_kwh
            FROM energy_readings
            WHERE recorded_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
              AND recorded_at < DATE_ADD(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL 1 MONTH)
            GROUP BY id_device
        ) t ON t.id_device = d.id_device
        WHERE d.id_room = %s
        GROUP BY d.device_type
        ORDER BY value DESC
    """
    
    cursor.execute(sql, (id_room,))
    data = cursor.fetchall()
    cursor.close()

    return [
        {"label": row["label"], "value": round(float(row["value"]), 2)}
        for row in data
    ]

from datetime import datetime

def get_room_monthly_comparison(db, user_id: int, id_room: int):
    cursor = db.cursor()

    now = datetime.now()
    current_month = now.month
    current_year = now.year

    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_year = current_year

    # 🔢 Mês atual
    cursor.execute("""
        SELECT COALESCE(SUM(er.energy_kwh), 0)
        FROM energy_readings er
        INNER JOIN devices d ON d.id_device = er.id_device
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE r.id_room = %s
          AND h.id_user = %s
          AND MONTH(er.recorded_at) = %s
          AND YEAR(er.recorded_at) = %s
    """, (id_room, user_id, current_month, current_year))

    current_total = cursor.fetchone()[0]

    # 🔢 Mês anterior
    cursor.execute("""
        SELECT COALESCE(SUM(er.energy_kwh), 0)
        FROM energy_readings er
        INNER JOIN devices d ON d.id_device = er.id_device
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE r.id_room = %s
          AND h.id_user = %s
          AND MONTH(er.recorded_at) = %s
          AND YEAR(er.recorded_at) = %s
    """, (id_room, user_id, previous_month, previous_year))

    previous_total = cursor.fetchone()[0]

    cursor.close()

    if previous_total == 0:
        return 0

    variation = ((current_total - previous_total) / previous_total) * 100

    return round(variation, 2)



# ALERTS SUPPORT


def get_average_power_last_days(
    db,
    house_id: int,
    days: int
):
    cursor = db.cursor()

    cursor.execute(
        """
        SELECT AVG(er.power_w)
        FROM energy_readings er
        JOIN devices d ON er.id_device = d.id_device
        JOIN rooms r ON d.id_room = r.id_room
        WHERE r.id_house = %s
          AND er.recorded_at >= NOW() - INTERVAL %s DAY
        """,
        (house_id, days),
    )

    result = cursor.fetchone()
    cursor.close()

    if not result or result[0] is None:
        return 0

    return float(result[0])


# ALERTS — detectar dispositivos ligados há muito tempo

def get_recent_device_power(db, house_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.name AS device_name,
            AVG(er.power_w) AS avg_power,
            TIMESTAMPDIFF(
                MINUTE,
                MIN(er.recorded_at),
                MAX(er.recorded_at)
            ) AS minutes_on
        FROM energy_readings er
        JOIN devices d ON er.id_device = d.id_device
        JOIN rooms r ON d.id_room = r.id_room
        WHERE r.id_house = %s
          AND er.recorded_at >= NOW() - INTERVAL 2 HOUR
        GROUP BY d.id_device
        """,
        (house_id,),
    )

    rows = cursor.fetchall()
    cursor.close()

    return rows
