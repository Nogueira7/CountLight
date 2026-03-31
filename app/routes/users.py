# backend/app/routes/users.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me/deactivate")
def deactivate_me(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
   
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
            detail="Utilizador não encontrado",
        )

    return {"message": "Conta desativada com sucesso"}