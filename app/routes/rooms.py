# backend/app/routes/rooms.py

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.database import get_db
from app.repositories.room_repository import (
    get_rooms_by_house,
    get_room_by_id,
    create_room,
    delete_room,
    update_room,  # NOVO
    get_room_month_percentage,
)
from app.repositories.energy_repository import (
    get_room_total_consumption_for_period,
    get_room_estimated_month_cost,
    get_energy_summary_by_device,
    get_hourly_consumption_today,
    get_room_consumption_by_device_type,
)
from app.repositories.energy_repository import get_room_monthly_comparison

router = APIRouter(tags=["Rooms"])


# =========================
# Helpers
# =========================
def _require_str(value, field: str = "Nome da divisão") -> str:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} é obrigatório",
        )
    s = str(value).strip()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} é obrigatório",
        )
    return s


# =========================
# GET /houses/{id_house}/rooms
# =========================
@router.get("/houses/{id_house}/rooms")
def list_rooms(
    id_house: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    return get_rooms_by_house(db, id_house, user_id)


# =========================
# GET /rooms/{id_room}
# =========================
@router.get("/rooms/{id_room}")
def get_room(
    id_room: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    room = get_room_by_id(db, id_room, user_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada",
        )
    return room


# =========================
# POST /houses/{id_house}/rooms
# =========================
@router.post(
    "/houses/{id_house}/rooms",
    status_code=status.HTTP_201_CREATED,
)
def create_new_room(
    id_house: int,
    data: dict,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    print("DATA RECEBIDA (CREATE ROOM):", data)

    name = _require_str(data.get("name") or data.get("nome"))

    room_id = create_room(
        db=db,
        id_house=id_house,
        user_id=user_id,
        name=name,
    )

    if room_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Casa não encontrada ou não pertence ao utilizador",
        )

    return {
        "message": "Divisão criada com sucesso",
        "id_room": room_id,
    }


# =========================
# PUT /rooms/{id_room}
# =========================
@router.put("/rooms/{id_room}")
def update_existing_room(
    id_room: int,
    data: dict,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    print("DATA RECEBIDA (UPDATE ROOM):", data)

    name = _require_str(data.get("name") or data.get("nome"))

    updated = update_room(
        db=db,
        id_room=id_room,
        user_id=user_id,
        name=name,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada ou não pertence ao utilizador",
        )

    return {"message": "Divisão atualizada com sucesso"}


# =========================
# DELETE /rooms/{id_room}
# =========================
@router.delete("/rooms/{id_room}")
def delete_existing_room(
    id_room: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    deleted = delete_room(db, id_room, user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada ou não pertence ao utilizador",
        )

    return {"message": "Divisão apagada com sucesso"}


# =========================
# GET /api/rooms (para sidebar)
# =========================
# ⚠️ IMPORTANTE:
# Antes:
#   - Usava "/api/rooms" → virava "/api/api/rooms" (404)
#   - Usava models diretos → dava erro (não existem)
# Agora:
#   - Usa "/rooms" → fica "/api/rooms" (correto)
#   - Usa repositories (como o resto do projeto)

@router.get("/rooms")
def get_rooms_for_sidebar(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Retorna todas as divisões do utilizador
    """

    from app.repositories.house_repository import get_houses_by_user

    houses = get_houses_by_user(db, user_id)

    all_rooms = []

    for house in houses:
        rooms = get_rooms_by_house(db, house["id_house"], user_id)
        all_rooms.extend(rooms)

    return all_rooms


# =========================
# GET /rooms/{id_room}/summary
# =========================
@router.get("/rooms/{id_room}/summary")
def get_room_summary(
    id_room: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve dados agregados da divisão (para statsroom)
    """

    # 🔎 Verificar se a divisão pertence ao utilizador
    room = get_room_by_id(db, id_room, user_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada ou não pertence ao utilizador",
        )

    # 🔢 Consumos
    today_kwh = get_room_total_consumption_for_period(db, user_id, id_room, "today")
    month_kwh = get_room_total_consumption_for_period(db, user_id, id_room, "month")
    year_kwh = get_room_total_consumption_for_period(db, user_id, id_room, "year")

    month_cost = get_room_estimated_month_cost(db, user_id, id_room)

    # 📊 Consumo por dispositivo (apenas desta divisão)
    devices = get_energy_summary_by_device(db, user_id)

    # 📊 Percentagem da divisão face à casa (mês atual)
    percentage = get_room_month_percentage(db, id_room, user_id)

    # 🔥 Hora pico
    hourly = get_hourly_consumption_today(db, user_id)

    peak_hour = "--"
    if hourly and hourly.get("data"):
        peak = max(hourly["data"], key=lambda x: x["value"])
        peak_hour = peak["label"]

    comparison = get_room_monthly_comparison(db, user_id, id_room)

    return {
        "room_name": room["name"],
        "consumption": {
            "today": round(today_kwh or 0, 2),
            "month": round(month_kwh or 0, 2),
            "year": round(year_kwh or 0, 2),
        },
        "cost": {
            "estimated": round(month_cost or 0, 2),
        },
        "percentage_of_house": percentage,
        "peak_hour": peak_hour,
        "devices": devices or [],
        "comparison_last_month": comparison,  # 👈 ESTA LINHA
    }


# =========================
# GET /rooms/{id_room}/device-types
# =========================
@router.get("/rooms/{id_room}/device-types")
def get_room_device_types(
    id_room: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve consumo mensal por tipo de equipamento da divisão
    """

    # 🔎 Verificar se a divisão pertence ao utilizador
    room = get_room_by_id(db, id_room, user_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada ou não pertence ao utilizador",
        )

    data = get_room_consumption_by_device_type(db, id_room)

    return data
