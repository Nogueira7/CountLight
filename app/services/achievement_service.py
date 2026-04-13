from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from app.repositories.achievement_repository import (
    get_all_achievements,
    get_user_achievement,
    upsert_user_achievement,
    get_monthly_consumption,
    get_previous_month,
    get_house_monthly_limit,
    mark_user_achievement_completed,
)
from app.services.notification_service import notify_achievement_completed


# ==========================================================
# HELPERS
# ==========================================================

def calculate_percentage_reduction(current: float, previous: float) -> float:
    """
    Percentagem de redução de consumo (>= 0).
    Ex.: previous=100, current=80 => 20%
    """
    if previous <= 0:
        return 0.0
    reduction = ((previous - current) / previous) * 100.0
    return max(0.0, reduction)


def get_current_period_reference(now: Optional[datetime] = None) -> date:
    now = now or datetime.utcnow()
    return date(now.year, now.month, 1)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


def _status_from_completed(is_completed: bool) -> str:
    # Mantém o teu contrato atual ("completed" vs "not_completed")
    return "completed" if is_completed else "not_completed"


def _persist_progress(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
    progress: float,
    status: str,
) -> int:
    """
    Persiste (upsert) e devolve id_user_achievement.
    """
    return upsert_user_achievement(
        db=db,
        user_id=user_id,
        house_id=house_id,
        achievement_id=int(achievement["id_achievement"]),
        period_reference=period_reference,
        status=status,
        progress=float(progress),
    )


def _maybe_notify_completed(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
    status: str,
    progress: float,
) -> None:

    if status != "completed":
        return

    # 🔍 VER ANTES DE GUARDAR
    current = get_user_achievement(
        db,
        user_id,
        house_id,
        int(achievement["id_achievement"]),
        period_reference,
    )

    # 🆕 Só notifica se ainda não estava completed
    if not current or current.get("status") != "completed":
        print("🔥 VOU NOTIFICAR:", achievement["title"])

        notify_achievement_completed(
            db,
            user_id,
            house_id,
            str(achievement.get("title") or "Conquista"),
        )


def _build_response(
    *,
    achievement: Dict[str, Any],
    progress: float,
    status: str,
    target: Optional[float],
) -> Dict[str, Any]:
    return {
        "achievement_id": int(achievement["id_achievement"]),
        "title": achievement.get("title"),
        "description": achievement.get("description"),
        "type": achievement.get("type"),
        "progress": round(float(progress), 2),
        "target": target,
        "status": status,
    }


# ==========================================================
# EVALUATORS
# ==========================================================

def evaluate_monthly_reduction(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
    now: datetime,
) -> Dict[str, Any]:
    year, month = now.year, now.month

    current = float(get_monthly_consumption(db, house_id, year, month) or 0.0)
    prev_year, prev_month = get_previous_month(year, month)
    previous = float(get_monthly_consumption(db, house_id, prev_year, prev_month) or 0.0)

    reduction = calculate_percentage_reduction(current, previous)
    target = float(achievement.get("target_value") or 0.0)

    is_completed = reduction >= target
    status = _status_from_completed(is_completed)

    # Persistir primeiro, depois notificar (evita notificação sem commit)

    _maybe_notify_completed(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        status=status,
        progress=reduction,
    )
    _persist_progress(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        progress=reduction,
        status=status,
    )
    

    return _build_response(achievement=achievement, progress=reduction, status=status, target=target)


def evaluate_monthly_limit(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
    now: datetime,
) -> Dict[str, Any]:
    year, month = now.year, now.month

    current = float(get_monthly_consumption(db, house_id, year, month) or 0.0)
    limit = get_house_monthly_limit(db, house_id)

    if not limit or limit <= 0:
        progress = 0.0
        status = "not_completed"
        _persist_progress(
            db,
            user_id=user_id,
            house_id=house_id,
            achievement=achievement,
            period_reference=period_reference,
            progress=progress,
            status=status,
        )
        return _build_response(achievement=achievement, progress=progress, status=status, target=0.0)

    # Progresso visual: margem abaixo do limite (0..100)
    margin_percentage = ((float(limit) - current) / float(limit)) * 100.0
    progress = clamp(margin_percentage, 0.0, 100.0)

    is_completed = current <= float(limit)
    status = _status_from_completed(is_completed)

    _maybe_notify_completed(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        status=status,
        progress=progress,
    )

    _persist_progress(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        progress=progress,
        status=status,
    )
    

    return _build_response(achievement=achievement, progress=progress, status=status, target=float(limit))


