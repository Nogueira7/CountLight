# backend/app/routes/user.py
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
)

from app.core.security import get_current_user
from app.db.database import get_db
from app.repositories.user_repository import (
    get_user_profile,
    update_user_profile,
    get_user_impact,
    is_username_taken,
    is_email_taken,
    update_user_account,
    get_user_suggestions,
    search_users_by_username,  # ✅ NOVO (barra de pesquisa)
)

router = APIRouter(prefix="/users", tags=["Users"])

# ==========================================================
# CONFIG (uploads)
# ==========================================================

# Este ficheiro está em: backend/app/routes/user.py
# app_dir -> backend/app
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ajusta conforme o teu projeto:
# - Se o teu static está dentro de backend/app/static (como o teu HTML sugere /static/...)
STATIC_DIR = os.path.join(APP_DIR, "static")

UPLOAD_DIR = os.path.join(STATIC_DIR, "images", "profile_photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2MB

USERNAME_RE = re.compile(r"^[a-z0-9_.-]+$")

# ==========================================================
# UTIL - EXTRACT USER ID
# ==========================================================


def extract_user_id(current_user: Any) -> int:
    """
    Suporta vários formatos do get_current_user:
    - int
    - dict com user_id / id_user / id
    - objeto com user_id / id_user / id
    """
    user_id: Any = None

    if isinstance(current_user, int):
        user_id = current_user
    elif isinstance(current_user, dict):
        user_id = current_user.get("user_id") or current_user.get("id_user") or current_user.get("id")
    else:
        user_id = (
            getattr(current_user, "user_id", None)
            or getattr(current_user, "id_user", None)
            or getattr(current_user, "id", None)
        )

    try:
        user_id_int = int(user_id)
    except Exception:
        user_id_int = 0

    if user_id_int <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível obter o id do utilizador a partir do token.",
        )

    return user_id_int


def _normalize_username(v: str) -> str:
    v = (v or "").strip().lower()
    if len(v) < 3 or len(v) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username deve ter entre 3 e 50 caracteres.",
        )
    if not USERNAME_RE.match(v):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username só pode conter letras minúsculas, números, ponto, underscore e hífen.",
        )
    return v


def _normalize_email(v: str) -> str:
    v = (v or "").strip().lower()
    if len(v) < 3 or len(v) > 100 or "@" not in v:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido.",
        )
    return v


def _safe_join_under(base_dir: str, rel_path: str) -> Optional[str]:
    """
    Constrói um caminho absoluto garantindo que fica dentro de base_dir.
    Se não ficar, devolve None.
    """
    if not rel_path:
        return None
    rel_path = rel_path.lstrip("/").replace("\\", "/")
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(os.path.join(abs_base, rel_path))
    if os.path.commonpath([abs_base, abs_target]) != abs_base:
        return None
    return abs_target


# ==========================================================
# GET PROFILE (SELF)
# ==========================================================


@router.get("/me")
def get_me(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve dados do utilizador + perfil.
    NOTA: stats/impact em /users/me/impact.
    """
    user_id = extract_user_id(current_user)

    profile = get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado.",
        )

    return {
        "id": profile["id_user"],
        "id_user": profile["id_user"],
        "username": profile["username"],
        "email": profile["email"],
        "description": profile.get("description"),
        "photo_url": profile.get("photo_url"),
        "is_active": profile.get("is_active", 1),
    }


# ==========================================================
# GET IMPACT (SELF)
# ==========================================================


@router.get("/me/impact")
def get_me_impact(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    user_id = extract_user_id(current_user)

    profile = get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado.",
        )

    return get_user_impact(db, user_id)


# ==========================================================
# PEOPLE YOU MAY KNOW (Sugestões)
# ⚠️ Tem de vir ANTES de /{user_id}
# ==========================================================


@router.get("/suggestions")
def get_suggestions(
    limit: int = Query(4, ge=1, le=20),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devolve uma lista (até `limit`) de utilizadores sugeridos.

    Formato de retorno pensado para o front-end:
      [
        {
          "id": 123,
          "username": "joao",
          "photo_url": "images/profile_photos/user_123_20250101_120000.jpg",
          "total_saved_eur": 85.10
        }
      ]
    """
    user_id = extract_user_id(current_user)

    try:
        suggestions = get_user_suggestions(db, exclude_user_id=user_id, limit=limit)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter sugestões.",
        )

    out: List[Dict[str, Any]] = []
    for row in (suggestions or []):
        raw_id = row.get("id") or row.get("id_user") or row.get("user_id")
        try:
            norm_id = int(raw_id) if raw_id is not None else None
        except Exception:
            norm_id = None

        out.append(
            {
                "id": norm_id,
                "username": (row.get("username") or "").strip(),
                "photo_url": row.get("photo_url"),
                "total_saved_eur": row.get("total_saved_eur"),
            }
        )

    return out[:limit]


