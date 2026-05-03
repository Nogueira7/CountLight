# backend/app/models/user.py
from __future__ import annotations

import re
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

# AUTH

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]+$")


class LoginData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str = Field(..., min_length=3, max_length=50)
    password: str


class RegisterData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if not USERNAME_PATTERN.match(v):
            raise ValueError("Username só pode conter letras, números, ponto, underscore e hífen")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        v = v or ""
        if len(v) < 8:
            raise ValueError("Password deve ter pelo menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password deve conter pelo menos uma letra maiúscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password deve conter pelo menos uma letra minúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password deve conter pelo menos um número")
        return v

# PROFILE (responses)

class UserMeResponse(BaseModel):
    """
    Resposta de GET /users/me
    """
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    # Para compatibilidade: alguns endpoints podem mandar id e/ou id_user
    id: Optional[int] = None
    id_user: int

    username: str
    email: EmailStr
    description: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: int = 1


class UserPublicResponse(BaseModel):
    """
    Resposta de GET /users/{user_id} (perfil de outras pessoas).
    Por defeito não inclui email.
    """
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    id_user: int
    username: str
    description: Optional[str] = None
    photo_url: Optional[str] = None


class UserSuggestion(BaseModel):
    """
    Item da resposta de GET /users/suggestions
    """
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    # Pode vir None se a normalização no endpoint não conseguir converter para int
    id: Optional[int] = None
    username: str = ""
    photo_url: Optional[str] = None
    total_saved_eur: Optional[float] = None


class UserSuggestionsResponse(BaseModel):
    """
    Se preferires devolver um objeto em vez de lista direta:
      { "items": [...] }
    NOTA: só uses isto se mudares a rota.
    """
    model_config = ConfigDict(extra="ignore")

    items: List[UserSuggestion]

# SEARCH BAR

class UserSearchItem(BaseModel):
    """
    Item de GET /users/search
    """
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    username: str
    photo_url: Optional[str] = None


class UserSearchResponse(BaseModel):
    """
    Se quiseres devolver objeto:
      { "items": [...] }
    (opcional; podes continuar a devolver lista direta)
    """
    model_config = ConfigDict(extra="ignore")

    items: List[UserSearchItem]

class LatestAchievement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = None
    description: Optional[str] = None
    completed_at: Optional[str] = None  # ISO string


class UserImpactTotals(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_houses: int = 0
    total_devices: int = 0
    total_energy_kwh: float = 0.0
    total_saved_eur: float = 0.0
    total_achievements: int = 0
    completed_achievements: int = 0
    in_progress_achievements: int = 0


class UserImpactResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    totals: UserImpactTotals
    latest_achievement: Optional[LatestAchievement] = None
