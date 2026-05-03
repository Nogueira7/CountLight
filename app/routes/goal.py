from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, status, Query

from app.core.security import get_current_user
from app.db.database import get_db
from app.services.goal_service import (
    create_monthly_limit_kwh_goal,
    create_monthly_cost_goal,
    evaluate_all_active_goals,
    remove_goal,
)
from app.repositories.achievement_repository import house_belongs_to_user
from app.repositories.goal_repository import get_all_goals as get_all_goals_repo

router = APIRouter(
    prefix="/goals",
    tags=["Goals"]
)



# DEPENDENCY: CASA ATIVA


def get_current_house_id(
    x_house_id: int = Header(..., alias="X-House-Id")
) -> int:

    if x_house_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Casa não selecionada."
        )

    return x_house_id



# CREATE GOAL (DINÂMICO POR TIPO)


@router.post("", response_model=Dict[str, Any])
def create_goal(
    goal_type: str = Query(..., description="monthly_limit_kwh ou monthly_cost_limit"),
    target_value: float = Query(...),
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):
    """
    Cria meta conforme o tipo.
    """

    # Segurança
    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa."
        )

    try:

        if goal_type == "monthly_limit_kwh":
            return create_monthly_limit_kwh_goal(
                db=db,
                user_id=current_user,
                house_id=house_id,
                target_value=target_value,
            )

        elif goal_type == "monthly_cost_limit":
            return create_monthly_cost_goal(
                db=db,
                user_id=current_user,
                house_id=house_id,
                target_value=target_value,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de meta inválido."
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# GET ALL GOALS (LISTAGEM) 

@router.get("", response_model=List[Dict[str, Any]])
def get_all_goals(
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):
    """
    Devolve todas as metas da casa (ativas, concluídas e falhadas).
    """

    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa."
        )


    evaluate_all_active_goals(
        db=db,
        user_id=current_user,
        house_id=house_id,
    )


    return get_all_goals_repo(db, current_user, house_id)
# ==========================================================
# GET ALL ACTIVE GOALS (AUTO UPDATE)
# ==========================================================

@router.get("/active", response_model=List[Dict[str, Any]])
def get_active_goals(
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):
    """
    Recalcula automaticamente todas as metas ativas.
    """


    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa."
        )

    goals = evaluate_all_active_goals(
        db=db,
        user_id=current_user,
        house_id=house_id,
    )

    return goals



# DELETE GOAL


@router.delete("/{goal_id}", response_model=Dict[str, Any])
def delete_goal(
    goal_id: int,
    db=Depends(get_db),
    current_user: int = Depends(get_current_user),
    house_id: int = Depends(get_current_house_id),
):


    if not house_belongs_to_user(db, current_user, house_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta casa."
        )

    try:
        return remove_goal(
            db=db,
            goal_id=goal_id,
            user_id=current_user,
            house_id=house_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
