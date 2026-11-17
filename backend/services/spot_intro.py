"""景点介绍生成：RAG 检索景点资料 + DeepSeek 润色。

用于「偏好面板直接生成路线」场景：路线生成后，按路线里的景点名称生成一段
通俗的景点介绍，补上对话区缺少的 AI 文字内容。

降级策略：
- 未配置 Key：直接拼接检索片段；
- 检索不到资料：返回空文本并标记 degraded；
- 调用失败：同样回退到片段拼接，不抛 500。
"""
import json
from typing import Iterable, List

import httpx

from core.config import settings
from services.rag import search as rag_search

SYSTEM_PROMPT = (
    "你是国内景点解说助手。只能依据给定的景点资料写介绍，禁止编造资料里没有的信息；"
    "把路线里的景点按顺序各写 1~2 句，总字数 150~250 字；纯文本中文，"
    "不要 markdown、不要标题、不要列表符号。"
)


def _clean_names(names: Iterable[str]) -> List[str]:
    result = []
    for name in names or []:
        text = str(name or "").strip()
        if text and text not in result:
            result.append(text)
    return result[:6]


def _collect_facts(names: List[str]) -> List[str]:
    facts = []
    for name in names:
        try:
            result = rag_search(name, top_k=1, threshold=0.2)
        except Exception:
            continue
        hits = result.get("hits") or []
        if hits:
            hit = hits[0]
            facts.append("【%s】%s" % (hit.get("spot") or name, (hit.get("text") or "")[:260]))
    return facts


def _fallback_note(facts: List[str]) -> str:
    if not facts:
        return "暂无这些景点的详细资料"
    return "；".join(facts)[:500]


def build_intro(db, spot_names: Iterable[str]) -> dict:
    """返回 {"note": 文本, "degraded": bool}，永不抛异常。"""
    names = _clean_names(spot_names)
    if not names:
        return {"note": "", "degraded": True}

    facts = _collect_facts(names)
    if not facts:
        return {"note": "暂无这些景点的详细资料", "degraded": True}

    if not (settings.DEEPSEEK_API_KEY or "").strip():
        return {"note": _fallback_note(facts), "degraded": True}

    user_content = "路线景点：%s\n\n景点资料：\n%s" % ("、".join(names), "\n".join(facts))
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "thinking": {"type": "disabled"},
    }
    url = settings.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": "Bearer %s" % settings.DEEPSEEK_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=settings.DEEPSEEK_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return {"note": _fallback_note(facts), "degraded": True}
        return {"note": content, "degraded": False}
    except Exception as exc:
        print("[spot_intro] 生成失败，降级=%s" % exc, flush=True)
        return {"note": _fallback_note(facts), "degraded": True}
