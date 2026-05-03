from datetime import datetime, date
from typing import Dict, Any, Tuple, List

from app.repositories.goal_repository import (
    get_active_goal_by_type,
    get_all_active_goals,
    create_goal,
    update_goal_progress,
    delete_goal,
)

from app.repositories.achievement_repository import (
    get_monthly_consumption,
)

from app.services.notification_service import (
    notify_goal_completed,
    notify_goal_failed,
)

# HELPERS



def get_current_month_range() -> Tuple[date, date]:
    now = datetime.utcnow()
    start_date = date(now.year, now.month, 1)

    if now.month == 12:
        end_date = date(now.year, 12, 31)
    else:
        next_month = date(now.year, now.month + 1, 1)
        end_date = next_month.replace(day=1) - date.resolution

    return start_date, end_date


def calculate_progress(current: float, limit: float) -> float:
    if limit <= 0:
        return 0.0
    return (current / limit) * 100.0


# CREATE GOALS



def create_monthly_limit_kwh_goal(
    db,
    user_id: int,
    house_id: int,
    target_value: float,
) -> Dict[str, Any]:

    existing = get_active_goal_by_type(
        db, user_id, house_id, "monthly_limit_kwh"
    )

    if existing:
        raise ValueError("Já existe uma meta ativa de consumo (kWh).")

    start_date, end_date = get_current_month_range()

    create_goal(
        db=db,
        user_id=user_id,
        house_id=house_id,
        goal_type="monthly_limit_kwh",
        target_value=target_value,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "message": "Meta mensal de consumo criada com sucesso.",
        "goal_type": "monthly_limit_kwh",
        "target_value": target_value,
        "status": "active",
    }


def create_monthly_cost_goal(
    db,
    user_id: int,
    house_id: int,
    target_value: float,
) -> Dict[str, Any]:

    existing = get_active_goal_by_type(
        db, user_id, house_id, "monthly_cost_limit"
    )

    if existing:
        raise ValueError("Já existe uma meta ativa de custo (€).")

    start_date, end_date = get_current_month_range()

    create_goal(
        db=db,
        user_id=user_id,
        house_id=house_id,
        goal_type="monthly_cost_limit",
        target_value=target_value,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "message": "Meta mensal de custo criada com sucesso.",
        "goal_type": "monthly_cost_limit",
        "target_value": target_value,
        "status": "active",
    }



# EVALUATION CORE



def evaluate_goal(
    db,
    user_id: int,
    house_id: int,
    goal: Dict[str, Any],
) -> Dict[str, Any]:

    now = datetime.utcnow()
    year, month = now.year, now.month

    current_consumption = float(
        get_monthly_consumption(db, house_id, year, month) or 0.0
    )

    goal_type = goal["goal_type"]
    limit = float(goal["target_value"])
    old_status = goal["status"]

    # CALCULAR VALOR ATUAL


    if goal_type == "monthly_limit_kwh":
        current_value = current_consumption

    elif goal_type == "monthly_cost_limit":
        price_per_kwh = 0.20  # placeholder
        current_value = current_consumption * price_per_kwh

    else:
        return {}

    progress = calculate_progress(current_value, limit)


    # DETERMINAR NOVO STATUS


    if current_value > limit:
        new_status = "failed"

    elif now.date() >= goal["end_date"]:
        new_status = "completed"

    else:
        new_status = "active"


    # NOTIFICAÇÕES (APENAS SE MUDOU)


    if old_status != new_status:

        if new_status == "completed":
            notify_goal_completed(db, user_id, house_id)

        elif new_status == "failed":
            notify_goal_failed(db, user_id, house_id)


    # ATUALIZAR BASE DE DADOS


    update_goal_progress(
        db=db,
        goal_id=goal["id_goal"],
        user_id=user_id,
        house_id=house_id,
        current_value=current_value,
        status=new_status,
    )

    return {
        "goal_id": goal["id_goal"],
        "goal_type": goal_type,
        "target_value": limit,
        "current_value": round(current_value, 2),
        "progress": round(progress, 2),
        "status": new_status,
        "start_date": goal["start_date"],
        "end_date": goal["end_date"],
    }



# EVALUATE ALL ACTIVE GOALS 



def evaluate_all_active_goals(
    db,
    user_id: int,
    house_id: int,
) -> List[Dict[str, Any]]:

    goals = get_all_active_goals(db, user_id, house_id)

    results = []

    for goal in goals:
        evaluated = evaluate_goal(db, user_id, house_id, goal)
        if evaluated:
            results.append(evaluated)

    return results



# DELETE GOAL



def remove_goal(
    db,
    goal_id: int,
    user_id: int,
    house_id: int,
) -> Dict[str, Any]:

    goals = get_all_active_goals(db, user_id, house_id)

    valid_goal = next(
        (g for g in goals if g["id_goal"] == goal_id),
        None
    )

    if not valid_goal:
        raise ValueError("Meta não encontrada ou não pertence ao utilizador.")

    delete_goal(db, goal_id, user_id, house_id)

    return {"message": "Meta removida com sucesso."}
