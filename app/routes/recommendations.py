from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db
from app.core.security import get_current_user
from app.core.logging import logger

from app.repositories.house_repository import get_user_house_data
from app.services.recommendation_service import (
    get_energy_recommendation,
    get_appliance_recommendation,
    get_time_of_use_recommendation,
    get_cost_recommendation,
)

router = APIRouter(
    prefix="/recommendation",
    tags=["Recommendation"],
)


@router.get("")
def get_recommendation(
    db=Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    try:
        # ============================
        # Buscar dados da casa
        # ============================
        user_data = get_user_house_data(db, user_id)

        logger.info(f"user_data keys: {list(user_data.keys()) if user_data else 'None'}")

        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="House data not found for this user",
            )

        # ============================
        # Recomendações
        # ============================
        tariff = get_energy_recommendation(user_data)
        appliance = get_appliance_recommendation(db, user_id)
        time_of_use = get_time_of_use_recommendation(user_data)
        cost = get_cost_recommendation(user_data)

        # ============================
        # Garantir estrutura correta
        # ============================
        def format_message(value, default_msg):
            if not value:
                return {"message": default_msg}

            if isinstance(value, dict) and "message" in value:
                return value

            return {"message": str(value)}

        # ============================
        # Resposta final
        # ============================
        return {
            "tariff": format_message(
                tariff,
                "Não foi possível calcular a melhor tarifa."
            ),
            "appliance": format_message(
                appliance,
                "Não foi possível analisar os eletrodomésticos."
            ),
            "timeOfUse": format_message(
                time_of_use,
                "Sem dados suficientes para calcular horários mais baratos."
            ),
            "cost": format_message(
                cost,
                "Não foi possível calcular o custo atual."
            ),
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Erro ao gerar recomendações",
        )