def evaluate_room_reduction(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
) -> Dict[str, Any]:
    # Placeholder: sem lógica ainda
    progress = 0.0
    status = "not_completed"

    _persist_progress(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        progress=progress,
        status=status,
    )
    return _build_response(
        achievement=achievement,
        progress=progress,
        status=status,
        target=float(achievement.get("target_value") or 0.0),
    )


def evaluate_device_reduction(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
) -> Dict[str, Any]:
    # Placeholder: sem lógica ainda
    progress = 0.0
    status = "not_completed"

    _persist_progress(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        progress=progress,
        status=status,
    )
    return _build_response(
        achievement=achievement,
        progress=progress,
        status=status,
        target=float(achievement.get("target_value") or 0.0),
    )


def evaluate_hourly_reduction(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
) -> Dict[str, Any]:
    # Placeholder: sem lógica ainda
    progress = 0.0
    status = "not_completed"

    _persist_progress(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        progress=progress,
        status=status,
    )
    return _build_response(
        achievement=achievement,
        progress=progress,
        status=status,
        target=float(achievement.get("target_value") or 0.0),
    )


def evaluate_streak_days(
    db,
    *,
    user_id: int,
    house_id: int,
    achievement: Dict[str, Any],
    period_reference: date,
    now: datetime,
) -> Dict[str, Any]:
    """
    Mantém a tua lógica atual (temporária): se mês está dentro do limite => streak=1 senão 0.
    Progress = (streak/target)*100.
    """
    limit = get_house_monthly_limit(db, house_id)
    target = int(achievement.get("target_value") or 1)

    if not limit or limit <= 0 or target <= 0:
        progress = 0.0
        status = "not_completed"
        _persist_progress(
            db,
            user_id=user_id,
            house_id=house_id,
            achievement=achievement,
            period_reference=period_reference,
            progress=progress,
            status=status,
        )
        return _build_response(achievement=achievement, progress=progress, status=status, target=float(target or 0))

    current = float(get_monthly_consumption(db, house_id, now.year, now.month) or 0.0)

    streak = 1 if current <= float(limit) else 0
    progress = (float(streak) / float(target)) * 100.0
    is_completed = streak >= target
    status = _status_from_completed(is_completed)

    _maybe_notify_completed(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        status=status,
        progress=progress,
    )

    _persist_progress(
        db,
        user_id=user_id,
        house_id=house_id,
        achievement=achievement,
        period_reference=period_reference,
        progress=progress,
        status=status,
    )
    

    return _build_response(achievement=achievement, progress=progress, status=status, target=float(target))


# ==========================================================
# PUBLIC SERVICE FUNCTION
# ==========================================================

def update_and_get_user_achievements(db, user_id: int, house_id: int) -> List[Dict[str, Any]]:
    """
    Atualiza (upsert) progresso/estado de todas as conquistas para o período atual
    e devolve a lista para UI.

    Inclui notificações quando uma conquista transita para 'completed' (1x por período).
    """
    now = datetime.utcnow()
    period_reference = get_current_period_reference(now)

    achievements = get_all_achievements(db)
    results: List[Dict[str, Any]] = []

    # Pequena otimização: consumo mensal atual calculado 1x (usado por vários tipos)
    # (mantém chamadas originais nos evaluators para não assumir demais; podes evoluir depois)

    for achievement in achievements:
        achievement_type = achievement.get("type")

        if achievement_type == "monthly_reduction":
            result = evaluate_monthly_reduction(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
                now=now,
            )

        elif achievement_type == "monthly_limit":
            result = evaluate_monthly_limit(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
                now=now,
            )

        elif achievement_type == "room_reduction":
            result = evaluate_room_reduction(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
            )

        elif achievement_type == "device_reduction":
            result = evaluate_device_reduction(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
            )

        elif achievement_type == "hourly_reduction":
            result = evaluate_hourly_reduction(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
            )

        elif achievement_type == "streak_days":
            result = evaluate_streak_days(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
                now=now,
            )

        else:
            # Tipo desconhecido: guarda placeholder sem notificar
            progress = 0.0
            status = "not_completed"
            _persist_progress(
                db,
                user_id=user_id,
                house_id=house_id,
                achievement=achievement,
                period_reference=period_reference,
                progress=progress,
                status=status,
            )
            result = _build_response(
                achievement=achievement,
                progress=progress,
                status=status,
                target=float(achievement.get("target_value") or 0.0),
            )

        results.append(result)

    print("RESULTS:", results)

    return results