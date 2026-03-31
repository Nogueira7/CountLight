from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/plans", tags=["plans"])


# ===============================
# GET ME
# ===============================
@router.get("/me")
def get_my_plan(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 
                p.id_plan,
                p.name,
                p.max_houses
            FROM subscriptions s
            JOIN plans p ON p.id_plan = s.id_plan
            WHERE s.id_user = %s AND s.is_active = 1
            LIMIT 1
            """,
            (user_id,),
        )

        plan = cursor.fetchone()

        # 🔐 fallback seguro (FREE)
        if not plan:
            return {
                "plan": "free",
                "plan_id": 1,
                "max_houses": 1
            }

        return {
            "plan": plan["name"],
            "plan_id": plan["id_plan"],
            "max_houses": plan["max_houses"]
        }

    finally:
        cursor.close()


# ===============================
# 🔥 SUBSCRIBE
# ===============================
@router.post("/subscribe")
def subscribe_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db)
):
    cursor = db.cursor()

    try:
        # 🔒 validar se plano existe
        cursor.execute(
            "SELECT id_plan FROM plans WHERE id_plan = %s",
            (plan_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Plano não existe")

        # 🔴 desativar plano atual
        cursor.execute(
            """
            UPDATE subscriptions
            SET is_active = 0,
                end_date = CURDATE()
            WHERE id_user = %s AND is_active = 1
            """,
            (user_id,)
        )

        # 🟢 criar novo plano
        cursor.execute(
            """
            INSERT INTO subscriptions (id_user, id_plan, start_date, is_active)
            VALUES (%s, %s, CURDATE(), 1)
            """,
            (user_id, plan_id)
        )

        db.commit()

        return {
            "success": True,
            "message": "Plano atualizado com sucesso"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()