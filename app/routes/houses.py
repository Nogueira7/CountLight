# backend/app/routes/houses.py

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.database import get_db
from app.repositories.house_repository import (
    create_house,
    deactivate_house,
    get_house_by_id,
    get_house_full,
    get_houses_by_user,
    update_house,
)

from app.routes.plans import get_my_plan

router = APIRouter(prefix="/houses", tags=["Houses"])

HOUSE_TYPES = {"apartamento", "moradia"}
OCCUPANCY_TYPES = {"permanente", "parcial", "ferias"}



def _pick(data: dict, *keys, default=None):
    """Devolve o primeiro valor não-nulo encontrado em data[key]."""
    for k in keys:
        if k in data and data.get(k) is not None:
            return data.get(k)
    return default


def _require_str(value, field_name: str) -> str:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campos obrigatórios em falta",
        )
    s = str(value).strip()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campos obrigatórios em falta",
        )
    return s


def _to_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor inválido (inteiro esperado)",
        )


def _to_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        if isinstance(value, str):
            value = value.replace(",", ".")  # aceitar "0,18"
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor inválido (número esperado)",
        )


def _validate_enum(value: str, allowed: set[str], field: str) -> str:
    v = str(value).strip()
    if v not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor inválido para {field}. Valores aceites: {','.join(sorted(allowed))}",
        )
    return v


def _validate_non_negative(value, field: str):
    if value is None:
        return None
    if not isinstance(value, (int, float)) or value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor inválido para {field} (tem de ser >= 0)",
        )
    return value



# GET /houses

@router.get("")
def list_houses(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    return get_houses_by_user(db, user_id)



# GET /houses/{id_house}

@router.get("/{id_house}")
def get_house(
    id_house: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    house = get_house_by_id(db, id_house, user_id)
    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Casa não encontrada",
        )
    return house



# POST /houses

@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_house(
    data: dict,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    

    houses = get_houses_by_user(db, user_id)
    plan = get_my_plan(user_id=user_id, db=db)

    if len(houses) >= plan["max_houses"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Atingiste o limite de casas do teu plano. Faz upgrade para adicionar mais.",
        )
    
    print("DATA RECEBIDA (CREATE):", data)

    nome = _require_str(_pick(data, "nome", "name"), "nome")

    tipo_casa_raw = _pick(data, "tipo_casa", "house_type", default=None)
    tipo_ocupacao_raw = _pick(data, "tipo_ocupacao", "occupancy_type", default=None)

    tipo_casa = (
        _validate_enum(tipo_casa_raw, HOUSE_TYPES, "tipo_casa/house_type")
        if tipo_casa_raw is not None
        else None
    )
    tipo_ocupacao = (
        _validate_enum(tipo_ocupacao_raw, OCCUPANCY_TYPES, "tipo_ocupacao/occupancy_type")
        if tipo_ocupacao_raw is not None
        else None
    )

    address = _pick(data, "morada", "address", default=None)
    adults = _to_int(_pick(data, "adultos", "adults", default=0), default=0)
    children = _to_int(_pick(data, "criancas", "children", default=0), default=0)
    provider = _pick(data, "comercializadora", "provider", default=None)
    tariff = _pick(data, "tarifa", "tariff", default=None)
    contract_power = _to_float(_pick(data, "potencia_contratada", "contract_power", default=None), default=None)
    monthly_kwh = _to_float(_pick(data, "consumo_kwh_mes", "monthly_kwh", default=None), default=None)

    price_per_kwh = _to_float(_pick(data, "preco_kwh", "price_per_kwh", default=None), default=None)

    _validate_non_negative(adults, "adultos/adults")
    _validate_non_negative(children, "criancas/children")
    _validate_non_negative(contract_power, "potencia_contratada/contract_power")
    _validate_non_negative(monthly_kwh, "consumo_kwh_mes/monthly_kwh")
    _validate_non_negative(price_per_kwh, "preco_kwh/price_per_kwh")

    try:
        house_id = create_house(
            db=db,
            user_id=user_id,
            name=nome,
            address=address,
            house_type=tipo_casa,
            adults=adults,
            children=children,
            occupancy_type=tipo_ocupacao,
            provider=provider,
            tariff=tariff,
            contract_power=contract_power,
            monthly_kwh=monthly_kwh,
            price_per_kwh=price_per_kwh,  # <- requer update no repository/model/DB
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao criar casa: {str(e)}",
        )

    return {
        "message": "Casa criada com sucesso",
        "id_house": house_id,
    }



# PUT /houses/{id_house}

@router.put("/{id_house}")
def update_existing_house(
    id_house: int,
    data: dict,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    print("DATA RECEBIDA (UPDATE):", data)

    nome = _require_str(_pick(data, "nome", "name"), "nome")

    tipo_casa_raw = _pick(data, "tipo_casa", "house_type", default=None)
    tipo_ocupacao_raw = _pick(data, "tipo_ocupacao", "occupancy_type", default=None)

    tipo_casa = (
        _validate_enum(tipo_casa_raw, HOUSE_TYPES, "tipo_casa/house_type")
        if tipo_casa_raw is not None
        else None
    )
    tipo_ocupacao = (
        _validate_enum(tipo_ocupacao_raw, OCCUPANCY_TYPES, "tipo_ocupacao/occupancy_type")
        if tipo_ocupacao_raw is not None
        else None
    )

    address = _pick(data, "morada", "address", default=None)
    adults = _to_int(_pick(data, "adultos", "adults", default=0), default=0)
    children = _to_int(_pick(data, "criancas", "children", default=0), default=0)
    provider = _pick(data, "comercializadora", "provider", default=None)
    tariff = _pick(data, "tarifa", "tariff", default=None)
    contract_power = _to_float(_pick(data, "potencia_contratada", "contract_power", default=None), default=None)
    monthly_kwh = _to_float(_pick(data, "consumo_kwh_mes", "monthly_kwh", default=None), default=None)

    price_per_kwh = _to_float(_pick(data, "preco_kwh", "price_per_kwh", default=None), default=None)

    _validate_non_negative(adults, "adultos/adults")
    _validate_non_negative(children, "criancas/children")
    _validate_non_negative(contract_power, "potencia_contratada/contract_power")
    _validate_non_negative(monthly_kwh, "consumo_kwh_mes/monthly_kwh")
    _validate_non_negative(price_per_kwh, "preco_kwh/price_per_kwh")

    try:
        updated = update_house(
            db=db,
            id_house=id_house,
            user_id=user_id,
            name=nome,
            address=address,
            house_type=tipo_casa,
            adults=adults,
            children=children,
            occupancy_type=tipo_ocupacao,
            provider=provider,
            tariff=tariff,
            contract_power=contract_power,
            monthly_kwh=monthly_kwh,
            price_per_kwh=price_per_kwh,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao atualizar casa: {str(e)}",
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Casa não encontrada ou não pertence ao utilizador",
        )

    return {"message": "Casa atualizada com sucesso"}



# GET /houses/{id_house}/full

@router.get("/{id_house}/full")
def get_house_full_route(
    id_house: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    house = get_house_full(db, id_house, user_id)
    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Casa não encontrada ou não pertence ao utilizador",
        )
    return house



# PATCH /houses/{id_house}/deactivate

@router.patch("/{id_house}/deactivate")
def deactivate_house_route(
    id_house: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    updated = deactivate_house(db, id_house, user_id)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Casa não encontrada ou não pertence ao utilizador",
        )

    return {"message": "Casa desativada com sucesso"}
