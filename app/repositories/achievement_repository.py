from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

# ACHIEVEMENTS

def get_all_achievements(db) -> List[Dict[str, Any]]:
    """
    Lista de conquistas base (catálogo).
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                id_achievement,
                title,
                description,
                type,
                target_value
            FROM achievements
            ORDER BY id_achievement ASC
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def get_achievement_by_id(db, achievement_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca uma conquista do catálogo por id.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                id_achievement,
                title,
                description,
                type,
                target_value
            FROM achievements
            WHERE id_achievement = %s
            LIMIT 1
            """,
            (achievement_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()

# USER ACHIEVEMENTS

def get_user_achievement(
    db,
    user_id: int,
    house_id: int,
    achievement_id: int,
    period_reference: date,
) -> Optional[Dict[str, Any]]:
    """
    Retorna o registo da conquista do utilizador para um dado período.

    Importante: esta versão NÃO assume created_at/updated_at na tabela.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                id_user_achievement,
                id_user,
                id_house,
                id_achievement,
                period_reference,
                status,
                progress
            FROM user_achievements
            WHERE id_user = %s
              AND id_house = %s
              AND id_achievement = %s
              AND period_reference = %s
            LIMIT 1
            """,
            (user_id, house_id, achievement_id, period_reference),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def get_user_achievements_for_period(
    db,
    user_id: int,
    house_id: int,
    period_reference: date,
) -> List[Dict[str, Any]]:
    """
    Lista conquistas do utilizador num período (útil para UI/overview).

    Importante: NÃO assume created_at/updated_at na tabela user_achievements.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                ua.id_user_achievement,
                ua.id_user,
                ua.id_house,
                ua.id_achievement,
                ua.period_reference,
                ua.status,
                ua.progress,
                a.title,
                a.description,
                a.type,
                a.target_value
            FROM user_achievements ua
            JOIN achievements a ON a.id_achievement = ua.id_achievement
            WHERE ua.id_user = %s
              AND ua.id_house = %s
              AND ua.period_reference = %s
            ORDER BY ua.id_achievement ASC
            """,
            (user_id, house_id, period_reference),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def upsert_user_achievement(
    db,
    user_id: int,
    house_id: int,
    achievement_id: int,
    period_reference: date,
    status: str,
    progress: float,
) -> int:
    """
    Cria ou atualiza (upsert) o registo de progresso da conquista para um período.
    Devolve id_user_achievement.

    NOTA:
    - Idealmente existe um UNIQUE (id_user, id_house, id_achievement, period_reference).
    - Em concorrência, este padrão "SELECT depois UPDATE/INSERT" pode duplicar sem UNIQUE.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT id_user_achievement
            FROM user_achievements
            WHERE id_user = %s
              AND id_house = %s
              AND id_achievement = %s
              AND period_reference = %s
            LIMIT 1
            """,
            (user_id, house_id, achievement_id, period_reference),
        )
        row = cursor.fetchone()

        if row:
            user_achievement_id = int(row[0])
            cursor.execute(
                """
                UPDATE user_achievements
                SET status = %s,
                    progress = %s
                WHERE id_user_achievement = %s
                  AND id_user = %s
                  AND id_house = %s
                """,
                (status, float(progress), user_achievement_id, user_id, house_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO user_achievements (
                    id_user,
                    id_house,
                    id_achievement,
                    period_reference,
                    status,
                    progress
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, house_id, achievement_id, period_reference, status, float(progress)),
            )
            user_achievement_id = int(cursor.lastrowid)

        db.commit()
        return user_achievement_id

    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def mark_user_achievement_completed(
    db,
    user_id: int,
    house_id: int,
    achievement_id: int,
    period_reference: date,
    *,
    progress: Optional[float] = None,
) -> Tuple[bool, int]:

    # 🔍 Buscar estado atual
    current = get_user_achievement(
        db,
        user_id,
        house_id,
        achievement_id,
        period_reference,
    )

    if current and current.get("status") == "completed":
        return False, int(current["id_user_achievement"])

    if progress is None:
        if current and current.get("progress") is not None:
            progress = float(current["progress"])
        else:
            progress = 0.0

    user_achievement_id = upsert_user_achievement(
        db=db,
        user_id=user_id,
        house_id=house_id,
        achievement_id=achievement_id,
        period_reference=period_reference,
        status="completed",
        progress=float(progress),
    )

    return True, user_achievement_id

# CONSUMPTION QUERIES (DADOS ACUMULATIVOS)

def get_monthly_consumption(
    db,
    house_id: int,
    year: int,
    month: int,
) -> float:
    """
    Calcula consumo mensal para dados acumulativos:
      Para cada dispositivo: MAX(energy_kwh) - MIN(energy_kwh)
      Depois soma todos os dispositivos.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT COALESCE(SUM(device_consumption), 0)
            FROM (
                SELECT
                    er.id_device,
                    MAX(er.energy_kwh) - MIN(er.energy_kwh) AS device_consumption
                FROM energy_readings er
                JOIN devices d ON er.id_device = d.id_device
                JOIN rooms r ON d.id_room = r.id_room
                WHERE r.id_house = %s
                  AND YEAR(er.recorded_at) = %s
                  AND MONTH(er.recorded_at) = %s
                GROUP BY er.id_device
            ) AS monthly
            """,
            (house_id, year, month),
        )
        row = cursor.fetchone()
        return float((row[0] if row else 0) or 0)
    finally:
        cursor.close()


def get_previous_month(year: int, month: int) -> Tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def get_house_monthly_limit(db, house_id: int) -> Optional[float]:
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT monthly_kwh
            FROM houses
            WHERE id_house = %s
            LIMIT 1
            """,
            (house_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return float(row[0]) if row[0] is not None else None
    finally:
        cursor.close()

# SECURITY CHECK

def house_belongs_to_user(db, user_id: int, house_id: int) -> bool:
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT 1
            FROM houses
            WHERE id_house = %s
              AND id_user = %s
            LIMIT 1
            """,
            (house_id, user_id),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
