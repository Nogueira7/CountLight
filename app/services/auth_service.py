from fastapi import HTTPException, status
from datetime import datetime, timedelta
import secrets

from app.core.logging import logger
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
)
from app.repositories.user_repository import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    save_refresh_token,
)

from app.core.email import send_verification_email

# =====================================================
# LOGIN
# =====================================================

def login_user(db, username: str, password: str) -> str:
    logger.info(f"Tentativa de login: {username}")

    user = get_user_by_username(db, username)

    if not user or not verify_password(password, user["password_hash"]):
        logger.warning(f"Login falhado: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login inválido",
        )

    if not user.get("is_active"):
        logger.warning(f"Tentativa de login em conta desativada: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada",
        )

    # 🔒 Bloquear login sem email verificado
    # (assume que o user_repository já devolve is_verified)
    if not user.get("is_verified"):
        logger.warning(f"Tentativa de login sem email verificado: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirma o teu email antes de fazer login",
        )

    access_token = create_access_token(str(user["id_user"]))
    refresh_token = create_refresh_token(str(user["id_user"]))

    save_refresh_token(db, int(user["id_user"]), refresh_token)

    logger.info(f"Login bem-sucedido: {username}")

    return access_token


# =====================================================
# REGISTER
# =====================================================

def register_user(db, username: str, email: str, password: str) -> int:
    logger.info(f"Tentativa de registo: {username}")

    if get_user_by_username(db, username):
        logger.warning(f"Registo falhado (username existente): {username}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username já existe",
        )

    if get_user_by_email(db, email):
        logger.warning(f"Registo falhado (email existente): {email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já registado",
        )

    password_hash = hash_password(password)

    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.utcnow() + timedelta(hours=24)

    user_id = create_user(
    db,
    username,
    email,
    password_hash,
    verification_token,
    verification_expires,
)

    logger.info(f"Utilizador registado com sucesso: {username}")
    logger.info(f"Token de verificação criado para: {email}")
    try:
        send_verification_email(email, verification_token)
        logger.info(f"Email enviado para: {email}")
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")

    return user_id