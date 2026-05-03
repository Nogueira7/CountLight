from datetime import date


# GET ACTIVE GOAL BY TYPE


def get_active_goal_by_type(
    db,
    user_id: int,
    house_id: int,
    goal_type: str,
):
    """
    Retorna a meta ativa de um determinado tipo.
    Permite 1 meta ativa por tipo.
    """
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM user_goals
        WHERE id_user = %s
          AND id_house = %s
          AND goal_type = %s
          AND status = 'active'
        LIMIT 1
        """,
        (user_id, house_id, goal_type),
    )

    result = cursor.fetchone()
    cursor.close()
    return result



# GET ALL ACTIVE GOALS (TODOS OS TIPOS)


def get_all_active_goals(
    db,
    user_id: int,
    house_id: int,
):
    """
    Retorna todas as metas ativas da casa (independentemente do tipo).
    """
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM user_goals
        WHERE id_user = %s
          AND id_house = %s
          AND status = 'active'
        ORDER BY created_at DESC
        """,
        (user_id, house_id),
    )

    results = cursor.fetchall()
    cursor.close()
    return results



# GET GOAL BY ID


def get_goal_by_id(
    db,
    goal_id: int,
    user_id: int,
    house_id: int,
):
    """
    Retorna uma meta específica (ativa ou histórico).
    """
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM user_goals
        WHERE id_goal = %s
          AND id_user = %s
          AND id_house = %s
        """,
        (goal_id, user_id, house_id),
    )

    result = cursor.fetchone()
    cursor.close()
    return result



# CREATE GOAL


def create_goal(
    db,
    user_id: int,
    house_id: int,
    goal_type: str,
    target_value: float,
    start_date: date,
    end_date: date,
):
    """
    Cria nova meta.
    O service deve garantir que não existe meta ativa do mesmo tipo.
    """
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO user_goals (
                id_user,
                id_house,
                goal_type,
                target_value,
                current_value,
                status,
                start_date,
                end_date
            )
            VALUES (%s, %s, %s, %s, 0, 'active', %s, %s)
            """,
            (
                user_id,
                house_id,
                goal_type,
                target_value,
                start_date,
                end_date,
            ),
        )

        goal_id = cursor.lastrowid
        db.commit()
        return goal_id

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# UPDATE GOAL PROGRESS


def update_goal_progress(
    db,
    goal_id: int,
    user_id: int,
    house_id: int,
    current_value: float,
    status: str,
):
    """
    Atualiza progresso e estado da meta.
    Status esperado:
    - active
    - completed
    - failed
    """
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            UPDATE user_goals
            SET current_value = %s,
                status = %s
            WHERE id_goal = %s
              AND id_user = %s
              AND id_house = %s
            """,
            (
                current_value,
                status,
                goal_id,
                user_id,
                house_id,
            ),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# DELETE GOAL


def delete_goal(
    db,
    goal_id: int,
    user_id: int,
    house_id: int,
):
    """
    Remove permanentemente uma meta.
    """
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM user_goals
            WHERE id_goal = %s
              AND id_user = %s
              AND id_house = %s
            """,
            (goal_id, user_id, house_id),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()



# HISTORY


def get_all_goals(
    db,
    user_id: int,
    house_id: int,
):
    """
    Retorna todas as metas (ativas + histórico).
    """
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM user_goals
        WHERE id_user = %s
          AND id_house = %s
        ORDER BY created_at DESC
        """,
        (user_id, house_id),
    )

    results = cursor.fetchall()
    cursor.close()
    return results
