# backend/app/repositories/house_repository.py

from __future__ import annotations


# =========================
# GET — casas do utilizador
# =========================
def get_houses_by_user(db, user_id: int):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            id_house,
            name,
            address,
            house_type,
            adults,
            children,
            occupancy_type,
            provider,
            tariff,
            contract_power,
            monthly_kwh,
            price_per_kwh,
            created_at
        FROM houses
        WHERE id_user = %s
          AND is_active = 1
        ORDER BY created_at ASC
        """,
        (user_id,),
    )
    houses = cursor.fetchall()
    cursor.close()
    return houses


# =========================
# GET — casa por ID (segura)
# =========================
def get_house_by_id(db, id_house: int, user_id: int):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            id_house,
            name,
            address,
            house_type,
            adults,
            children,
            occupancy_type,
            provider,
            tariff,
            contract_power,
            monthly_kwh,
            price_per_kwh,
            created_at
        FROM houses
        WHERE id_house = %s
          AND id_user = %s
        """,
        (id_house, user_id),
    )
    house = cursor.fetchone()
    cursor.close()
    return house


# =========================
# POST — criar casa
# =========================
def create_house(
    db,
    user_id: int,
    name: str,
    house_type: str | None,
    occupancy_type: str | None,
    address: str | None = None,
    adults: int = 0,
    children: int = 0,
    provider: str | None = None,
    tariff: str | None = None,
    contract_power: float | None = None,
    monthly_kwh: float | None = None,
    price_per_kwh: float | None = None,  # NOVO
):
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO houses (
                id_user,
                name,
                address,
                house_type,
                adults,
                children,
                occupancy_type,
                provider,
                tariff,
                contract_power,
                monthly_kwh,
                price_per_kwh
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                name,
                address,
                house_type,
                adults,
                children,
                occupancy_type,
                provider,
                tariff,
                contract_power,
                monthly_kwh,
                price_per_kwh,
            ),
        )

        db.commit()
        return cursor.lastrowid

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


# =========================
# PUT — atualizar casa
# =========================
def update_house(
    db,
    id_house: int,
    user_id: int,
    name: str,
    address: str | None,
    house_type: str | None,
    adults: int,
    children: int,
    occupancy_type: str | None,
    provider: str | None,
    tariff: str | None,
    contract_power: float | None,
    monthly_kwh: float | None,
    price_per_kwh: float | None = None,
):
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE houses
            SET
                name = %s,
                address = %s,
                house_type = %s,
                adults = %s,
                children = %s,
                occupancy_type = %s,
                provider = %s,
                tariff = %s,
                contract_power = %s,
                monthly_kwh = %s,
                price_per_kwh = %s
            WHERE id_house = %s
              AND id_user = %s
            """,
            (
                name,
                address,
                house_type,
                adults,
                children,
                occupancy_type,
                provider,
                tariff,
                contract_power,
                monthly_kwh,
                price_per_kwh,
                id_house,
                user_id,
            ),
        )

        db.commit()

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT 1 FROM houses WHERE id_house = %s AND id_user = %s",
                (id_house, user_id),
            )
            exists = cursor.fetchone()
            return exists is not None

        return True

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


# =========================
# GET — casa completa (rooms + devices)
# =========================
def get_house_full(db, id_house: int, user_id: int):
    cursor = db.cursor(dictionary=True)

    try:
        # 1) Casa (segurança: pertence ao user)
        cursor.execute(
            """
            SELECT
                id_house,
                name,
                address,
                house_type,
                adults,
                children,
                occupancy_type,
                provider,
                tariff,
                contract_power,
                monthly_kwh,
                price_per_kwh,
                created_at
            FROM houses
            WHERE id_house = %s
              AND id_user = %s
            """,
            (id_house, user_id),
        )
        house = cursor.fetchone()

        if not house:
            return None

        # 2) Divisões
        cursor.execute(
            """
            SELECT
                id_room,
                id_house,
                name,
                created_at
            FROM rooms
            WHERE id_house = %s
            ORDER BY created_at ASC
            """,
            (id_house,),
        )
        rooms = cursor.fetchall()

        # 3) Dispositivos por divisão (ativos)
        for room in rooms:
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
                WHERE id_room = %s
                  AND is_active = 1
                ORDER BY id_device ASC
                """,
                (room["id_room"],),
            )
            room["devices"] = cursor.fetchall()

        house["rooms"] = rooms
        return house

    finally:
        cursor.close()


# =========================
# PATCH — desativar casa
# =========================
def deactivate_house(db, id_house: int, user_id: int):
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE houses
            SET is_active = 0
            WHERE id_house = %s
              AND id_user = %s
            """,
            (id_house, user_id),
        )

        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


def get_user_house_data(db, user_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            monthly_kwh,
            price_per_kwh,
            provider,
            tariff,
            contract_power,
            adults,
            children
        FROM houses
        WHERE id_user = %s
        AND is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )

    house = cursor.fetchone()
    cursor.close()

    if not house:
        return None

    monthly = float(house["monthly_kwh"] or 0)

    # API espera consumo anual
    yearly = monthly * 12

    consumption_low = yearly * 0.4
    consumption_high = yearly * 0.6

    return {
    "adults": house["adults"],
    "children": house["children"],
    "consumption_low": consumption_low,
    "consumption_high": consumption_high,
    "consumption_total": monthly,
    "power": house["contract_power"],
    "tariff": house["tariff"],        # 👈 adicionar
    "price_per_kwh": house["price_per_kwh"],  # 👈 opcional mas útil
    "provider": house["provider"],    # 👈 opcional
    "gas": 0
}