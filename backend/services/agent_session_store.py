"""Agent 会话持久化：把多轮记忆、工具事实、偏好快照落到本地 JSON 文件。

目录：backend/data/agent_sessions/<session_id>.json
结构：{"messages": [...], "facts": [...], "snapshot": {...}, "updated_at": 时间戳}

目的：后端重启后仍能继续上一轮对话（原先只存在进程内字典里）。
单文件读写 + 原子替换，异常时静默降级为不持久化，不影响主流程。
"""
import json
import os
import time
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DIR = os.path.join(BASE_DIR, "data", "agent_sessions")


def _path(session_id: str) -> str:
    safe = "".join(c for c in str(session_id or "") if c.isalnum() or c in "-_")[:64]
    return os.path.join(SESSION_DIR, "%s.json" % safe)


def save(session_id: str, messages: list, facts: list, snapshot: dict) -> None:
    """保存会话状态；任何异常都只打日志，不向上抛。"""
    if not session_id:
        return
    try:
        os.makedirs(SESSION_DIR, exist_ok=True)
        payload = {
            "messages": messages or [],
            "facts": facts or [],
            "snapshot": snapshot or {},
            "updated_at": int(time.time()),
        }
        path = _path(session_id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as exc:
        print("[agent-session] 保存失败 session=%s err=%s" % (session_id, exc), flush=True)


def load(session_id: str) -> Optional[dict]:
    """读取会话状态；不存在或损坏时返回 None。"""
    if not session_id:
        return None
    try:
        path = _path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return {
            "messages": data.get("messages") or [],
            "facts": data.get("facts") or [],
            "snapshot": data.get("snapshot") or {},
        }
    except Exception as exc:
        print("[agent-session] 读取失败 session=%s err=%s" % (session_id, exc), flush=True)
        return None


def delete(session_id: str) -> None:
    """清空会话（/ai/agent/reset 时调用）。"""
    if not session_id:
        return
    try:
        path = _path(session_id)
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:
        print("[agent-session] 删除失败 session=%s err=%s" % (session_id, exc), flush=True)
