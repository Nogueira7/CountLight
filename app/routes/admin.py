from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])



#VERIFICAR ADMIN

def is_admin(db, user_id: int) -> bool:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.name
            FROM users u
            JOIN roles r ON u.id_role = r.id_role
            WHERE u.id_user = %s
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        return bool(row and row["name"] == "admin")
    finally:
        cursor.close()



# DASHBOARD ADMIN

@router.get("/dashboard")
def get_admin_dashboard(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Acesso negado")

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM users")
        total_users = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM houses")
        total_houses = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM rooms")
        total_rooms = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM devices")
        total_devices = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT id_user, email
            FROM users
            ORDER BY id_user DESC
            LIMIT 5
        """)
        latest_users = cursor.fetchall()

    finally:
        cursor.close()

    return {
        "total_users": total_users,
        "total_houses": total_houses,
        "total_rooms": total_rooms,
        "total_devices": total_devices,
        "latest_users": latest_users,
    }



# LISTAR USERS

@router.get("/users")
def get_users(
    search: str = Query(default=""),
    user_id: int = Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Acesso negado")

    cursor = db.cursor(dictionary=True)

    try:
        query = """
            SELECT 
                id_user, 
                username, 
                email, 
                is_active AS active
            FROM users
            WHERE username LIKE %s
               OR email LIKE %s
               OR CAST(id_user AS CHAR) LIKE %s
            ORDER BY id_user DESC
        """

        search_like = f"%{search}%"
        cursor.execute(query, (search_like, search_like, search_like))

        users = cursor.fetchall()

    finally:
        cursor.close()

    return users



# BLOQUEAR / ATIVAR USER

@router.put("/users/{target_user_id}/toggle")
def toggle_user(
    target_user_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if target_user_id == user_id:
        raise HTTPException(status_code=400, detail="Não podes desativar a tua própria conta")

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT is_active FROM users WHERE id_user = %s",
            (target_user_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User não encontrado")

        new_status = 0 if user["is_active"] == 1 else 1

        cursor.execute(
            "UPDATE users SET is_active = %s WHERE id_user = %s",
            (new_status, target_user_id)
        )
        db.commit()

    finally:
        cursor.close()

    return {
        "message": "Estado atualizado",
        "active": new_status
    }



# DETALHES DO USER

@router.get("/users/{target_user_id}")
def get_user_details(
    target_user_id: int,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_admin(db, user_id):
        raise HTTPException(status_code=403, detail="Acesso negado")

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT 
                id_user, 
                username, 
                email, 
                is_active AS active
            FROM users 
            WHERE id_user = %s
            """,
            (target_user_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User não encontrado")

        cursor.execute(
            "SELECT id_house, name FROM houses WHERE id_user = %s",
            (target_user_id,)
        )
        houses = cursor.fetchall()

        cursor.execute("""
            SELECT r.id_room, r.name, r.id_house
            FROM rooms r
            JOIN houses h ON r.id_house = h.id_house
            WHERE h.id_user = %s
        """, (target_user_id,))
        rooms = cursor.fetchall()

        cursor.execute("""
            SELECT d.id_device, d.name, d.id_room
            FROM devices d
            JOIN rooms r ON d.id_room = r.id_room
            JOIN houses h ON r.id_house = h.id_house
            WHERE h.id_user = %s
        """, (target_user_id,))
        devices = cursor.fetchall()

    finally:
        cursor.close()

    return {
        "user": user,
        "houses": houses,
        "rooms": rooms,
        "devices": devices,
    }
