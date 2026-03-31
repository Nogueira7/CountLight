# backend/app/routes/energy.py

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.db.database import get_db
from app.repositories.energy_repository import (
    get_energy_by_device,
    get_latest_energy_by_device,
    get_energy_by_room,
    get_daily_consumption_month_comparison,
)

router = APIRouter(tags=["Energy"])


# =====================================================
# 🔒 Helper — verificar se device pertence ao user
# =====================================================
def _ensure_device_belongs_to_user(db, id_device: int, user_id: int):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE d.id_device = %s
          AND h.id_user = %s
        """,
        (id_device, user_id),
    )
    allowed = cursor.fetchone()
    cursor.close()

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado ou não pertence ao utilizador",
        )


# =====================================================
# GET /devices/{id_device}/energy
# =====================================================
@router.get("/devices/{id_device}/energy")
def list_energy_by_device(
    id_device: int,
    limit: int | None = Query(default=None, ge=1, le=10000),
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve leituras energéticas de um device.
    """

    _ensure_device_belongs_to_user(db, id_device, user_id)

    return get_energy_by_device(db, id_device, limit)


# =====================================================
# GET /devices/{id_device}/energy/latest
# =====================================================
@router.get("/devices/{id_device}/energy/latest")
def get_latest_energy(
    id_device: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve a última leitura energética de um device.
    """

    _ensure_device_belongs_to_user(db, id_device, user_id)

    reading = get_latest_energy_by_device(db, id_device)

    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sem leituras para este dispositivo",
        )

    return reading


# =====================================================
# GET /rooms/{id_room}/energy
# =====================================================
@router.get("/rooms/{id_room}/energy")
def list_energy_by_room(
    id_room: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve leituras energéticas de todos os devices
    de uma divisão.
    """

    readings = get_energy_by_room(db, id_room, user_id)

    # Aqui mantemos 404 porque é recurso específico
    if not readings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada, não pertence ao utilizador ou sem leituras",
        )

    return readings


# =====================================================
# 📊 GET /dashboard/energy/month-comparison
# =====================================================
@router.get("/dashboard/energy/month-comparison")
def get_month_comparison(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve consumo diário (kWh) do mês atual
    comparado com o mês anterior.

    ⚠ Nunca devolve 404.
    Mesmo sem dados devolve arrays com zeros.
    """

    return get_daily_consumption_month_comparison(db, user_id)
