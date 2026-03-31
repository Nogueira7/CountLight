# backend/app/repositories/device_repository.py

from __future__ import annotations


# =========================
# GET — devices por divisão (seguro)
# =========================
def get_devices_by_room(db, id_room: int, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.id_device,
            d.id_room,
            d.name,
            d.shelly_id,
            d.device_type,
            d.energy_class,
            d.is_active
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE d.id_room = %s
          AND h.id_user = %s
        ORDER BY d.id_device ASC
        """,
        (id_room, user_id),
    )

    devices = cursor.fetchall()
    cursor.close()
    return devices


# =========================
# GET — device por shelly_id (NÃO seguro sozinho)
# Mantém para usos internos/admin; não usar para responder a users sem validar ownership.
# =========================
def get_device_by_shelly_id(db, shelly_id: str):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id_device,
            id_room,
            name,
            shelly_id,
            device_type,
            energy_class,
            is_active
        FROM devices
        WHERE shelly_id = %s
        """,
        (shelly_id,),
    )

    device = cursor.fetchone()
    cursor.close()
    return device


# =========================
# GET — device por shelly_id (seguro: pertence ao user)
# =========================
def get_device_by_shelly_id_for_user(db, user_id: int, shelly_id: str):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.id_device,
            d.id_room,
            d.name,
            d.shelly_id,
            d.device_type,
            d.energy_class,
            d.is_active
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE d.shelly_id = %s
          AND h.id_user = %s
        """,
        (shelly_id, user_id),
    )

    device = cursor.fetchone()
    cursor.close()
    return device


# =========================
# POST — criar device (seguro + erros consistentes)
# =========================
def create_device(
    db,
    id_room: int,
    user_id: int,
    name: str,
    shelly_id: str,
    device_type: str | None = None,
    energy_class: str | None = None,
):
    cursor = db.cursor()

    try:
        # Verifica se a divisão pertence ao user
        cursor.execute(
            """
            SELECT 1
            FROM rooms r
            INNER JOIN houses h ON h.id_house = r.id_house
            WHERE r.id_room = %s
              AND h.id_user = %s
            """,
            (id_room, user_id),
        )

        if cursor.fetchone() is None:
            return None, "ROOM_NOT_FOUND"

        # Verifica se o Shelly já existe
        cursor.execute(
            """
            SELECT 1
            FROM devices
            WHERE shelly_id = %s
            """,
            (shelly_id,),
        )

        if cursor.fetchone():
            return None, "SHELLY_EXISTS"

        cursor.execute(
            """
            INSERT INTO devices (
                id_room,
                name,
                shelly_id,
                device_type,
                energy_class,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, 1)
            """,
            (
                id_room,
                name,
                shelly_id,
                device_type,
                energy_class,
            ),
        )

        db.commit()
        return cursor.lastrowid, None

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


# =========================
# DELETE — apagar device (seguro)
# =========================
def delete_device(
    db,
    id_device: int,
    user_id: int,
):
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            DELETE d
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            WHERE d.id_device = %s
              AND h.id_user = %s
            """,
            (id_device, user_id),
        )

        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()

def update_device(
    db,
    id_device: int,
    user_id: int,
    name: str,
    device_type: str | None,
    energy_class: str | None,
):
    cursor = db.cursor()

    try:
        # Verifica se existe e pertence ao user
        cursor.execute(
            """
            SELECT 1
            FROM devices d
            INNER JOIN rooms r ON r.id_room = d.id_room
            INNER JOIN houses h ON h.id_house = r.id_house
            WHERE d.id_device = %s
              AND h.id_user = %s
            """,
            (id_device, user_id),
        )

        if cursor.fetchone() is None:
            return False

        # Faz o update (mesmo que não mude nada)
        cursor.execute(
            """
            UPDATE devices
            SET name = %s,
                device_type = %s,
                energy_class = %s
            WHERE id_device = %s
            """,
            (name, device_type, energy_class, id_device),
        )

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


# =========================
# GET — todos os devices do utilizador
# =========================
def get_all_user_devices(db, user_id: int):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            d.id_device,
            d.name,
            d.device_type,
            d.energy_class
        FROM devices d
        INNER JOIN rooms r ON r.id_room = d.id_room
        INNER JOIN houses h ON h.id_house = r.id_house
        WHERE h.id_user = %s
        """,
        (user_id,),
    )

    devices = cursor.fetchall()
    cursor.close()
    return devices