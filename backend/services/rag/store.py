"""向量检索层：加载本地索引文件，做余弦相似度检索。

索引文件：
- data/rag/vectors.npz : {"vectors": (n, dim) float32, 已归一化}
- data/rag/docs.jsonl  : 每行一个 chunk 元数据（text/spot/city/tags/...）

检索策略：
1) 查询向量与全量 chunk 做余弦（点积）；
2) 可选按城市过滤；
3) 分数阈值过滤；
4) 同一景点最多保留 per_spot 条；
5) 取 top_k。
"""
import json
import os
import threading
from typing import List, Optional

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAG_DIR = os.path.join(BASE_DIR, "data", "rag")
VECTORS_PATH = os.path.join(RAG_DIR, "vectors.npz")
# 问题未点名景点时的最低相似度（低于它视为库外问题）
NAME_MISS_THRESHOLD = 0.62
DOCS_PATH = os.path.join(RAG_DIR, "docs.jsonl")

_lock = threading.Lock()
_state = {"vectors": None, "docs": None, "loaded": False}


def _mentions(query: str, name: str, cities: set) -> bool:
    """判断问题是否点名了某个景点（支持简称：沙面 -> 沙面岛）。

    城市名片段（如「广州」）不算点名，避免「广州有滑雪场吗」被当成点名了「广州博物馆」。
    """
    if not name:
        return False
    if name in query:
        return True
    for i in range(len(name) - 1):
        frag = name[i:i + 2]
        if frag in cities:
            continue
        if frag in query:
            return True
    return False


def index_exists() -> bool:
    return os.path.exists(VECTORS_PATH) and os.path.exists(DOCS_PATH)


def _load():
    """懒加载索引；文件不存在时返回 False，不抛异常。"""
    if _state["loaded"]:
        return _state["vectors"] is not None
    with _lock:
        if _state["loaded"]:
            return _state["vectors"] is not None
        if not index_exists():
            _state["loaded"] = True
            return False
        vectors = np.load(VECTORS_PATH)["vectors"].astype(np.float32)
        docs = []
        with open(DOCS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(json.loads(line))
        if len(docs) != len(vectors):
            print("[rag] 索引不一致：docs=%d vectors=%d" % (len(docs), len(vectors)), flush=True)
            _state["loaded"] = True
            return False
        _state["vectors"] = vectors
        _state["docs"] = docs
        _state["loaded"] = True
        print("[rag] 索引加载完成：%d 条" % len(docs), flush=True)
        return True


def search(query: str, city: Optional[str] = None, top_k: int = 4,
           threshold: float = 0.30, per_spot: int = 2) -> dict:
    """检索景点知识片段；索引缺失或查询为空时返回空结果而不是异常。"""
    query = (query or "").strip()
    if not query:
        return {"query": query, "count": 0, "hits": [], "note": "查询为空"}
    if not _load():
        return {"query": query, "count": 0, "hits": [], "note": "知识库未构建，请先运行 scripts/build_rag_index.py"}

    from services.rag.embedder import embed_query

    try:
        qvec = embed_query(query)
    except Exception as exc:
        print("[rag] 查询编码失败：%s" % exc, flush=True)
        return {"query": query, "count": 0, "hits": [], "note": "向量模型不可用"}

    vectors = _state["vectors"]
    docs = _state["docs"]
    scores = vectors @ qvec

    candidates = []
    for idx, score in enumerate(scores):
        doc = docs[idx]
        if city and (doc.get("city") or "") != city:
            continue
        if float(score) < threshold:
            continue
        candidates.append((float(score), doc))
    candidates.sort(key=lambda item: -item[0])

    # 相关性护栏：问题里没有点名任何景点时，提高最低分，避免"滑雪场"这类库外问题硬凑结果
    spot_names = {doc.get("spot") for doc in docs if doc.get("spot")}
    # 支持简称命中：如「沙面」命中「沙面岛」（景点名任意两字片段出现在问题里）
    cities = {doc.get("city") for doc in docs if doc.get("city")}
    named = [name for name in spot_names if name and _mentions(query, name, cities)]
    min_score = threshold if named else max(threshold, NAME_MISS_THRESHOLD)
    candidates = [item for item in candidates if item[0] >= min_score]
    if not candidates:
        return {
            "query": query,
            "count": 0,
            "hits": [],
            "note": "知识库未收录与该问题相关的景点内容",
        }

    hits = []
    per_spot_count = {}
    for score, doc in candidates:
        spot = doc.get("spot") or ""
        if per_spot_count.get(spot, 0) >= per_spot:
            continue
        per_spot_count[spot] = per_spot_count.get(spot, 0) + 1
        hits.append({
            "spot": spot,
            "city": doc.get("city"),
            "kind": doc.get("kind"),
            "score": round(score, 3),
            "text": doc.get("text"),
            "source": doc.get("source"),
        })
        if len(hits) >= top_k:
            break

    return {"query": query, "count": len(hits), "hits": hits}
