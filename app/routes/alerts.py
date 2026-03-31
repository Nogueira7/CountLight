from fastapi import APIRouter, Depends, HTTPException, Header

from app.db.database import get_db
from app.core.security import get_current_user

from app.services.alert_service import (
    get_peak_power_alert,
    get_consumption_pattern_alert,
    get_device_on_too_long_alert,
    get_night_consumption_alert,
    get_data_quality_alert
)

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


@router.get("")
def get_alerts(
    db=Depends(get_db),
    user_id: int = Depends(get_current_user),
    house_id: int = Header(..., alias="X-House-Id"),
):
    try:

        # Pico de potência
        peak_power_alert = get_peak_power_alert(
            db,
            user_id,
            house_id
        )

        # Consumo fora do padrão
        consumption_pattern_alert = get_consumption_pattern_alert(
            db,
            user_id,
            house_id
        )

        # Dispositivo ligado demasiado tempo
        device_on_too_long_alert = get_device_on_too_long_alert(
            db,
            house_id
        )

        # Consumo noturno
        night_consumption_alert = get_night_consumption_alert(
            db,
            house_id
        )

        # Qualidade de dados e conectividade
        data_quality_alert = get_data_quality_alert(
            db,
            house_id
        )

        return {
            "peak_power": peak_power_alert,
            "consumption_pattern": consumption_pattern_alert,
            "device_on_too_long": device_on_too_long_alert,
            "night_consumption": night_consumption_alert,
            "data_quality": data_quality_alert
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Alert error: {str(e)}"
        )