# backend/app/services/auth_service.py
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

from app.repositories.user_repository import get_user_by_google_id, create_google_user

# =====================================================
# LOGIN
# =====================================================

def login_user(db, username: str, password: str) -> str:
    logger.info(f"Tentativa de login: {username}")

    user = get_user_by_username(db, username) or get_user_by_email(db, username)

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


def login_google_user(db, google_token: str):
    from google.oauth2 import id_token
    from google.auth.transport import requests

    try:
        # 🔐 validar token com Google
        idinfo = id_token.verify_oauth2_token(
            google_token,
            requests.Request()
        )

        google_id = idinfo["sub"]
        email = idinfo.get("email")
        name = idinfo.get("name", "")

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google inválido",
        )

    # 🔍 1. procurar por google_id
    user = get_user_by_google_id(db, google_id)

    # 🧠 2. se não existir, tentar por email
    if not user and email:
        user = get_user_by_email(db, email)

        if user:
            # 🔗 ligar conta existente ao Google
            cursor = db.cursor()
            try:
                cursor.execute(
                    "UPDATE users SET google_id=%s WHERE id_user=%s",
                    (google_id, user["id_user"]),
                )
                db.commit()
            finally:
                cursor.close()

    # 👤 3. se ainda não existir → criar novo
    if not user:
        username = f"{email.split('@')[0]}_{google_id[:4]}" if email else f"user_{google_id[:6]}"

        user_id = create_google_user(
            db,
            username=username,
            email=email,
            google_id=google_id,
        )

        # 🔥 criar plano FREE
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO subscriptions (id_user, id_plan, start_date, is_active)
                VALUES (%s, %s, CURDATE(), 1)
                """,
                (user_id, 4)
            )
            db.commit()
        finally:
            cursor.close()

        user = {"id_user": user_id}

    # 🔐 tokens
    access_token = create_access_token(str(user["id_user"]))
    refresh_token = create_refresh_token(str(user["id_user"]))

    # 🔐 guardar hash do refresh
    hashed_refresh = hash_password(refresh_token)
    save_refresh_token(db, int(user["id_user"]), hashed_refresh)

    return access_token, refresh_token