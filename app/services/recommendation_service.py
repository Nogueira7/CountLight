import requests
from app.core.logging import logger
from app.repositories.device_repository import get_all_user_devices

# =====================================================
# CONFIGURAÇÃO
# =====================================================

COMPARAJA_API = "https://www.comparaja.pt/api/energy/products"
ENABLE_COMPARAJA_API = False

# escala energética
ENERGY_SCORE = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "G": 7
}

# consumo médio estimado por classe (kWh/ano)
ENERGY_CONSUMPTION = {
    "A": 100,
    "B": 130,
    "C": 160,
    "D": 200,
    "E": 250,
    "F": 300,
    "G": 350
}

ELECTRICITY_PRICE = 0.20  # €/kWh


# =====================================================
# HELPERS
# =====================================================

def _safe_float(value, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


# =====================================================
# RECOMENDAÇÃO DE ELETRODOMÉSTICOS
# =====================================================

def get_appliance_recommendation(db, user_id: int):
    devices = get_all_user_devices(db, user_id)

    if not devices:
        return None

    # escolher device com pior classe
    worst_device = None
    worst_score = -1

    for d in devices:
        energy_class = d.get("energy_class")
        if not energy_class:
            continue

        score = ENERGY_SCORE.get(str(energy_class).upper(), 0)

        if score > worst_score:
            worst_score = score
            worst_device = d

    if not worst_device:
        return None

    current_class = str(worst_device["energy_class"]).upper()
    recommended_class = "A"

    current_consumption = ENERGY_CONSUMPTION.get(current_class, 200)
    new_consumption = ENERGY_CONSUMPTION["A"]

    savings_kwh = current_consumption - new_consumption
    savings_yearly = round(savings_kwh * ELECTRICITY_PRICE)

    appliance_price = 500  # preço médio estimado
    payback_months = round((appliance_price / savings_yearly) * 12) if savings_yearly > 0 else 0

    cycles_per_week = 4

    message = (
        f"A sua {worst_device['name']} tem classe {current_class} (escala A–G). "
        f"Se trocar por uma classe {recommended_class}, pode poupar ~{savings_yearly}€/ano "
        f"e recuperar o investimento em cerca de {payback_months} meses "
        f"(considerando {cycles_per_week} ciclos/semana)."
    )

    return {
        "appliance": worst_device["name"],
        "energyClassCurrent": current_class,
        "energyClassRecommended": recommended_class,
        "estimatedSavingsYearly": savings_yearly,
        "paybackMonths": payback_months,
        "cyclesPerWeek": cycles_per_week,
        "message": message
    }


# =====================================================
# RECOMENDAÇÃO — Horários mais baratos (bi/tri-horário)
# =====================================================

def get_time_of_use_recommendation(user_data: dict):
    """
    Gera a frase dinâmica do tipo:
    "Se deslocar X kWh/mês ... para Y (Z), pode reduzir ..."

    Nota:
    - A tua BD (pelo dump) não tem preços por período (vazio/cheias/ponta),
      só price_per_kwh "plano". Portanto esta recomendação usa uma heurística
      conservadora para estimar poupança.
    """

    # campos que costumam existir no teu user_data (vindo do house_repository):
    monthly_kwh = _safe_float(
    user_data.get("monthly_kwh")
    or user_data.get("monthlyKwh")
    or user_data.get("monthly")
    or user_data.get("monthly_consumption")
    or user_data.get("monthly_consumption_kwh")
    or user_data.get("house_monthly_kwh")
    or user_data.get("consumption_total"),
    default=None,
)

    price_per_kwh = _safe_float(
    user_data.get("price_per_kwh")
    or user_data.get("pricePerKwh")
    or user_data.get("price_kwh")
    or user_data.get("priceKwh"),
    default=0.0,
) or 0.0

    tariff = (
    user_data.get("tariff")
    or user_data.get("tariff_name")
    or user_data.get("tariffType")
    or ""
).strip().lower()

    if not monthly_kwh or monthly_kwh <= 0:
        return None

    # quanto dá para "mexer" (lavar roupa/loiça, secar, etc.)
    shiftable_kwh_per_month = round(monthly_kwh * 0.15, 1)

    # janelas típicas (ajusta depois consoante a tua lógica/fornecedor)
    if "bi" in tariff:
        cheapest_period_name = "Vazio"
        cheapest_period_hours = "22:00–08:00"
        # estimativa conservadora: ~4% de poupança no kWh deslocável
        estimated_savings_monthly = round(shiftable_kwh_per_month * price_per_kwh * 0.04, 2)

    elif "tri" in tariff:
        cheapest_period_name = "Vazio"
        cheapest_period_hours = "00:00–08:00"
        # estimativa conservadora: ~5% de poupança no kWh deslocável
        estimated_savings_monthly = round(shiftable_kwh_per_month * price_per_kwh * 0.05, 2)

    else:
        # tarifa simples: não há período mais barato
        return {
            "shiftableKwhPerMonth": shiftable_kwh_per_month,
            "cheapestPeriodName": "—",
            "cheapestPeriodHours": "—",
            "estimatedSavingsMonthly": 0,
            "message": (
                "A tua tarifa é simples, por isso não existem períodos horários mais baratos para otimizar."
            ),
        }

    message = (
        f"Se deslocar {shiftable_kwh_per_month} kWh/mês (ex.: lavar roupa/loiça) para "
        f"{cheapest_period_name} ({cheapest_period_hours}), pode reduzir a fatura em "
        f"~{estimated_savings_monthly}€/mês."
    )

    return {
        "shiftableKwhPerMonth": shiftable_kwh_per_month,
        "cheapestPeriodName": cheapest_period_name,
        "cheapestPeriodHours": cheapest_period_hours,
        "estimatedSavingsMonthly": estimated_savings_monthly,
        "message": message,
    }


# =====================================================
# RECOMENDAÇÃO DE TARIFA
# =====================================================

def get_energy_recommendation(user_data: dict):
    if not ENABLE_COMPARAJA_API:
        logger.info("Comparaja API desativada (modo desenvolvimento)")

        return {
            "provider": "Simulação",
            "tariff": "Tarifa Teste CountLight",
            "monthly_price": 75,
            "message": "Recomendação simulada (API externa desativada)."
        }

    total = _safe_int(user_data.get("consumption_total"), default=0) or 0
    if total <= 0:
        return {
            "provider": "N/A",
            "tariff": "N/A",
            "monthly_price": 0,
            "message": "Sem dados de consumo suficientes para calcular a melhor tarifa."
        }

    low = int(round(total * 0.4))
    high = int(round(total * 0.6))

    adults = _safe_int(user_data.get("adults"), default=0) or 0
    children = _safe_int(user_data.get("children"), default=0) or 0
    power = _safe_float(user_data.get("power"), default=0.0) or 0.0

    params = {
        "journeyId": "4fbd1ee2-c835-4a2b-a668-85a75a6d99c7",
        "contractType": "electricity",
        "houseUsage": "normal",
        "householdAdults": adults,
        "householdChildren": children,
        "electricityConsumptionLow": low,
        "electricityConsumptionHigh": high,
        "electricityConsumption": total,
        "electricityTariffType": "simple",
        "electricityContractedPower": f"{power:.2f}",
        "gasTier": 1,
        "gasConsumption": 200
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        logger.info(f"Comparaja request feita para consumo {total} kWh")

        response = requests.get(
            COMPARAJA_API,
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        products = data.get("listOfProducts", [])

        if not products:
            return {
                "provider": "N/A",
                "tariff": "N/A",
                "monthly_price": 0,
                "message": "Nenhuma tarifa encontrada."
            }

        best = min(
            products,
            key=lambda p: p.get("enProductSpec", {}).get("electricityTotal", float("inf"))
        )

        provider = best.get("provider", "Desconhecido")
        tariff = best.get("productName", "Desconhecido")
        price = best.get("enProductSpec", {}).get("electricityTotal", 0)

        logger.info(f"Melhor tarifa encontrada: {tariff} ({provider})")

        return {
            "provider": provider,
            "tariff": tariff,
            "monthly_price": round(float(price or 0), 2),
            "message": (
                f"A melhor tarifa para si é {tariff} da {provider} "
                f"com custo estimado de {round(float(price or 0), 2)}€/mês."
            )
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao contactar Comparaja API: {str(e)}")

        return {
            "provider": "Erro",
            "tariff": "N/A",
            "monthly_price": 0,
            "message": f"Erro ao contactar a API de comparação: {str(e)}"
        }
    

# =====================================================
# RECOMENDAÇÃO — Custo em tempo real e previsão mensal
# =====================================================

def get_cost_recommendation(user_data: dict):
    """
    Calcula custo aproximado em tempo real e previsão mensal
    com base na potência atual do dispositivo.
    """

    power_w = _safe_float(
        user_data.get("current_power")
        or user_data.get("power_w")
        or user_data.get("power")
        or 0
    )

    price_per_kwh = _safe_float(
        user_data.get("price_per_kwh")
        or ELECTRICITY_PRICE
    )

    monthly_budget = _safe_float(
        user_data.get("monthly_budget")
        or 40
    )

    if not power_w or power_w <= 0:
        return {
            "costPerHour": 0,
            "estimatedMonthlyCost": 0,
            "budget": monthly_budget,
            "message": "Sem dados de potência suficientes para calcular o custo atual."
        }

    power_kw = power_w / 1000

    cost_per_hour = power_kw * price_per_kwh

    estimated_monthly = cost_per_hour * 24 * 30

    if estimated_monthly > monthly_budget:
        message = (
            f"Estás a gastar cerca de {cost_per_hour:.2f}€/h agora. "
            f"Se o consumo se mantiver, a fatura mensal pode chegar a "
            f"{estimated_monthly:.2f}€, acima do orçamento definido."
        )
    else:
        message = (
            f"Estás a gastar cerca de {cost_per_hour:.2f}€/h agora. "
            f"Estimativa mensal: {estimated_monthly:.2f}€, dentro do orçamento."
        )

    return {
        "costPerHour": round(cost_per_hour, 2),
        "estimatedMonthlyCost": round(estimated_monthly, 2),
        "budget": monthly_budget,
        "message": message
    }