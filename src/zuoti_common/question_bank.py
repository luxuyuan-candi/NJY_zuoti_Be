from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from .clients import create_mongodb_client
from .config import get_settings


LEVEL_ORDER = {
    "PRIMARY": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
}

TYPE_LABELS = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "true_false": "判断题",
}


def get_question_db():
    settings = get_settings()
    client = create_mongodb_client()
    return client[settings.mongodb_database]


def list_practice_sets() -> list[dict[str, Any]]:
    db = get_question_db()
    rows = list(
        db["practice_sets"].find(
            {"status": "ACTIVE"},
            {
                "_id": 1,
                "name": 1,
                "level": 1,
                "levelLabel": 1,
                "questionCount": 1,
                "sheetName": 1,
                "mappingWorkbook": 1,
            },
        )
    )
    rows.sort(key=lambda item: (LEVEL_ORDER.get(item.get("level") or "", 99), item["_id"]))

    return [
        {
            "id": item["_id"],
            "type": f"{item.get('levelLabel') or ''}理论",
            "name": item.get("name") or item["_id"],
            "desc": f"来源于 {item.get('sheetName') or '题库导入'}，共 {item.get('questionCount') or 0} 题。",
            "total": item.get("questionCount") or 0,
            "done": 0,
            "accuracy": 0,
            "cached": "在线题库",
            "authorized": True,
            "level": item.get("level") or "",
            "levelLabel": item.get("levelLabel") or "",
            "sheetName": item.get("sheetName") or "",
            "mappingWorkbook": item.get("mappingWorkbook") or "",
        }
        for item in rows
    ]


def get_practice_set(practice_set_id: str) -> dict[str, Any] | None:
    db = get_question_db()
    item = db["practice_sets"].find_one({"_id": practice_set_id, "status": "ACTIVE"})
    if not item:
        return None
    return {
        "id": item["_id"],
        "name": item.get("name") or item["_id"],
        "level": item.get("level") or "",
        "levelLabel": item.get("levelLabel") or "",
        "questionCount": item.get("questionCount") or 0,
        "sheetName": item.get("sheetName") or "",
        "mappingWorkbook": item.get("mappingWorkbook") or "",
    }


def list_chapters(practice_set_id: str) -> list[dict[str, Any]]:
    db = get_question_db()
    rows = list(
        db["questions"].find(
            {"practiceSetId": practice_set_id},
            {"knowledge.pathNames": 1},
        )
    )

    chapter_counts: dict[tuple[str, ...], int] = defaultdict(int)
    for row in rows:
        path_names = (row.get("knowledge") or {}).get("pathNames") or []
        path_names = [part for part in path_names if part]
        chapter_path = tuple(path_names[:-1] if len(path_names) > 1 else path_names)
        if not chapter_path:
            chapter_path = ("未分类",)
        chapter_counts[chapter_path] += 1

    chapters = []
    for chapter_path, count in chapter_counts.items():
        breadcrumb = " / ".join(chapter_path[:-1])
        chapters.append(
            {
                "id": encode_chapter_key(chapter_path),
                "name": chapter_path[-1],
                "subtitle": breadcrumb,
                "path": list(chapter_path),
                "pathKey": encode_chapter_key(chapter_path),
                "total": count,
                "done": 0,
                "accuracy": 0,
                "cached": "在线题目",
            }
        )

    chapters.sort(key=lambda item: (-item["total"], item["name"]))
    return chapters


def encode_chapter_key(chapter_path: tuple[str, ...] | list[str]) -> str:
    return "|".join(chapter_path)


def decode_chapter_key(chapter_key: str | None) -> list[str]:
    if not chapter_key:
        return []
    return [part for part in chapter_key.split("|") if part]


