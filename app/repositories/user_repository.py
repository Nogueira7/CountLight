# backend/app/repositories/user_repository.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, List


# ==========================================================
# AUTH / LOGIN
# ==========================================================

def get_user_by_email(db, email: str) -> Optional[Dict[str, Any]]:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                id_user,
                username,
                email,
                password_hash,
                is_active,
                is_verified,
                verification_token,
                verification_expires
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def get_user_by_google_id(db, google_id: str):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                id_user,
                username,
                email,
                is_active,
                is_verified,
                google_id
            FROM users
            WHERE google_id = %s
            """,
            (google_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def get_user_by_username(db, username: str) -> Optional[Dict[str, Any]]:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                id_user,
                username,
                email,
                password_hash,
                is_active,
                is_verified,
                verification_token,
                verification_expires
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def create_user(
    db,
    username: str,
    email: str,
    password_hash: str,
    verification_token: str,
    verification_expires: Any,  # ideal: datetime
) -> int:
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                is_verified,
                verification_token,
                verification_expires
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                username,
                email,
                password_hash,
                False,  # conta NÃO verificada
                verification_token,
                verification_expires,
            ),
        )
        user_id = int(cursor.lastrowid)
        db.commit()
        return user_id
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def create_google_user(db, username: str, email: str, google_id: str) -> int:
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                google_id,
                is_verified,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                username,
                email,
                google_id,
                True,   # 🔥 Google já é verificado
                True,
            ),
        )
        user_id = int(cursor.lastrowid)
        db.commit()
        return user_id
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


# ==========================================================
# REFRESH TOKEN
# ==========================================================

def save_refresh_token(db, user_id: int, token: str) -> None:
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE users SET refresh_token=%s WHERE id_user=%s",
            (token, user_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def get_refresh_token(db, user_id: int) -> Optional[str]:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT refresh_token FROM users WHERE id_user=%s",
            (user_id,),
        )
        row = cursor.fetchone()
        return row["refresh_token"] if row else None
    finally:
        cursor.close()


def clear_refresh_token(db, user_id: int) -> None:
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE users SET refresh_token=NULL WHERE id_user=%s",
            (user_id,),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


# ==========================================================
# PROFILE DATA
# ==========================================================

def get_user_profile(db, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Devolve dados base do utilizador + perfil (se existir).
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                u.id_user,
                u.username,
                u.email,
                u.is_active,
                u.id_role,
                r.name AS role,
                up.description,
                up.photo_url
            FROM users u
            LEFT JOIN roles r ON u.id_role = r.id_role
            LEFT JOIN user_profiles up ON up.id_user = u.id_user
            WHERE u.id_user = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def update_user_profile(
    db,
    user_id: int,
    description: Optional[str] = None,
    photo_url: Optional[str] = None,
) -> None:
    """
    Atualiza ou cria o perfil do utilizador.
    Só atualiza campos que venham definidos (None = mantém).
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id_user_profile, description, photo_url FROM user_profiles WHERE id_user=%s",
            (user_id,),
        )
        existing = cursor.fetchone()

        if existing:
            new_description = description if description is not None else existing.get("description")
            new_photo_url = photo_url if photo_url is not None else existing.get("photo_url")

            cursor.execute(
                """
                UPDATE user_profiles
                SET description=%s, photo_url=%s
                WHERE id_user=%s
                """,
                (new_description, new_photo_url, user_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO user_profiles (id_user, description, photo_url)
                VALUES (%s, %s, %s)
                """,
                (user_id, description, photo_url),
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


# ==========================================================
# HELPERS (impact pieces)
# ==========================================================

def _to_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _get_user_price_per_kwh(db, user_id: int) -> float:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT price_per_kwh
            FROM houses
            WHERE id_user = %s AND is_active = 1
            ORDER BY id_house ASC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone() or {}
        try:
            return float(row.get("price_per_kwh") or 0.0)
        except Exception:
            return 0.0
    finally:
        cursor.close()


def _get_user_total_energy_kwh(db, user_id: int) -> float:
    """
    Total energia (kWh) aproximado:
      SUM(MAX(energy_kwh) - MIN(energy_kwh)) por device (contador cumulativo).
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT COALESCE(SUM(t.device_kwh), 0) AS total_kwh
            FROM (
                SELECT
                    d.id_device,
                    GREATEST(MAX(er.energy_kwh) - MIN(er.energy_kwh), 0) AS device_kwh
                FROM devices d
                JOIN rooms r ON r.id_room = d.id_room
                JOIN houses h ON h.id_house = r.id_house
                JOIN energy_readings er ON er.id_device = d.id_device
                WHERE h.id_user = %s
                GROUP BY d.id_device
            ) t
            """,
            (user_id,),
        )
        val = (cursor.fetchone() or {}).get("total_kwh") or 0.0
        try:
            return float(val)
        except Exception:
            return 0.0
    finally:
        cursor.close()


def _estimate_total_saved_eur(db, user_id: int) -> float:
    total_kwh = _get_user_total_energy_kwh(db, user_id)
    price = _get_user_price_per_kwh(db, user_id)
    if price <= 0:
        return 0.0
    return float(total_kwh * price)


# ==========================================================
# PEOPLE SUGGESTIONS
# ==========================================================

def get_user_suggestions(db, exclude_user_id: int, limit: int = 4) -> List[Dict[str, Any]]:
    """
    Devolve até `limit` utilizadores aleatórios (ativos),
    excluindo `exclude_user_id`.

    Retorna dicts com:
      - id_user
      - username
      - photo_url
      - total_saved_eur
    """
    try:
        limit_i = int(limit or 4)
    except Exception:
        limit_i = 4

    if limit_i < 1:
        return []
    if limit_i > 20:
        limit_i = 20

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                u.id_user,
                u.username,
                up.photo_url
            FROM users u
            LEFT JOIN user_profiles up ON up.id_user = u.id_user
            WHERE u.is_active = 1
              AND u.id_user <> %s
              AND u.username IS NOT NULL
              AND u.username <> ''
            ORDER BY RAND()
            LIMIT %s
            """,
            (exclude_user_id, limit_i),
        )
        rows = cursor.fetchall() or []
    finally:
        cursor.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        uid = r.get("id_user")
        try:
            uid_i = int(uid)
        except Exception:
            uid_i = None

        total_saved = None
        if uid_i is not None:
            try:
                total_saved = round(_estimate_total_saved_eur(db, uid_i), 2)
            except Exception:
                total_saved = None

        out.append(
            {
                "id_user": uid_i,
                "username": r.get("username"),
                "photo_url": r.get("photo_url"),
                "total_saved_eur": total_saved,
            }
        )

    return out


# ==========================================================
# SEARCH USERS (para a barra de pesquisa no header)
# ==========================================================

def search_users_by_username(
    db,
    q: str,
    limit: int = 8,
    exclude_user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Pesquisa utilizadores por username (parcial).
    Devolve: id_user, username, photo_url.

    - Ordena para aparecerem primeiro os que começam por `q`.
    - Exclui opcionalmente o próprio utilizador.
    """
    q = (q or "").strip()
    if not q:
        return []

    try:
        limit_i = int(limit or 8)
    except Exception:
        limit_i = 8
    limit_i = max(1, min(limit_i, 20))

    cursor = db.cursor(dictionary=True)
    try:
        sql = """
            SELECT
                u.id_user,
                u.username,
                up.photo_url
            FROM users u
            LEFT JOIN user_profiles up ON up.id_user = u.id_user
            WHERE u.is_active = 1
              AND u.username IS NOT NULL
              AND u.username <> ''
              AND u.username LIKE %s
        """
        params: List[Any] = [f"%{q}%"]

        if exclude_user_id is not None:
            sql += " AND u.id_user <> %s"
            params.append(exclude_user_id)

        sql += """
            ORDER BY
              CASE WHEN u.username LIKE %s THEN 0 ELSE 1 END,
              u.username ASC
            LIMIT %s
        """
        params.append(f"{q}%")
        params.append(limit_i)

        cursor.execute(sql, tuple(params))
        return cursor.fetchall() or []
    finally:
        cursor.close()


# ==========================================================
# ACCOUNT DATA (username/email)
# ==========================================================

def is_username_taken(db, username: str, exclude_user_id: int) -> bool:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 1
            FROM users
            WHERE username = %s AND id_user <> %s
            LIMIT 1
            """,
            (username, exclude_user_id),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def is_email_taken(db, email: str, exclude_user_id: int) -> bool:
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 1
            FROM users
            WHERE email = %s AND id_user <> %s
            LIMIT 1
            """,
            (email, exclude_user_id),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def update_user_account(
    db,
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """
    Atualiza username/email do utilizador.
    Só atualiza campos enviados (None = mantém).
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT username, email FROM users WHERE id_user=%s",
            (user_id,),
        )
        current = cursor.fetchone()
        if not current:
            raise ValueError("Utilizador não encontrado")

        new_username = username if username is not None else current.get("username")
        new_email = email if email is not None else current.get("email")

        cursor.execute(
            """
            UPDATE users
            SET username=%s, email=%s
            WHERE id_user=%s
            """,
            (new_username, new_email, user_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


# ==========================================================
# IMPACT / STATISTICS (para a página de Perfil)
# ==========================================================

def get_user_impact(db, user_id: int) -> Dict[str, Any]:
    """
    Devolve totais agregados para "Resumo de Impacto" + última conquista concluída.

    Assume energy_readings.energy_kwh como contador cumulativo por device:
      total ~= SUM(MAX(energy_kwh) - MIN(energy_kwh)) por device
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM achievements")
        total_achievements = int((cursor.fetchone() or {}).get("total") or 0)

        cursor.execute(
            """
            SELECT COUNT(DISTINCT id_achievement) AS completed
            FROM user_achievements
            WHERE id_user = %s AND status = 'completed'
            """,
            (user_id,),
        )
        completed_achievements = int((cursor.fetchone() or {}).get("completed") or 0)
        in_progress_achievements = max(total_achievements - completed_achievements, 0)

        cursor.execute(
            """
            SELECT
                a.title,
                a.description,
                ua.completed_at,
                ua.started_at,
                ua.id_user_achievement
            FROM user_achievements ua
            JOIN achievements a ON a.id_achievement = ua.id_achievement
            WHERE ua.id_user = %s
              AND ua.status = 'completed'
            ORDER BY COALESCE(ua.completed_at, ua.started_at) DESC, ua.id_user_achievement DESC
            LIMIT 1
            """,
            (user_id,),
        )
        last = cursor.fetchone()
        latest_achievement = None
        if last:
            latest_achievement = {
                "title": last.get("title"),
                "description": last.get("description"),
                "completed_at": _to_iso(last.get("completed_at") or last.get("started_at")),
            }

        cursor.execute(
            "SELECT COUNT(*) AS total FROM houses WHERE id_user = %s",
            (user_id,),
        )
        total_houses = int((cursor.fetchone() or {}).get("total") or 0)

        cursor.execute(
            """
            SELECT COUNT(d.id_device) AS total
            FROM devices d
            JOIN rooms r ON r.id_room = d.id_room
            JOIN houses h ON h.id_house = r.id_house
            WHERE h.id_user = %s
            """,
            (user_id,),
        )
        total_devices = int((cursor.fetchone() or {}).get("total") or 0)

        total_energy_kwh = _get_user_total_energy_kwh(db, user_id)
        price_per_kwh = _get_user_price_per_kwh(db, user_id)
        total_saved_eur = (total_energy_kwh * price_per_kwh) if price_per_kwh > 0 else 0.0

        return {
            "totals": {
                "total_houses": total_houses,
                "total_devices": total_devices,
                "total_energy_kwh": round(total_energy_kwh, 2),
                "total_saved_eur": round(total_saved_eur, 2),
                "total_achievements": total_achievements,
                "completed_achievements": completed_achievements,
                "in_progress_achievements": in_progress_achievements,
            },
            "latest_achievement": latest_achievement,
        }
    finally:
        cursor.close()



def get_user_by_verification_token(db, token: str):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id_user, verification_expires
            FROM users
            WHERE verification_token = %s
            """,
            (token,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def verify_user(db, user_id: int):
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET is_verified = 1,
                verification_token = NULL,
                verification_expires = NULL
            WHERE id_user = %s
            """,
            (user_id,),
        )
        db.commit()
    finally:
        cursor.close()


def get_active_subscription(db, user_id: int):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT *
            FROM subscriptions
            WHERE id_user = %s AND is_active = 1
            LIMIT 1
            """,
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()