from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4

from .clients import create_mysql_connection
from .question_bank import get_question_by_id, serialize_question_detail


def ensure_practice_schema() -> None:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS practice_records (
                  id VARCHAR(64) PRIMARY KEY,
                  user_id VARCHAR(64) NOT NULL,
                  type VARCHAR(32) NOT NULL DEFAULT '练习',
                  title VARCHAR(255) NOT NULL,
                  bank_id VARCHAR(128),
                  chapter_key VARCHAR(512),
                  total_count INT NOT NULL DEFAULT 0,
                  correct_count INT NOT NULL DEFAULT 0,
                  wrong_count INT NOT NULL DEFAULT 0,
                  accuracy INT NOT NULL DEFAULT 0,
                  duration_seconds INT NOT NULL DEFAULT 0,
                  details_json JSON NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_practice_user_created (user_id, created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            _ensure_columns(
                cursor,
                "practice_records",
                {
                    "type": "ALTER TABLE practice_records ADD COLUMN type VARCHAR(32) NOT NULL DEFAULT '练习' AFTER user_id",
                    "title": "ALTER TABLE practice_records ADD COLUMN title VARCHAR(255) NOT NULL DEFAULT '练习结果' AFTER type",
                    "bank_id": "ALTER TABLE practice_records ADD COLUMN bank_id VARCHAR(128) NULL AFTER title",
                    "chapter_key": "ALTER TABLE practice_records ADD COLUMN chapter_key VARCHAR(512) NULL AFTER bank_id",
                    "wrong_count": "ALTER TABLE practice_records ADD COLUMN wrong_count INT NOT NULL DEFAULT 0 AFTER correct_count",
                    "accuracy": "ALTER TABLE practice_records ADD COLUMN accuracy INT NOT NULL DEFAULT 0 AFTER wrong_count",
                    "details_json": "ALTER TABLE practice_records ADD COLUMN details_json JSON NULL AFTER duration_seconds",
                },
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS practice_record_questions (
                  id VARCHAR(64) PRIMARY KEY,
                  practice_record_id VARCHAR(64) NOT NULL,
                  user_id VARCHAR(64) NOT NULL,
                  question_id VARCHAR(255) NOT NULL,
                  title TEXT,
                  chapter VARCHAR(512),
                  selected_answer VARCHAR(64),
                  correct_answer VARCHAR(64),
                  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
                  analysis TEXT,
                  question_type VARCHAR(64),
                  question_type_label VARCHAR(64),
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_prq_record_id (practice_record_id),
                  INDEX idx_prq_user_question (user_id, question_id)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mistakes (
                  id VARCHAR(64) PRIMARY KEY,
                  user_id VARCHAR(64) NOT NULL,
                  question_id VARCHAR(191) NOT NULL,
                  title TEXT,
                  chapter VARCHAR(512),
                  wrong_times INT NOT NULL DEFAULT 0,
                  last_selected_answer VARCHAR(64),
                  correct_answer VARCHAR(64),
                  analysis TEXT,
                  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                  last_wrong_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_user_question_mistake (user_id, question_id),
                  INDEX idx_mistake_user_status (user_id, status, last_wrong_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            _ensure_columns(
                cursor,
                "mistakes",
                {
                    "title": "ALTER TABLE mistakes ADD COLUMN title TEXT NULL AFTER question_id",
                    "chapter": "ALTER TABLE mistakes ADD COLUMN chapter VARCHAR(512) NULL AFTER title",
                    "wrong_times": "ALTER TABLE mistakes ADD COLUMN wrong_times INT NOT NULL DEFAULT 0 AFTER chapter",
                    "last_selected_answer": "ALTER TABLE mistakes ADD COLUMN last_selected_answer VARCHAR(64) NULL AFTER wrong_times",
                    "correct_answer": "ALTER TABLE mistakes ADD COLUMN correct_answer VARCHAR(64) NULL AFTER last_selected_answer",
                    "analysis": "ALTER TABLE mistakes ADD COLUMN analysis TEXT NULL AFTER correct_answer",
                    "status": "ALTER TABLE mistakes ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' AFTER wrong_times",
                    "last_wrong_at": "ALTER TABLE mistakes ADD COLUMN last_wrong_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP AFTER status",
                },
            )
            cursor.execute("ALTER TABLE mistakes MODIFY COLUMN question_id VARCHAR(191) NOT NULL")


def _ensure_columns(cursor, table_name: str, column_sql: dict[str, str]) -> None:
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    existing = {row["Field"] for row in cursor.fetchall()}
    for column_name, statement in column_sql.items():
        if column_name not in existing:
            cursor.execute(statement)


def save_practice_record(user_id: str, payload: dict) -> dict:
    ensure_practice_schema()
    record_id = payload.get("recordId") or f"practice-{uuid4().hex[:12]}"
    details = payload.get("details") or []
    questions = payload.get("questions") or []
    title = payload.get("title") or "练习结果"
    record_type = payload.get("type") or "练习"
    bank_id = payload.get("bankId") or None
    chapter_key = payload.get("chapterKey") or None
    answered_count = int(payload.get("answeredCount") or 0)
    correct_count = int(payload.get("correctCount") or 0)
    wrong_count = int(payload.get("wrongCount") or 0)
    accuracy = int(payload.get("accuracy") or 0)

    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO practice_records (
                  id, user_id, type, title, bank_id, chapter_key,
                  total_count, correct_count, wrong_count, accuracy, details_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record_id,
                    user_id,
                    record_type,
                    title,
                    bank_id,
                    chapter_key,
                    answered_count,
                    correct_count,
                    wrong_count,
                    accuracy,
                    json.dumps(details, ensure_ascii=False),
                ),
            )

            if questions:
                cursor.executemany(
                    """
                    INSERT INTO practice_record_questions (
                      id, practice_record_id, user_id, question_id, title, chapter,
                      selected_answer, correct_answer, is_correct, analysis,
                      question_type, question_type_label
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            f"prq-{uuid4().hex[:20]}",
                            record_id,
                            user_id,
                            item.get("questionId") or "",
                            item.get("stem") or "",
                            item.get("chapter") or "",
                            item.get("selected") or "",
                            item.get("answer") or "",
                            1 if item.get("correct") else 0,
                            item.get("analysis") or "",
                            item.get("type") or "",
                            item.get("typeLabel") or "",
                        )
                        for item in questions
                    ],
                )

            for item in questions:
                if item.get("correct"):
                    continue
                cursor.execute(
                    """
                    INSERT INTO mistakes (
                      id, user_id, question_id, title, chapter, wrong_times,
                      last_selected_answer, correct_answer, analysis, status, last_wrong_at
                    ) VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, 'ACTIVE', NOW())
                    ON DUPLICATE KEY UPDATE
                      title = VALUES(title),
                      chapter = VALUES(chapter),
                      wrong_times = wrong_times + 1,
                      last_selected_answer = VALUES(last_selected_answer),
                      correct_answer = VALUES(correct_answer),
                      analysis = VALUES(analysis),
                      status = 'ACTIVE',
                      last_wrong_at = NOW()
                    """,
                    (
                        f"mistake-{uuid4().hex[:20]}",
                        user_id,
                        item.get("questionId") or "",
                        item.get("stem") or "",
                        item.get("chapter") or "",
                        item.get("selected") or "",
                        item.get("answer") or "",
                        item.get("analysis") or "",
                    ),
                )

    return get_practice_record(user_id, record_id)


def get_record_dashboard(user_id: str) -> dict:
    ensure_practice_schema()
    records = list_practice_records(user_id)
    total_answered = sum(int(item.get("answeredCount") or 0) for item in records)
    total_wrong = sum(int(item.get("wrongCount") or 0) for item in records)
    total_correct = max(total_answered - total_wrong, 0)
    accuracy = round((total_correct / total_answered) * 100) if total_answered else 0
    mistake_count = count_active_mistakes(user_id)

    return {
        "hasCompletedPractice": bool(records),
        "stats": [
            {"label": "总做题数", "value": str(total_answered)},
            {"label": "正确率", "value": f"{accuracy}%"},
            {"label": "考试数", "value": str(len(records))},
        ],
        "records": records,
        "mistakeCount": mistake_count,
        "practiceCount": len(records),
        "examCount": len(records),
    }


def list_practice_records(user_id: str) -> list[dict]:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, type, title, total_count, correct_count, wrong_count, accuracy, created_at
                FROM practice_records
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
    return [_format_record_summary(row) for row in rows]


def get_practice_record(user_id: str, record_id: str) -> dict | None:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, type, title, bank_id, chapter_key, total_count, correct_count, wrong_count,
                       accuracy, details_json, created_at
                FROM practice_records
                WHERE user_id = %s AND id = %s
                """,
                (user_id, record_id),
            )
            row = cursor.fetchone()
    if not row:
        return None
    details = row.get("details_json") or []
    if isinstance(details, str):
        details = json.loads(details or "[]")
    return {
        "id": row["id"],
        "type": row.get("type") or "练习",
        "title": row.get("title") or "练习结果",
        "bankId": row.get("bank_id") or "",
        "chapterKey": row.get("chapter_key") or "",
        "answeredCount": int(row.get("total_count") or 0),
        "correctCount": int(row.get("correct_count") or 0),
        "wrongCount": int(row.get("wrong_count") or 0),
        "accuracy": int(row.get("accuracy") or 0),
        "details": details or [],
        "date": _format_date(row.get("created_at")),
        "dateTime": _format_datetime(row.get("created_at")),
    }


def list_record_mistakes(user_id: str, record_id: str) -> list[dict]:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, question_id, title, chapter, selected_answer, correct_answer, analysis
                FROM practice_record_questions
                WHERE user_id = %s AND practice_record_id = %s AND is_correct = 0
                ORDER BY created_at ASC, id ASC
                """,
                (user_id, record_id),
            )
            rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "questionId": row.get("question_id") or "",
            "title": row.get("title") or "未命名题目",
            "chapter": row.get("chapter") or "练习题",
            "selectedAnswer": row.get("selected_answer") or "",
            "correctAnswer": row.get("correct_answer") or "",
            "analysis": row.get("analysis") or "",
            "wrongTimes": 1,
        }
        for row in rows
    ]


def list_global_mistakes(user_id: str) -> list[dict]:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, question_id, title, chapter, wrong_times,
                       last_selected_answer, correct_answer, analysis, last_wrong_at
                FROM mistakes
                WHERE user_id = %s AND status = 'ACTIVE'
                ORDER BY last_wrong_at DESC, updated_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
    return [
        {
            "id": row["id"],
            "questionId": row.get("question_id") or "",
            "title": row.get("title") or "未命名题目",
            "chapter": row.get("chapter") or "练习题",
            "wrongTimes": int(row.get("wrong_times") or 0),
            "selectedAnswer": row.get("last_selected_answer") or "",
            "correctAnswer": row.get("correct_answer") or "",
            "analysis": row.get("analysis") or "",
            "dateTime": _format_datetime(row.get("last_wrong_at")),
        }
        for row in rows
    ]


def dismiss_mistake(user_id: str, mistake_id: str) -> None:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE mistakes
                SET status = 'DISMISSED'
                WHERE user_id = %s AND id = %s
                """,
                (user_id, mistake_id),
            )


def get_record_mistake_detail(user_id: str, item_id: str) -> dict | None:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, question_id, title, chapter, selected_answer, correct_answer,
                       analysis, question_type, question_type_label
                FROM practice_record_questions
                WHERE user_id = %s AND id = %s AND is_correct = 0
                """,
                (user_id, item_id),
            )
            row = cursor.fetchone()
    if not row:
        return None
    return _build_mistake_detail(
        detail_id=row["id"],
        question_id=row.get("question_id") or "",
        title=row.get("title") or "",
        chapter=row.get("chapter") or "",
        selected_answer=row.get("selected_answer") or "",
        correct_answer=row.get("correct_answer") or "",
        analysis=row.get("analysis") or "",
        wrong_times=1,
        fallback_type=row.get("question_type") or "",
        fallback_type_label=row.get("question_type_label") or "",
    )


def get_global_mistake_detail(user_id: str, mistake_id: str) -> dict | None:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, question_id, title, chapter, wrong_times,
                       last_selected_answer, correct_answer, analysis
                FROM mistakes
                WHERE user_id = %s AND id = %s AND status = 'ACTIVE'
                """,
                (user_id, mistake_id),
            )
            row = cursor.fetchone()
    if not row:
        return None
    return _build_mistake_detail(
        detail_id=row["id"],
        question_id=row.get("question_id") or "",
        title=row.get("title") or "",
        chapter=row.get("chapter") or "",
        selected_answer=row.get("last_selected_answer") or "",
        correct_answer=row.get("correct_answer") or "",
        analysis=row.get("analysis") or "",
        wrong_times=int(row.get("wrong_times") or 0),
    )


def list_practice_trends(user_id: str) -> list[dict]:
    ensure_practice_schema()
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT accuracy, created_at
                FROM practice_records
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 7
                """,
                (user_id,),
            )
            rows = list(reversed(cursor.fetchall()))
    return [
        {
            "label": _format_date(row.get("created_at"))[5:],
            "value": max(0, min(100, int(row.get("accuracy") or 0))),
        }
        for row in rows
    ]


def count_active_mistakes(user_id: str) -> int:
    with create_mysql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM mistakes
                WHERE user_id = %s AND status = 'ACTIVE'
                """,
                (user_id,),
            )
            row = cursor.fetchone() or {}
    return int(row.get("total") or 0)


def _build_mistake_detail(
    detail_id: str,
    question_id: str,
    title: str,
    chapter: str,
    selected_answer: str,
    correct_answer: str,
    analysis: str,
    wrong_times: int,
    fallback_type: str = "",
    fallback_type_label: str = "",
) -> dict:
    question_row = get_question_by_id(question_id)
    if question_row:
        question = serialize_question_detail(question_row)
    else:
        question = {
            "id": question_id,
            "type": fallback_type,
            "typeLabel": fallback_type_label,
            "stem": title or "未命名题目",
            "options": [],
            "answer": correct_answer,
            "analysis": analysis,
            "knowledge": {},
            "importance": None,
        }
    return {
        "id": detail_id,
        "questionId": question_id,
        "title": question.get("stem") or title or "未命名题目",
        "chapter": chapter or "练习题",
        "type": question.get("type") or fallback_type,
        "typeLabel": question.get("typeLabel") or fallback_type_label,
        "stem": question.get("stem") or title or "",
        "options": question.get("options") or [],
        "selectedAnswer": selected_answer,
        "correctAnswer": correct_answer or question.get("answer") or "",
        "analysis": analysis or question.get("analysis") or "",
        "wrongTimes": wrong_times,
        "knowledge": question.get("knowledge") or {},
        "importance": question.get("importance"),
    }


def _format_record_summary(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row.get("title") or "练习结果",
        "type": row.get("type") or "练习",
        "score": f"{int(row.get('accuracy') or 0)}%",
        "date": _format_date(row.get("created_at")),
        "dateTime": _format_datetime(row.get("created_at")),
        "accuracy": int(row.get("accuracy") or 0),
        "answeredCount": int(row.get("total_count") or 0),
        "correctCount": int(row.get("correct_count") or 0),
        "wrongCount": int(row.get("wrong_count") or 0),
    }


def _format_date(value) -> str:
    dt = _to_local_datetime(value)
    return dt.strftime("%Y-%m-%d")


def _format_datetime(value) -> str:
    dt = _to_local_datetime(value)
    return dt.strftime("%Y-%m-%d %H:%M")


def _to_local_datetime(value) -> datetime:
    return _to_datetime(value) + timedelta(hours=8)


def _to_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now()
    if isinstance(value, str):
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:19], pattern)
            except ValueError:
                continue
    return datetime.now()
