# backend/app/routes/devices.py

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.database import get_db
from app.repositories.device_repository import update_device
from app.repositories.device_repository import (
    get_devices_by_room,
    get_device_by_shelly_id_for_user,
    create_device,
    delete_device,
)
ALLOWED_DEVICE_TYPES = {
    "Eletrodomésticos",
    "Climatização",
    "Iluminação",
    "Entretenimento",
    "Eletrónica e Entretenimento",
    "Utensílios",
    "Outros",
}


router = APIRouter(tags=["Devices"])


# =========================
# Helpers
# =========================
def _require_str(value, field: str) -> str:
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


def _normalize_energy_class(value):
    """
    A BD só aceita A-G ou NULL (enum).
    """
    if value is None:
        return None
    s = str(value).strip().upper()
    if s == "" or s in {"NAO_SEI", "NÃO SEI", "NAOSEI"}:
        return None
    if s not in {"A", "B", "C", "D", "E", "F", "G"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="energy_class inválida (use A-G ou vazio)",
        )
    return s

def _normalize_device_type(value):
    if value is None:
        return None

    s = str(value).strip()

    if s == "":
        return None

    if s not in ALLOWED_DEVICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="device_type inválido",
        )

    return s



# =========================
# GET /rooms/{id_room}/devices
# =========================
@router.get("/rooms/{id_room}/devices")
def list_devices(
    id_room: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    return get_devices_by_room(db, id_room, user_id)


# =========================
# GET /devices/by-shelly/{shelly_id}
# (seguro: só devolve se pertencer ao utilizador)
# =========================
@router.get("/devices/by-shelly/{shelly_id}")
def get_device_by_shelly(
    shelly_id: str,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    shelly_id = _require_str(shelly_id, "Shelly ID")

    device = get_device_by_shelly_id_for_user(db, user_id, shelly_id)

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado",
        )

    return device


# =========================
# POST /rooms/{id_room}/devices
# =========================
@router.post(
    "/rooms/{id_room}/devices",
    status_code=status.HTTP_201_CREATED,
)
def create_new_device(
    id_room: int,
    data: dict,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    print("DATA RECEBIDA (CREATE DEVICE):", data)

    name = _require_str(data.get("name") or data.get("nome"), "Nome")

    # aceitar variações comuns, mantendo compatibilidade
    shelly_id = _require_str(
        data.get("shelly_id") or data.get("shellyId") or data.get("id_shelly"),
        "Shelly ID",
    )

    device_type_raw = data.get("device_type") or data.get("tipo")
    device_type = _normalize_device_type(device_type_raw)

    energy_class = _normalize_energy_class(data.get("energy_class") or data.get("classe"))

    device_id, error = create_device(
        db=db,
        id_room=id_room,
        user_id=user_id,
        name=name,
        shelly_id=shelly_id,
        device_type=device_type,
        energy_class=energy_class,
    )

    if error == "ROOM_NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Divisão não encontrada ou não pertence ao utilizador",
        )

    if error == "SHELLY_EXISTS":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este Shelly já está associado a uma divisão",
        )

    if device_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao criar dispositivo",
        )

    return {
        "message": "Dispositivo criado com sucesso",
        "id_device": device_id,
    }


# =========================
# DELETE /devices/{id_device}
# =========================
@router.delete("/devices/{id_device}")
def delete_existing_device(
    id_device: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    deleted = delete_device(db, id_device, user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado ou não pertence ao utilizador",
        )

    return {"message": "Dispositivo apagado com sucesso"}

@router.put("/devices/{id_device}")
def update_existing_device(
    id_device: int,
    data: dict,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    name = _require_str(data.get("name") or data.get("nome"), "Nome")

    device_type_raw = data.get("device_type") or data.get("tipo")
    device_type = _normalize_device_type(device_type_raw)

    energy_class = _normalize_energy_class(
        data.get("energy_class") or data.get("classe")
    )

    updated = update_device(
        db=db,
        id_device=id_device,
        user_id=user_id,
        name=name,
        device_type=device_type,
        energy_class=energy_class,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo não encontrado ou não pertence ao utilizador",
        )

    return {"message": "Dispositivo atualizado com sucesso"}
