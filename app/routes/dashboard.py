from fastapi import APIRouter, Depends
from app.db.database import get_db
from app.core.security import get_current_user

from app.repositories.energy_repository import (
    get_total_consumption_for_period,
    get_total_consumption_for_date,
    get_total_consumption_previous_month,
    get_daily_consumption_in_month,
    get_hourly_consumption_today,
    get_room_consumption_today,
    get_device_consumption_today,
    get_price_per_kwh,
)

from datetime import datetime, timedelta
import calendar


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/detailed")
def get_dashboard_detailed(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user


    # CONSUMOS BASE 


    today_kwh = float(get_total_consumption_for_period(db, user_id, "today") or 0)
    month_kwh = float(get_total_consumption_for_period(db, user_id, "month") or 0)

    yesterday_date = datetime.now().date() - timedelta(days=1)
    yesterday_kwh = float(get_total_consumption_for_date(db, user_id, yesterday_date) or 0)

    previous_month_kwh = float(get_total_consumption_previous_month(db, user_id) or 0)


    # MÉDIA DIÁRIA DO MÊS (ATÉ HOJE)


    # Média baseada nos dias decorridos até hoje, não no total de dias do mês
    today_day = datetime.now().day
    month_daily_avg = (
        month_kwh / today_day
        if today_day > 0 else 0
    )

    # Para cálculos de percentagem, usar always o mismo month_daily_avg


    # COMPARAÇÕE
  

    vs_yesterday_percent = (
        ((today_kwh - yesterday_kwh) / yesterday_kwh) * 100
        if yesterday_kwh > 0 else 0
    )

    vs_month_avg_kwh = today_kwh - month_daily_avg

    # Calcular percentagem usando month_daily_avg
    vs_month_avg_percent = (
        (vs_month_avg_kwh / month_daily_avg) * 100
        if month_daily_avg > 0 else 0
    )


    # PICO HORÁRIO


    hourly_data = get_hourly_consumption_today(db, user_id) or {}
    hourly_values = hourly_data.get("data", [])

    today_peak_kwh = 0
    today_peak_hour = None

    for item in hourly_values:
        value = float(item["value"] or 0)
        if value > today_peak_kwh:
            today_peak_kwh = value
            today_peak_hour = item["label"]


    # CUSTOS


    price_per_kwh = float(get_price_per_kwh(db, user_id) or 0)

    current_month_cost = month_kwh * price_per_kwh

    today_date = datetime.now()
    days_passed = today_date.day
    days_in_month = calendar.monthrange(
        today_date.year, today_date.month
    )[1]

    projected_month_kwh = (
        (month_kwh / days_passed) * days_in_month
        if days_passed > 0 else 0
    )

    projected_month_cost = projected_month_kwh * price_per_kwh

    previous_month_cost = previous_month_kwh * price_per_kwh
    diff_vs_previous_month_cost = current_month_cost - previous_month_cost


    # DIVISÕES

    room_today = get_room_consumption_today(db, user_id) or {}
    room_values = room_today.get("data", [])

    principal_room = None
    max_room_kwh = 0
    room_percentages = []

    for item in room_values:
        value = float(item["value"] or 0)
        percent = (value / today_kwh * 100) if today_kwh > 0 else 0

        room_percentages.append({
            "label": item["label"],
            "value_kwh": round(value, 2),
            "percentage": round(percent, 1)
        })

        if value > max_room_kwh:
            max_room_kwh = value
            principal_room = item["label"]

    # EQUIPAMENTOS

    device_today = get_device_consumption_today(db, user_id) or []

    device_percentages = []

    for item in device_today:
        value = float(item["value"] or 0)
        percent = (value / today_kwh * 100) if today_kwh > 0 else 0

        device_percentages.append({
            "label": item["label"],
            "value_kwh": round(value, 2),
            "percentage": round(percent, 1)
        })

    # IMPACTO €

    impact_kwh = max(today_kwh - month_daily_avg, 0)
    impact_eur = impact_kwh * price_per_kwh

    # INSIGHT INTELIGENTE

    difference_kwh = today_kwh - month_daily_avg
    difference_percent = vs_month_avg_percent

    if today_kwh == 0:
        insight = "Ainda não há consumo registado hoje."

    elif difference_percent > 15:
        insight = (
            f"Hoje consumiu {round(difference_kwh, 2)} kWh "
            f"({round(difference_percent, 1)}%) acima da média diária. "
            f"Impacto estimado: {round(impact_eur, 2)} €."
        )

    elif difference_percent > 5:
        insight = (
            f"Consumo {round(difference_kwh, 2)} kWh "
            f"({round(difference_percent, 1)}%) acima do habitual."
        )

    elif difference_percent < -10:
        insight = (
            f"Excelente eficiência! "
            f"{round(abs(difference_kwh), 2)} kWh "
            f"({round(abs(difference_percent), 1)}%) abaixo da média."
        )

    elif difference_percent < 0:
        insight = (
            f"Consumo ligeiramente abaixo do habitual "
            f"({round(abs(difference_percent), 1)}%)."
        )

    else:
        insight = "Consumo dentro do padrão normal."

    #RESPOSTA FINAL

    return {
        "consumption": {
            "today_kwh": round(today_kwh, 2),
            "yesterday_kwh": round(yesterday_kwh, 2),
            "month_kwh": round(month_kwh, 2),
            "month_daily_average_kwh": round(month_daily_avg, 2),
        },
        "comparisons": {
            "vs_yesterday_percent": round(vs_yesterday_percent, 2),
            "vs_month_average_kwh": round(vs_month_avg_kwh, 2),
            "vs_month_average_percent": round(vs_month_avg_percent, 2),
        },
        "peaks": {
            "today_peak_kwh": round(today_peak_kwh, 2),
            "today_peak_hour": today_peak_hour,
        },
        "top_rooms": room_percentages,
        "top_devices": device_percentages,
        "costs": {
            "current_month_cost": round(current_month_cost, 2),
            "projected_month_cost": round(projected_month_cost, 2),
            "difference_vs_previous_month": round(diff_vs_previous_month_cost, 2),
        },
        "principal_cause": {
            "room": principal_room,
            "time_range": today_peak_hour,
            "impact_eur": round(impact_eur, 2),
        },
        "daily_insight": insight,
    }
