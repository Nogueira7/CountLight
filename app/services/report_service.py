from datetime import datetime, timedelta
from typing import Optional

from app.repositories.energy_repository import (
    get_total_consumption_for_period,
    get_total_consumption_for_date,
    get_total_consumption_previous_month,
    get_estimated_month_cost,
    get_price_per_kwh,
    get_room_total_consumption_for_period,
    get_room_estimated_month_cost,
    get_device_consumption_today,
)

from app.repositories.energy_repository import (
    get_energy_summary_by_room,
    get_energy_summary_by_device,
    get_hourly_consumption_today,
)


# =====================================================
# 🧠 HELPERS
# =====================================================


def _calculate_cost(kwh: float, price_per_kwh: float) -> float:
    return round(kwh * price_per_kwh, 2)


def _get_period_days(start: str, end: str) -> int:
    d1 = datetime.strptime(start, "%Y-%m-%d")
    d2 = datetime.strptime(end, "%Y-%m-%d")
    return (d2 - d1).days + 1


def _map_period_to_repo(period: str):
    if period == "today":
        return "today"
    elif period in ["thisMonth", "prevMonth"]:
        return "month"
    else:
        return None


# =====================================================
# 🏠 HOUSE REPORT (SIMPLE)
# =====================================================


def generate_house_report_simple(
    db,
    user_id: int,
    period: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    price_per_kwh = get_price_per_kwh(db, user_id)

    # -----------------------------------------
    # 📊 CONSUMO
    # -----------------------------------------
    if period == "today":
        total_kwh = get_total_consumption_for_period(db, user_id, "today")

    elif period == "thisMonth":
        total_kwh = get_total_consumption_for_period(db, user_id, "month")

    elif period == "prevMonth":
        total_kwh = get_total_consumption_previous_month(db, user_id)

    elif period == "last7":
        total_kwh = 0
        for i in range(7):
            day = datetime.now() - timedelta(days=i)
            total_kwh += get_total_consumption_for_date(db, user_id, day.date())

    elif period == "custom" and start and end:
        total_kwh = 0
        days = _get_period_days(start, end)

        for i in range(days):
            day = datetime.strptime(start, "%Y-%m-%d") + timedelta(days=i)
            total_kwh += get_total_consumption_for_date(db, user_id, day.date())
    else:
        total_kwh = 0

    total_kwh = round(total_kwh, 3)

    # -----------------------------------------
    # 💰 CUSTO
    # -----------------------------------------
    cost = _calculate_cost(total_kwh, price_per_kwh)

    # -----------------------------------------
    # 📉 COMPARAÇÃO (simples)
    # -----------------------------------------
    previous_kwh = get_total_consumption_previous_month(db, user_id)

    if previous_kwh > 0:
        variation = ((total_kwh - previous_kwh) / previous_kwh) * 100
    else:
        variation = 0

    variation = round(variation, 2)

    # -----------------------------------------
    # 🧠 INSIGHT
    # -----------------------------------------
    if total_kwh == 0:
        insight = "Sem consumo registado no período."
    elif variation < 0:
        insight = f"Consumo {abs(variation)}% abaixo do período anterior."
    elif variation > 0:
        insight = f"Consumo {variation}% acima do período anterior."
    else:
        insight = "Consumo igual ao período anterior."

    return {
        "type": "house",
        "total_kwh": total_kwh,
        "cost": cost,
        "variation": variation,
        "insight": insight,
    }


# =====================================================
# 🏠 ROOM REPORT (SIMPLE)
# =====================================================


def generate_room_report_simple(
    db,
    user_id: int,
    room_id: int,
    period: str,
):
    price_per_kwh = get_price_per_kwh(db, user_id)

    # -----------------------------------------
    # 📊 CONSUMO
    # -----------------------------------------
    repo_period = _map_period_to_repo(period)

    if repo_period:
        total_kwh = get_room_total_consumption_for_period(
            db, user_id, room_id, repo_period
        )
    else:
        total_kwh = 0

    total_kwh = round(total_kwh, 3)

    # -----------------------------------------
    # 💰 CUSTO
    # -----------------------------------------
    cost = _calculate_cost(total_kwh, price_per_kwh)

    # -----------------------------------------
    # 🔝 TOP DEVICES (hoje - simplificado)
    # -----------------------------------------
    devices = get_device_consumption_today(db, user_id)

    top_devices = sorted(devices, key=lambda x: x["value"], reverse=True)[:3]

    # -----------------------------------------
    # 🧠 INSIGHT
    # -----------------------------------------
    if total_kwh == 0:
        insight = "Sem consumo registado nesta divisão."
    else:
        insight = f"Divisão consumiu {total_kwh} kWh no período."

    return {
        "type": "room",
        "total_kwh": total_kwh,
        "cost": cost,
        "top_devices": top_devices,
        "insight": insight,
    }


# =====================================================
# 🚀 ENTRY POINT
# =====================================================


def generate_report(
    db,
    user_id: int,
    report_type: str,
    detail: str,
    period: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    room_id: Optional[int] = None,
):
    # Por agora só suportamos SIMPLE
    if detail != "simple":
        raise ValueError("Apenas 'simple' está implementado para já.")

    if report_type == "house":
        return generate_house_report_simple(db, user_id, period, start, end)

    elif report_type == "room":
        if not room_id:
            raise ValueError("room_id é obrigatório para relatórios de divisão.")

        return generate_room_report_simple(db, user_id, room_id, period)

    else:
        raise ValueError("Tipo de relatório inválido.")


def get_simple_report(
    db,
    user_id: int,
    start_date: str,
    end_date: str,
    report_type: str,
    room_id: int | None = None,
):
    """
    Wrapper que adapta para generate_report
    """

    # 🔥 converter intervalo em period
    # (por agora vamos assumir custom)
    period = "custom"

    return generate_report(
        db=db,
        user_id=user_id,
        report_type=report_type,
        detail="simple",
        period=period,
        start=start_date,
        end=end_date,
        room_id=room_id,
    )


def get_detailed_report(
    db,
    user_id: int,
    start_date: str,
    end_date: str,
    report_type: str,
    room_id: int | None = None,
):
    """
    Relatório detalhado baseado no dashboard
    """

    # =========================================
    # ⚡ KPIs
    # =========================================
    today_kwh = get_total_consumption_for_period(db, user_id, "today")
    month_kwh = get_total_consumption_for_period(db, user_id, "month")
    year_kwh = get_total_consumption_for_period(db, user_id, "year")
    month_cost = get_estimated_month_cost(db, user_id)

    # =========================================
    # 📊 DISTRIBUIÇÃO
    # =========================================
    rooms = get_energy_summary_by_room(db, user_id)
    devices = get_energy_summary_by_device(db, user_id)

    # ⚠️ alguns repos retornam {"data": [...]}
    if isinstance(rooms, dict):
        rooms = rooms.get("data", [])

    if isinstance(devices, dict):
        devices = devices.get("data", [])

    # =========================================
    # 📈 COMPARAÇÕES
    # =========================================
    previous_month = get_total_consumption_previous_month(db, user_id)

    if previous_month > 0:
        vs_month = ((month_kwh - previous_month) / previous_month) * 100
    else:
        vs_month = 0

    vs_month = round(vs_month, 2)

    # =========================================
    # ⚠️ PICOS (simples por agora)
    # =========================================
    hourly = get_hourly_consumption_today(db, user_id)

    peak_value = 0
    peak_hour = "--"

    if isinstance(hourly, dict):
        data = hourly.get("data", [])
        if data:
            peak = max(data, key=lambda x: x["value"])
            peak_value = peak["value"]
            peak_hour = peak["label"]

    peaks = {
        "value": peak_value,
        "hour": peak_hour
    }

    # =========================================
    # 🔝 TOP
    # =========================================
    top_rooms = sorted(rooms, key=lambda x: x["value"], reverse=True)[:3]
    top_devices = sorted(devices, key=lambda x: x["value"], reverse=True)[:3]

    # =========================================
    # 📊 PERCENTAGENS
    # =========================================
    total_rooms = sum(r["value"] for r in rooms) or 1
    total_devices = sum(d["value"] for d in devices) or 1

    for r in top_rooms:
        r["percentage"] = round((r["value"] / total_rooms) * 100, 1)

    for d in top_devices:
        d["percentage"] = round((d["value"] / total_devices) * 100, 1)

    # =========================================
    # 💰 CUSTOS
    # =========================================
    costs = {
        "current": round(month_cost, 2),
        "projected": round(month_cost * 1.1, 2),
        "diff": round(month_cost - (month_cost * 0.9), 2),
    }

    # =========================================
    # 🧠 INSIGHT
    # =========================================
    if vs_month > 0:
        insight = f"Consumo {vs_month}% acima do mês anterior."
    elif vs_month < 0:
        insight = f"Consumo {abs(vs_month)}% abaixo do mês anterior."
    else:
        insight = "Consumo estável."

    # =========================================
    # 🚀 OUTPUT FINAL
    # =========================================
    return {
        "kpis": {
            "today": round(today_kwh, 2),
            "month": round(month_kwh, 2),
            "year": round(year_kwh, 2),
            "cost": round(month_cost, 2),
        },
        "rooms": rooms,
        "devices": devices,
        "comparisons": {
            "vs_yesterday": 0,  # podes melhorar depois
            "vs_month": vs_month,
        },
        "peaks": peaks,
        "top_rooms": top_rooms,
        "top_devices": top_devices,
        "costs": costs,
        "insight": insight,
    }