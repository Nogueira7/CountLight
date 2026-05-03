from typing import List, Dict, Any


# CREATE NOTIFICATION

def create_notification(
    db,
    user_id: int,
    house_id: int,
    type: str,
    title: str,
    message: str,
) -> int:
    """
    Cria uma nova notificação no sistema.
    """

    cursor = db.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO notifications (id_user, id_house, type, title, message)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, house_id, type, title, message),
        )

        db.commit()

        return cursor.lastrowid

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# GET USER NOTIFICATIONS


def get_user_notifications(
    db,
    user_id: int,
    house_id: int,
) -> List[Dict[str, Any]]:
    """
    Obtém notificações do utilizador para a casa selecionada.
    Usado no Registo de eventos (timeline).
    """

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id_notification,
                type,
                title,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE id_user = %s
              AND id_house = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id, house_id),
        )

        notifications = cursor.fetchall()

        return notifications

    finally:
        cursor.close()



# MARK ALL AS READ


def mark_all_notifications_as_read(
    db,
    user_id: int,
    house_id: int,
) -> int:
    """
    Marca todas as notificações como lidas.
    """

    cursor = db.cursor()

    try:
        cursor.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id_user = %s
              AND id_house = %s
              AND is_read = 0
            """,
            (user_id, house_id),
        )

        affected = cursor.rowcount

        db.commit()

        return int(affected or 0)

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()
