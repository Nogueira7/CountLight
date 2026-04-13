from typing import List, Dict, Any
from app.repositories.notification_repository import (
    create_notification,
    get_user_notifications,
    mark_all_notifications_as_read,
)

# ==========================================================
# GENERIC NOTIFICATION
# ==========================================================

def notify(
    db,
    user_id: int,
    house_id: int,
    type: str,
    title: str,
    message: str,
):
    """
    Cria uma notificação genérica.
    Pode ser usada por qualquer parte do sistema.
    """
    create_notification(
        db=db,
        user_id=user_id,
        house_id=house_id,
        type=type,
        title=title,
        message=message,
    )


# ==========================================================
# GOAL COMPLETED
# ==========================================================

def notify_goal_completed(db, user_id: int, house_id: int):
    notify(
        db=db,
        user_id=user_id,
        house_id=house_id,
        type="goal_completed",
        title="Meta Concluída!",
        message="Parabéns! Atingiste o teu objetivo mensal.",
    )


# ==========================================================
# GOAL FAILED
# ==========================================================

def notify_goal_failed(db, user_id: int, house_id: int):
    notify(
        db=db,
        user_id=user_id,
        house_id=house_id,
        type="goal_failed",
        title="Meta Não Atingida",
        message="Ultrapassaste o limite definido para este mês.",
    )


# ==========================================================
# ACHIEVEMENT COMPLETED
# ==========================================================

def notify_achievement_completed(
    db,
    user_id: int,
    house_id: int,
    achievement_title: str
):

    print("🔔 NOTIFICATION FUNCTION CHAMADA")  # 👈 AQUI

    notify(
        db=db,
        user_id=user_id,
        house_id=house_id,
        type="achievement_completed",
        title="Nova Conquista!",
        message=f"Desbloqueaste a conquista: {achievement_title}",
    )


# ==========================================================
# ENERGY ALERTS (para timeline inteligente)
# ==========================================================

def notify_energy_alert(
    db,
    user_id: int,
    house_id: int,
    title: str,
    message: str
):
    """
    Usado pelos alertas de energia.
    Exemplo: pico de potência, consumo noturno, etc.
    """
    notify(
        db=db,
        user_id=user_id,
        house_id=house_id,
        type="energy_alert",
        title=title,
        message=message,
    )


# ==========================================================
# GET NOTIFICATIONS
# ==========================================================

def get_notifications(db, user_id: int, house_id: int) -> List[Dict[str, Any]]:
    """
    Obtém notificações da casa para o utilizador.
    Usado pelo Registo de eventos (timeline).
    """
    return get_user_notifications(
        db=db,
        user_id=user_id,
        house_id=house_id
    )


# ==========================================================
# CLEAR NOTIFICATIONS
# ==========================================================

def clear_notifications(db, user_id: int, house_id: int) -> int:
    """
    Marca todas as notificações como lidas.
    """
    return mark_all_notifications_as_read(
        db=db,
        user_id=user_id,
        house_id=house_id
    )