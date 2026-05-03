# backend/app/repositories/room_repository.py

from __future__ import annotations



# GET — divisões de uma casa

def get_rooms_by_house(db, id_house: int, user_id: int):
    """
    Devolve todas as divisões de uma casa,
    garantindo que a casa pertence ao utilizador.
    """
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            r.id_room,
            r.id_house,
            r.name,
            r.created_at
        FROM rooms r
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE r.id_house = %s
          AND h.id_user = %s
        ORDER BY r.created_at ASC
        """,
        (id_house, user_id),
    )

    rooms = cursor.fetchall()
    cursor.close()
    return rooms



# GET — divisão por ID

def get_room_by_id(db, id_room: int, user_id: int):
    """
    Devolve uma divisão pelo ID,
    garantindo que pertence ao utilizador.
    """
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            r.id_room,
            r.id_house,
            r.name,
            r.created_at
        FROM rooms r
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE r.id_room = %s
          AND h.id_user = %s
        """,
        (id_room, user_id),
    )

    room = cursor.fetchone()
    cursor.close()
    return room



# POST — criar divisão

def create_room(
    db,
    id_house: int,
    user_id: int,
    name: str,
):
    """
    Cria uma divisão numa casa do utilizador.
    """
    cursor = db.cursor()
    try:
        # Garante que a casa pertence ao utilizador
        cursor.execute(
            """
            SELECT 1
            FROM houses
            WHERE id_house = %s
              AND id_user = %s
            """,
            (id_house, user_id),
        )

        if cursor.fetchone() is None:
            return None  # casa não existe ou não é do user

        cursor.execute(
            """
            INSERT INTO rooms (
                id_house,
                name
            )
            VALUES (%s, %s)
            """,
            (id_house, name),
        )

        db.commit()
        return cursor.lastrowid

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# PUT — atualizar divisã 

def update_room(
    db,
    id_room: int,
    user_id: int,
    name: str,
) -> bool:
    """
    Atualiza o nome de uma divisão se pertencer ao utilizador.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE rooms r
            INNER JOIN houses h ON h.id_house = r.id_house
            SET r.name = %s
            WHERE r.id_room = %s
              AND h.id_user = %s
            """,
            (name, id_room, user_id),
        )

        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# DELETE — apagar divisão 

def delete_room(
    db,
    id_room: int,
    user_id: int,
):
    """
    Apaga uma divisão se pertencer ao utilizador.
    Devices associados devem ser apagados por cascade.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            DELETE r
            FROM rooms r
            INNER JOIN houses h ON h.id_house = r.id_house
            WHERE r.id_room = %s
              AND h.id_user = %s
            """,
            (id_room, user_id),
        )

        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# GET — resumo da divisão

def get_room_month_percentage(db, id_room: int, user_id: int):
    """
    Calcula percentagem do consumo mensal da divisão
    face ao consumo total da casa.
    """

    cursor = db.cursor(dictionary=True)

    # Verificar se a divisão pertence ao utilizador
    cursor.execute(
        """
        SELECT r.id_house
        FROM rooms r
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE r.id_room = %s
          AND h.id_user = %s
        """,
        (id_room, user_id),
    )

    room = cursor.fetchone()
    if not room:
        cursor.close()
        return None

    id_house = room["id_house"]

    # 2️Consumo mensal da divisão
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(device_consumption), 0) AS room_month
        FROM (
            SELECT
                d.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM devices d
            LEFT JOIN energy_readings er ON er.id_device = d.id_device
            WHERE d.id_room = %s
              AND MONTH(er.recorded_at) = MONTH(CURRENT_DATE())
              AND YEAR(er.recorded_at) = YEAR(CURRENT_DATE())
            GROUP BY d.id_device
        ) AS sub
        """,
        (id_room,),
    )

    room_month = cursor.fetchone()["room_month"] or 0

    # Consumo mensal total da casa
    cursor.execute(
        """
        SELECT
            COALESCE(SUM(device_consumption), 0) AS house_month
        FROM (
            SELECT
                d.id_device,
                MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            LEFT JOIN energy_readings er ON er.id_device = d.id_device
            WHERE r.id_house = %s
              AND MONTH(er.recorded_at) = MONTH(CURRENT_DATE())
              AND YEAR(er.recorded_at) = YEAR(CURRENT_DATE())
            GROUP BY d.id_device
        ) AS sub
        """,
        (id_house,),
    )

    house_month = cursor.fetchone()["house_month"] or 0

    cursor.close()

    if house_month == 0:
        return 0

    percentage = round((room_month / house_month) * 100, 2)
    return percentage
