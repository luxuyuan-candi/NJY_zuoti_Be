from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import get_settings


SOFT_SKILL_KEYWORDS = (
    "着装",
    "仪容",
    "仪表",
    "仪态",
    "态度",
    "微笑",
    "语言",
    "礼貌",
    "礼仪",
    "普通话",
    "热情",
    "文明用语",
    "服务用语",
    "站姿",
    "坐姿",
    "姿态",
    "眼神",
    "表情",
    "迎送",
    "工作牌",
    "临场表现",
    "举止",
    "自然大方",
    "灵活应变",
    "对答如流",
    "不紧张",
    "不拘束",
)


class PracticalEvaluationError(RuntimeError):
    pass


def extract_practical_core_points(question_row: dict[str, Any]) -> list[str]:
    content = question_row.get("content") or {}
    candidates: list[str] = []

    key_points = content.get("keyPoints") or ""
    if isinstance(key_points, str):
        candidates.extend(_split_lines(key_points))

    for row in content.get("scoringRows") or []:
        if not isinstance(row, list):
            continue
        text = _stringify_scoring_row(row)
        if text:
            candidates.append(text)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = _normalize(item)
        if not normalized or _is_soft_skill_item(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item.strip())
    return deduped


def format_practical_reference_answer(question_row: dict[str, Any]) -> str:
    core_points = extract_practical_core_points(question_row)
    if not core_points:
        return "请围绕题目涉及的核心业务知识点作答。"
    return "\n".join(f"{index + 1}. {item}" for index, item in enumerate(core_points))


def grade_practical_answer(question_row: dict[str, Any], user_answer: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise PracticalEvaluationError("AI 判题服务未配置。")

    answer_text = (user_answer or "").strip()
    if not answer_text:
        raise PracticalEvaluationError("请输入作答内容后再提交。")

    reference_answer = format_practical_reference_answer(question_row)
    content = question_row.get("content") or {}
    prompt = "\n".join(
        part
        for part in [
            f"题目：{question_row.get('stem') or ''}",
            f"考评准备：{content.get('preparation') or ''}",
            f"考评步骤：{content.get('steps') or ''}",
            f"注意事项：{content.get('notes') or ''}",
            "核心要点：",
            reference_answer,
            f"考生作答：{answer_text}",
        ]
        if part
    )
    system_prompt = (
        "你是医药商品购销员实操题判卷助手。"
        "只按照提供的核心要点判定知识点是否覆盖，不要把着装、态度、语言礼仪作为评分依据。"
        "请返回严格 JSON，不要输出任何额外文本。"
        "JSON 字段必须包含：correct(boolean)、analysis(string)、referenceAnswer(string)。"
        "当答案覆盖主要核心要点且没有明显事实错误时，correct 为 true；否则为 false。"
        "analysis 需要简要说明命中和缺失的知识点。"
    )

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 800,
    }
    base_url = settings.deepseek_base_url.rstrip("/")

    try:
        with httpx.Client(timeout=25.0) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        response.raise_for_status()
        response_json = response.json()
        content_text = (
            (((response_json.get("choices") or [{}])[0]).get("message") or {}).get("content")
            or ""
        )
        parsed = _parse_json_response(content_text)
    except PracticalEvaluationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PracticalEvaluationError("AI 判题服务暂不可用，请稍后重试。") from exc

    ai_reference_answer = str(parsed.get("referenceAnswer") or "").strip()
    if not ai_reference_answer or _normalize(ai_reference_answer) == _normalize(answer_text):
        ai_reference_answer = reference_answer

    return {
        "questionId": question_row.get("_id") or "",
        "correct": bool(parsed.get("correct")),
        "answer": ai_reference_answer,
        "analysis": parsed.get("analysis") or "当前题目暂无解析。",
    }


def _split_lines(text: str) -> list[str]:
    parts = re.split(r"[\n\r]+|[；;]+", text)
    return [_clean_line(part) for part in parts if _clean_line(part)]


def _stringify_scoring_row(row: list[Any]) -> str:
    cells = [str(cell).strip() for cell in row if str(cell or "").strip()]
    if not cells:
        return ""
    header_tokens = ("序号", "考核内容", "考核要点", "评分标准", "分值", "扣分", "得分", "项目")
    joined = "".join(cells)
    if "考核要点" in joined and "评分标准" in joined:
        return ""
    if cells[0] == "合计":
        return ""

    meaningful: list[str] = []
    for cell in cells:
        normalized = _normalize(cell)
        if not normalized:
            continue
        if any(token in normalized for token in header_tokens):
            continue
        if "扣" in normalized:
            continue
        if re.fullmatch(r"[0-9.]+分?", normalized):
            continue
        meaningful.append(cell)
    text = "；".join(meaningful[:2] if len(meaningful) >= 2 else meaningful)
    return _clean_line(text)


def _clean_line(text: str) -> str:
    cleaned = re.sub(r"^[0-9一二三四五六七八九十、.．\-\s]+", "", str(text or "").strip())
    return cleaned.strip("：:;； ")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def _is_soft_skill_item(normalized_text: str) -> bool:
    return any(keyword in normalized_text for keyword in SOFT_SKILL_KEYWORDS)


def _parse_json_response(content_text: str) -> dict[str, Any]:
    stripped = (content_text or "").strip()
    if not stripped:
        raise PracticalEvaluationError("AI 判题结果为空。")
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    if not stripped.startswith("{"):
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise PracticalEvaluationError("AI 判题结果格式不可解析。")
        stripped = match.group(0)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise PracticalEvaluationError("AI 判题结果格式不可解析。") from exc
    if not isinstance(parsed, dict):
        raise PracticalEvaluationError("AI 判题结果格式不可解析。")
    return parsed
