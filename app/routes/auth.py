# backend/app/routes/auth.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import RegisterData
from app.services.auth_service import login_user, register_user

# Nota: manter o teu refresh/logout como está exigiria imports de jwt/SECRET_KEY/ALGORITHM/create_access_token.
# Aqui deixo-os como no teu ficheiro original (assumindo que já existem no projeto).
import jwt  # type: ignore
from app.core.security import SECRET_KEY, ALGORITHM, create_access_token  # ajusta se os teus imports diferirem

from fastapi import HTTPException
from datetime import datetime

from app.repositories.user_repository import (
    get_user_by_verification_token,
    verify_user,
)

import secrets
from datetime import timedelta

from app.repositories.user_repository import get_user_by_email
from app.core.email import send_reset_email
from app.core.security import hash_password

from fastapi import APIRouter, Depends, HTTPException, Form

from fastapi import Request
from app.services.auth_service import login_google_user
from app.core.security import verify_password

import traceback

router = APIRouter()


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    token = login_user(
        db,
        form_data.username,
        form_data.password,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/register")
def register(data: RegisterData, db=Depends(get_db)):
    # criar user
    user_id = register_user(db, data.username, data.email, data.password)

    cursor = db.cursor()
    try:
        # atribuir plano FREE automaticamente
        cursor.execute(
            """
            INSERT INTO subscriptions (id_user, id_plan, start_date, is_active)
            VALUES (%s, %s, CURDATE(), 1)
            """,
            (user_id, 4)  # 4 = free
        )
        db.commit()
    finally:
        cursor.close()

    return {"message": "Conta criada com sucesso"}


@router.get("/me")
def me(user_id: int = Depends(get_current_user)):
    return {"user_id": user_id}



@router.post("/refresh")
def refresh(token: str, db=Depends(get_db)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = payload.get("sub")

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT refresh_token FROM users WHERE id_user=%s",
            (user_id,),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()


    if not user or not verify_password(token, user["refresh_token"]):
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    new_access = create_access_token(user_id)
    return {"access_token": new_access}


@router.post("/logout")
def logout(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE users SET refresh_token=NULL WHERE id_user=%s",
            (user_id,),
        )
        db.commit()
    finally:
        cursor.close()

    return {"message": "Logout efetuado"}

@router.get("/verify")
def verify(token: str, db=Depends(get_db)):
    user = get_user_by_verification_token(db, token)

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    if user["verification_expires"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expirado")

    verify_user(db, user["id_user"])

    return {"message": "Conta verificada com sucesso"}


@router.post("/forgot-password")
def forgot_password(data: dict, db=Depends(get_db)):
    email = data.get("email")

    from app.repositories.user_repository import get_user_by_email
    user = get_user_by_email(db, email)

    # Não revelar se existe ou não
    if not user:
        return {"message": "Se existir, será enviado email"}

    import secrets
    from datetime import datetime, timedelta

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)

    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET reset_token=%s, reset_expires=%s
            WHERE id_user=%s
            """,
            (token, expires, user["id_user"]),
        )
        db.commit()
    finally:
        cursor.close()

    from app.core.email import send_reset_email
    send_reset_email(user["email"], token)

    return {"message": "Email enviado"}


@router.post("/reset-password")
def reset_password(
    token: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id_user, reset_expires
            FROM users
            WHERE reset_token=%s
            """,
            (token,),
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Token inválido")

        if user["reset_expires"] < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token expirado")

        password_hash = hash_password(password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash=%s,
                reset_token=NULL,
                reset_expires=NULL
            WHERE id_user=%s
            """,
            (password_hash, user["id_user"]),
        )
        db.commit()

        return {"message": "Password atualizada"}
    finally:
        cursor.close()

from pydantic import BaseModel

class GoogleAuthRequest(BaseModel):
    token: str


@router.post("/google")
async def google_login(data: GoogleAuthRequest, db=Depends(get_db)):
    token = data.token

    if not token:
        raise HTTPException(status_code=400, detail="Token Google em falta")

    try:
        access_token, refresh_token = login_google_user(db, token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    except Exception as e:
        traceback.print_exc()  # 🔥 aparece no journalctl
        raise HTTPException(status_code=500, detail=str(e))