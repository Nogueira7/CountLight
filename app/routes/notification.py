from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.security import get_current_user
from app.db.database import get_db
from app.services.notification_service import get_notifications, clear_notifications
from app.repositories.achievement_repository import house_belongs_to_user


router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ==========================================================
# DEPENDENCY: CASA ATIVA
# ==========================================================

def get_current_house_id(x_house_id: Optional[int] = Header(None, alias="X-House-Id")) -> int:
    """
    Obtém o ID da casa ativa através do header X-House-Id.
    """
    if x_house_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Casa não selecionada.",
        )

    if x_house_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-House-Id inválido.",
        )

    return x_house_id


# ==========================================================
# GET USER NOTIFICATIONS (Timeline / Registo de eventos)
# ==========================================================

@router.get("", response_model=List[Dict[str, Any]])
def get_user_notifications(
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):
    """
    Devolve as notificações da casa selecionada.
    Estas notificações são usadas no Registo de eventos (timeline).
    """

    # Verificar se a casa pertence ao utilizador
    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa.",
        )

    notifications = get_notifications(
        db=db,
        user_id=current_user,
        house_id=house_id
    )

    return notifications


# ==========================================================
# MARK ALL AS READ
# ==========================================================

@router.patch("/read-all")
def mark_all_notifications_read(
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):
    """
    Marca todas as notificações da casa como lidas.
    """

    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa.",
        )

    updated = clear_notifications(
        db=db,
        user_id=current_user,
        house_id=house_id
    )

    return {
        "message": "Notificações marcadas como lidas.",
        "updated": updated
    }