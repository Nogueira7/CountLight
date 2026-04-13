from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_db
from app.core.security import get_current_user

router = APIRouter()

@router.post("/generate-data")
def generate_data(user_id: int = Depends(get_current_user), db=Depends(get_db)):

    # 🔐 PROTEÇÃO
    if user_id not in [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]:
        raise HTTPException(status_code=403, detail="Não permitido")

    cursor = db.cursor()

    try:
        # 🔍 verificar se já existem dados
        cursor.execute("""
            SELECT 1
            FROM energy_readings er
            JOIN devices d ON er.id_device = d.id_device
            JOIN rooms r ON d.id_room = r.id_room
            JOIN houses h ON r.id_house = h.id_house
            WHERE h.id_user = %s
            LIMIT 1
        """, (user_id,))

        already_exists = cursor.fetchone() is not None

        if already_exists:
            return {"message": "Já existem dados gerados", "already_exists": True}

        # 🚀 gerar dados
        cursor.execute("CALL GerarDadosUser(%s)", (user_id,))
        db.commit()

        return {"message": "Dados gerados com sucesso", "already_exists": False}

    except Exception as e:
        db.rollback()
        print("ERRO generate-data:", e)  # 👈 MUITO IMPORTANTE para debug
        raise HTTPException(status_code=500, detail="Erro ao gerar dados")

    finally:
        cursor.close()

@router.get("/generate-data-status")
def generate_data_status(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor()

    try:
        # 🔍 Verificar se tem dispositivos
        cursor.execute("""
            SELECT 1
            FROM devices d
            JOIN rooms r ON d.id_room = r.id_room
            JOIN houses h ON r.id_house = h.id_house
            WHERE h.id_user = %s
            LIMIT 1
        """, (user_id,))
        has_devices = cursor.fetchone() is not None

        # 🔍 Verificar se já tem dados
        cursor.execute("""
            SELECT 1
            FROM energy_readings er
            JOIN devices d ON er.id_device = d.id_device
            JOIN rooms r ON d.id_room = r.id_room
            JOIN houses h ON r.id_house = h.id_house
            WHERE h.id_user = %s
            LIMIT 1
        """, (user_id,))
        has_data = cursor.fetchone() is not None

        return {
            "can_generate": has_devices and not has_data,
            "already_exists": has_data
        }

    finally:
        cursor.close()