# backend/app/services/auth_service.py
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import secrets
import random

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

from app.core.email import send_verification_email, send_login_code_email

from app.repositories.user_repository import get_user_by_google_id, create_google_user

from app.core.email import send_login_code_email


# =====================================================
# LOGIN (PASSO 1 - CREDENCIAIS)
# =====================================================

def login_user(db, username: str, password: str):
    logger.info(f"Tentativa de login: {username}")

    user = get_user_by_username(db, username) or get_user_by_email(db, username)

    # 🔒 credenciais inválidas
    if not user or not verify_password(password, user["password_hash"]):
        logger.warning(f"Login falhado: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login inválido",
        )

    # 🔒 conta desativada
    if not user.get("is_active"):
        logger.warning(f"Tentativa de login em conta desativada: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada",
        )

    # 🔒 email não verificado
    if not user.get("is_verified"):
        logger.warning(f"Tentativa de login sem email verificado: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirma o teu email antes de fazer login",
        )

    # =====================================================
    # 🔐 GERAR CÓDIGO 2FA
    # =====================================================

    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=5)

    # 💾 guardar código na DB
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET login_code=%s, login_expires=%s
            WHERE id_user=%s
            """,
            (code, expires, user["id_user"]),
        )
        db.commit()
    finally:
        cursor.close()

    # 📧 enviar email
    try:
        send_login_code_email(user["email"], code)
        logger.info(f"Código 2FA enviado para: {user['email']}")
    except Exception as e:
        logger.error(f"Erro ao enviar código 2FA: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao enviar código",
        )

    logger.info(f"Login fase 1 concluída (aguarda 2FA): {username}")

    # 👉 ainda NÃO autenticado
    return {
        "2fa_required": True,
        "user_id": user["id_user"]
    }


# =====================================================
# LOGIN (PASSO 2 - VERIFICAR CÓDIGO)
# =====================================================

def verify_login_code(db, user_id: int, code: str):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT login_code, login_expires
            FROM users
            WHERE id_user=%s
            """,
            (user_id,),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()

    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")

    # 🔒 código errado
    if not user["login_code"] or user["login_code"] != code:
        raise HTTPException(status_code=401, detail="Código inválido")

    # 🔒 código expirado
    if user["login_expires"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Código expirado")

    # 🔑 criar tokens
    access_token = create_access_token(str(user_id))
    refresh_token = create_refresh_token(str(user_id))

    # 🔐 guardar refresh token
    hashed_refresh = hash_password(refresh_token)
    save_refresh_token(db, user_id, hashed_refresh)

    # 🧹 limpar código usado
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET login_code=NULL, login_expires=NULL
            WHERE id_user=%s
            """,
            (user_id,),
        )
        db.commit()
    finally:
        cursor.close()

    logger.info(f"Login completo com 2FA: user_id={user_id}")

    return access_token, refresh_token


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

    try:
        send_verification_email(email, verification_token)
        logger.info(f"Email enviado para: {email}")
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")

    return user_id


# =====================================================
# LOGIN GOOGLE (SEM 2FA)
# =====================================================

def login_google_user(db, google_token: str):
    from google.oauth2 import id_token
    from google.auth.transport import requests

    try:
        idinfo = id_token.verify_oauth2_token(
            google_token,
            requests.Request()
        )

        google_id = idinfo["sub"]
        email = idinfo.get("email")

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google inválido",
        )

    user = get_user_by_google_id(db, google_id)

    if not user and email:
        user = get_user_by_email(db, email)

        if user:
            cursor = db.cursor()
            try:
                cursor.execute(
                    "UPDATE users SET google_id=%s WHERE id_user=%s",
                    (google_id, user["id_user"]),
                )
                db.commit()
            finally:
                cursor.close()

    if not user:
        username = f"{email.split('@')[0]}_{google_id[:4]}" if email else f"user_{google_id[:6]}"

        user_id = create_google_user(
            db,
            username=username,
            email=email,
            google_id=google_id,
        )

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

    access_token = create_access_token(str(user["id_user"]))
    refresh_token = create_refresh_token(str(user["id_user"]))

    hashed_refresh = hash_password(refresh_token)
    save_refresh_token(db, int(user["id_user"]), hashed_refresh)

    return access_token, refresh_token