def build_practice_questions(
    practice_set_id: str,
    chapter_key: str | None,
    count: int,
    order: str = "SEQUENTIAL",
    question_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    db = get_question_db()
    projection = {
        "_id": 1,
        "type": 1,
        "typeLabel": 1,
        "stem": 1,
        "options": 1,
        "analysis": 1,
        "answer": 1,
        "knowledge": 1,
        "importance": 1,
    }

    if question_ids:
        rows = list(
            db["questions"].find(
                {"_id": {"$in": question_ids}},
                projection,
            )
        )
        row_map = {row["_id"]: row for row in rows}
        rows = [row_map[question_id] for question_id in question_ids if question_id in row_map]
    else:
        rows = list(
            db["questions"].find(
                {"practiceSetId": practice_set_id},
                projection,
            )
        )

    chapter_path = decode_chapter_key(chapter_key)
    if chapter_path and not question_ids:
        rows = [
            row
            for row in rows
            if ((row.get("knowledge") or {}).get("pathNames") or [])[:-1] == chapter_path
        ]

    if not question_ids:
        rows.sort(key=lambda item: item["_id"])
    normalized_order = (order or "SEQUENTIAL").strip().upper()
    if normalized_order == "RANDOM":
        random.shuffle(rows)

    limited_rows = rows[: max(1, min(count, len(rows)))] if rows else []
    total = len(limited_rows)
    return [
        serialize_question_for_practice(row, index + 1, total)
        for index, row in enumerate(limited_rows)
    ]


def get_question_by_id(question_id: str) -> dict[str, Any] | None:
    db = get_question_db()
    row = db["questions"].find_one({"_id": question_id})
    if not row:
        return None
    return row


def verify_answer(question_id: str, answer: str) -> dict[str, Any] | None:
    row = get_question_by_id(question_id)
    if not row:
        return None

    correct_answer = row.get("answer") or ""
    normalized_received = (answer or "").strip().upper()
    normalized_correct = str(correct_answer).strip().upper()
    return {
        "questionId": question_id,
        "correct": normalized_received == normalized_correct,
        "answer": correct_answer,
        "analysis": row.get("analysis"),
    }


def list_questions(limit: int = 100) -> list[dict[str, Any]]:
    db = get_question_db()
    rows = list(
        db["questions"]
        .find(
            {},
            {
                "_id": 1,
                "practiceSetId": 1,
                "type": 1,
                "typeLabel": 1,
                "stem": 1,
                "answer": 1,
                "importance": 1,
                "knowledge.pathNames": 1,
            },
        )
        .sort("_id", 1)
        .limit(limit)
    )
    return [serialize_question_summary(row) for row in rows]


def serialize_question_summary(row: dict[str, Any]) -> dict[str, Any]:
    knowledge = row.get("knowledge") or {}
    return {
        "id": row["_id"],
        "practiceSetId": row.get("practiceSetId") or "",
        "type": row.get("type") or "",
        "typeLabel": row.get("typeLabel") or TYPE_LABELS.get(row.get("type") or "", ""),
        "stem": row.get("stem") or "",
        "answer": row.get("answer") or "",
        "importance": row.get("importance"),
        "knowledgePath": knowledge.get("pathNames") or [],
    }


def serialize_question_detail(row: dict[str, Any]) -> dict[str, Any]:
    knowledge = row.get("knowledge") or {}
    return {
        "id": row["_id"],
        "type": row.get("type") or "",
        "typeLabel": row.get("typeLabel") or TYPE_LABELS.get(row.get("type") or "", ""),
        "stem": row.get("stem") or "",
        "options": row.get("options") or [],
        "answer": row.get("answer") or "",
        "analysis": row.get("analysis"),
        "knowledge": knowledge,
        "importance": row.get("importance"),
    }


def serialize_question_for_practice(row: dict[str, Any], no: int, total: int) -> dict[str, Any]:
    knowledge = row.get("knowledge") or {}
    return {
        "id": row["_id"],
        "no": no,
        "total": total,
        "type": row.get("type") or "",
        "typeLabel": row.get("typeLabel") or TYPE_LABELS.get(row.get("type") or "", ""),
        "stem": row.get("stem") or "",
        "options": row.get("options") or [],
        "analysis": row.get("analysis"),
        "knowledge": knowledge,
        "importance": row.get("importance"),
    }