# ==========================================================
# SEARCH USERS (para a barra de pesquisa no header) ✅ NOVO
# ⚠️ Tem de vir ANTES de /{user_id}
# ==========================================================


@router.get("/search")
def search_users(
    q: str = Query("", min_length=1, max_length=50),
    limit: int = Query(8, ge=1, le=20),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
) -> List[Dict[str, Any]]:
    requester_id = extract_user_id(current_user)

    try:
        rows = search_users_by_username(db, q=q, limit=limit, exclude_user_id=requester_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao pesquisar utilizadores.",
        )

    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            uid = int(r.get("id_user"))
        except Exception:
            continue

        out.append(
            {
                "id": uid,
                "username": (r.get("username") or "").strip(),
                "photo_url": r.get("photo_url"),
            }
        )

    return out


# ==========================================================
# GET IMPACT (OTHER USER)
# (põe antes de /{user_id} por clareza)
# ==========================================================


@router.get("/{user_id}/impact")
def get_user_impact_by_id(
    user_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    _ = extract_user_id(current_user)

    profile = get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado.",
        )

    return get_user_impact(db, user_id)


# ==========================================================
# GET PROFILE (OTHER USER)
# ==========================================================


@router.get("/{user_id}")
def get_user_by_id(
    user_id: int,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Devolve dados do perfil de outro utilizador (dados "públicos").
    Por defeito não devolvemos email.
    """
    _ = extract_user_id(current_user)

    profile = get_user_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado.",
        )

    return {
        "id": profile["id_user"],
        "id_user": profile["id_user"],
        "username": profile["username"],
        "description": profile.get("description"),
        "photo_url": profile.get("photo_url"),
    }


# ==========================================================
# UPDATE PROFILE (USERNAME + EMAIL + DESCRIPTION + PHOTO)
# (multipart/form-data)
# ==========================================================


@router.put("/me")
async def update_me(
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    user_id = extract_user_id(current_user)

    # strings vazias => None (não altera)
    if username is not None:
        username = username.strip() or None
    if email is not None:
        email = email.strip() or None
    if description is not None:
        description = description.strip() or None

    # validar + unicidade
    if username is not None:
        username = _normalize_username(username)
        if is_username_taken(db, username, exclude_user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username já está a ser usado.",
            )

    if email is not None:
        email = _normalize_email(email)
        if is_email_taken(db, email, exclude_user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já está a ser usado.",
            )

    # Foto (opcional)
    photo_url: Optional[str] = None
    if photo is not None:
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato inválido. Apenas JPEG, PNG ou WEBP.",
            )

        contents = await photo.read()
        try:
            await photo.close()
        except Exception:
            pass

        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagem demasiado grande (máx 2MB).",
            )

        filename = (photo.filename or "").strip()
        extension = ""
        if "." in filename:
            extension = filename.rsplit(".", 1)[-1].lower()

        if extension not in {"jpg", "jpeg", "png", "webp"}:
            extension = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }.get(photo.content_type, "jpg")

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = f"user_{user_id}_{ts}.{extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        # apagar foto antiga (se existir) — só se estiver dentro do STATIC_DIR
        existing_profile = get_user_profile(db, user_id)
        if existing_profile and existing_profile.get("photo_url"):
            old_rel = str(existing_profile["photo_url"]).lstrip("/")
            old_abs = _safe_join_under(STATIC_DIR, old_rel)
            if old_abs and os.path.exists(old_abs):
                try:
                    os.remove(old_abs)
                except Exception:
                    pass

        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        # Guardamos relativo ao /static
        photo_url = f"images/profile_photos/{safe_name}"

    # Atualizar tabela users (username/email)
    if username is not None or email is not None:
        try:
            update_user_account(db, user_id, username=username, email=email)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    # Atualizar tabela user_profiles (description/photo_url)
    if description is not None or photo_url is not None:
        update_user_profile(
            db=db,
            user_id=user_id,
            description=description,
            photo_url=photo_url,
        )

    return {"message": "Perfil atualizado com sucesso."}


# ==========================================================
# DEACTIVATE ACCOUNT
# ==========================================================


@router.patch("/me/deactivate")
def deactivate_me(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    user_id = extract_user_id(current_user)

    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE users SET is_active=0 WHERE id_user=%s",
            (user_id,),
        )
        db.commit()
        updated = cursor.rowcount
        cursor.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao desativar conta: {str(e)}",
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizador não encontrado.",
        )

    return {"message": "Conta desativada com sucesso."}