from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from .clients import create_mysql_connection


MIN_RANK_ANSWERED_COUNT = 100
LEADERBOARD_LIMIT = 50
SCORE_BY_EVENT = {
    "FAVORITE_ADDED": 1,
    "PRACTICE_COMPLETED": 10,
    "MISTAKE_REMOVED": 3,
}


def ensure_ranking_schema() -> None:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ranking_score_events (
                  id VARCHAR(64) PRIMARY KEY,
                  user_id VARCHAR(64) NOT NULL,
                  event_type VARCHAR(64) NOT NULL,
                  score INT NOT NULL,
                  related_id VARCHAR(191),
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_ranking_score_user_created (user_id, created_at),
                  INDEX idx_ranking_score_event_type (event_type, created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )


def record_score_event(user_id: str, event_type: str, related_id: str = "") -> None:
    ensure_ranking_schema()
    score = SCORE_BY_EVENT.get(event_type)
    if not score:
        return
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ranking_score_events (
                  id, user_id, event_type, score, related_id
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (f"rse-{uuid4().hex[:20]}", user_id, event_type, score, related_id or None),
            )


def get_ranking_summary(user_id: str) -> dict:
    ensure_ranking_schema()
    total_rows = _query_leaderboard_rows()
    weekly_rows = _query_leaderboard_rows(start_at=_current_week_start_utc())
    total_row = _find_user_row(total_rows, user_id)
    weekly_row = _find_user_row(weekly_rows, user_id)
    return {
        "total": total_row.get("rank") if total_row else None,
        "weekly": weekly_row.get("rank") if weekly_row else None,
        "currentScore": _get_current_score(user_id),
        "totalAccuracy": total_row.get("accuracy") if total_row else None,
        "weeklyAccuracy": weekly_row.get("accuracy") if weekly_row else None,
        "totalAnsweredCount": total_row.get("answeredCount") if total_row else _get_answered_count(user_id),
        "weeklyAnsweredCount": weekly_row.get("answeredCount") if weekly_row else _get_answered_count(
            user_id, start_at=_current_week_start_utc()
        ),
        "minAnsweredCount": MIN_RANK_ANSWERED_COUNT,
        "eligibleTotal": bool(total_row),
        "eligibleWeekly": bool(weekly_row),
    }


def list_leaderboard(scope: str, current_user_id: str) -> list[dict]:
    ensure_ranking_schema()
    rows = _query_leaderboard_rows(start_at=_current_week_start_utc() if scope == "weekly" else None)
    leaderboard = rows[:LEADERBOARD_LIMIT]
    return [
        {
            **row,
            "isCurrentUser": row["userId"] == current_user_id,
        }
        for row in leaderboard
    ]


def _query_leaderboard_rows(start_at: datetime | None = None) -> list[dict]:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            if start_at:
                cursor.execute(
                    """
                    SELECT
                      pr.user_id,
                      COALESCE(NULLIF(u.nickname, ''), '匿名') AS nickname,
                      COALESCE(u.avatar_url, '') AS avatar_url,
                      SUM(pr.total_count) AS answered_count,
                      SUM(pr.correct_count) AS correct_count
                    FROM practice_records pr
                    LEFT JOIN users u ON BINARY u.id = BINARY pr.user_id
                    WHERE pr.created_at >= %s
                    GROUP BY pr.user_id, u.nickname, u.avatar_url
                    HAVING SUM(pr.total_count) >= %s
                    ORDER BY
                      (SUM(pr.correct_count) / NULLIF(SUM(pr.total_count), 0)) DESC,
                      SUM(pr.total_count) DESC,
                      pr.user_id ASC
                    """,
                    (start_at, MIN_RANK_ANSWERED_COUNT),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                      pr.user_id,
                      COALESCE(NULLIF(u.nickname, ''), '匿名') AS nickname,
                      COALESCE(u.avatar_url, '') AS avatar_url,
                      SUM(pr.total_count) AS answered_count,
                      SUM(pr.correct_count) AS correct_count
                    FROM practice_records pr
                    LEFT JOIN users u ON BINARY u.id = BINARY pr.user_id
                    GROUP BY pr.user_id, u.nickname, u.avatar_url
                    HAVING SUM(pr.total_count) >= %s
                    ORDER BY
                      (SUM(pr.correct_count) / NULLIF(SUM(pr.total_count), 0)) DESC,
                      SUM(pr.total_count) DESC,
                      pr.user_id ASC
                    """,
                    (MIN_RANK_ANSWERED_COUNT,),
                )
            rows = cursor.fetchall()
    return [
        {
            "rank": index + 1,
            "userId": row.get("user_id") or "",
            "name": row.get("nickname") or "匿名",
            "avatarUrl": row.get("avatar_url") or "",
            "accuracy": _build_accuracy(row),
            "answeredCount": int(row.get("answered_count") or 0),
            "correctCount": int(row.get("correct_count") or 0),
        }
        for index, row in enumerate(rows)
    ]


def _build_accuracy(row: dict) -> int:
    answered = int(row.get("answered_count") or 0)
    correct = int(row.get("correct_count") or 0)
    return round((correct / answered) * 100) if answered else 0


def _find_user_row(rows: list[dict], user_id: str) -> dict | None:
    for row in rows:
        if row["userId"] == user_id:
            return row
    return None


def _get_current_score(user_id: str) -> int:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(COUNT(*), 0) AS total
                FROM practice_records
                WHERE user_id = %s
                """,
                (user_id,),
            )
            practice_row = cursor.fetchone() or {}
            cursor.execute(
                """
                SELECT COALESCE(SUM(score), 0) AS total
                FROM ranking_score_events
                WHERE user_id = %s AND event_type != 'PRACTICE_COMPLETED'
                """,
                (user_id,),
            )
            event_row = cursor.fetchone() or {}
    return int(practice_row.get("total") or 0) * SCORE_BY_EVENT["PRACTICE_COMPLETED"] + int(event_row.get("total") or 0)


def _get_answered_count(user_id: str, start_at: datetime | None = None) -> int:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            if start_at:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(total_count), 0) AS total
                    FROM practice_records
                    WHERE user_id = %s AND created_at >= %s
                    """,
                    (user_id, start_at),
                )
            else:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(total_count), 0) AS total
                    FROM practice_records
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def _current_week_start_utc() -> datetime:
    local_now = datetime.utcnow() + timedelta(hours=8)
    start_local = (local_now - timedelta(days=local_now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local - timedelta(hours=8)
