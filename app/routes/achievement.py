from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.db.database import get_db
from app.services.achievement_service import update_and_get_user_achievements
from app.repositories.achievement_repository import house_belongs_to_user


router = APIRouter(prefix="/achievements", tags=["Achievements"])


# ==========================================================
# RESPONSE MODEL
# ==========================================================

class AchievementOut(BaseModel):
    achievement_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    progress: float = Field(..., ge=0)
    target: Optional[float] = None
    status: str  # "completed" | "not_completed"


# ==========================================================
# DEPENDENCY: CASA ATIVA
# ==========================================================

def get_current_house_id(
    x_house_id: Optional[int] = Header(None, alias="X-House-Id"),
) -> int:
    """
    Lê o header X-House-Id enviado pelo frontend.
    - 400 se não vier ou se for inválido
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
# GET ACHIEVEMENTS
# ==========================================================

@router.get("", response_model=List[AchievementOut])
def get_achievements(
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):
    """
    Fluxo:
    - Valida JWT
    - Recebe casa ativa via header
    - Verifica se a casa pertence ao utilizador
    - Recalcula e faz upsert das conquistas do período atual
    - Pode disparar notificação quando uma conquista transita para 'completed'
    - Devolve estado atualizado
    """
    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa.",
        )

    return update_and_get_user_achievements(
        db=db,
        user_id=current_user,
        house_id=house_id,
    )