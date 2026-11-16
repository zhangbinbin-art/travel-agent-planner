"""构建景点知识库索引（RAG）。

用法：
    cd backend
    .venv\\Scripts\\python.exe scripts\\build_rag_index.py

产出：
    backend/data/rag/docs.jsonl     每行一个片段（含元数据）
    backend/data/rag/vectors.npz    归一化向量矩阵

语料范围（按约定不含游记正文）：
1) 景点简介块：名称/城市/标签/票价/地址/评分 + description
2) 景点点评块：该景点评论按点赞数取前 8 条，附情感统计

重复运行会全量重建，保证与数据库一致。
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal  # noqa: E402
from models import Comment, Spot  # noqa: E402
from services.rag.embedder import MODEL_NAME, embed_texts  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_DIR = os.path.join(BASE_DIR, "data", "rag")
DOCS_PATH = os.path.join(RAG_DIR, "docs.jsonl")
VECTORS_PATH = os.path.join(RAG_DIR, "vectors.npz")

MAX_REVIEWS = 8
REVIEW_EXCERPT = 60


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:limit]


def spot_doc(spot: Spot) -> dict:
    """景点简介块。"""
    parts = [
        "景点：%s" % (spot.name or ""),
        "城市：%s" % (spot.city or ""),
        "省份：%s" % (spot.province or ""),
        "标签：%s" % (spot.tags or "无"),
        "主题：%s" % (spot.theme or "无"),
        "票价：%s 元" % (float(spot.price or 0)),
        "评分：%s" % (spot.score or 0),
    ]
    # 由名称推导场所类型，帮助「下雨天/室内」这类问题检索（规则透明、可解释）
    indoor_keywords = ("博物馆", "博物院", "纪念馆", "美术馆", "大剧院", "图书馆", "展览馆", "科学中心")
    if any(k in (spot.name or "") for k in indoor_keywords):
        parts.append("场所类型：室内（雨天、高温天气可优先考虑）")
        parts.append("适合场景：下雨天、室内活动、避雨、避暑")
    else:
        parts.append("场所类型：户外")
        parts.append("适合场景：户外活动、晴天出行")
    if spot.address:
        parts.append("地址：%s" % spot.address)
    if spot.description:
        parts.append("简介：%s" % _truncate(spot.description, 300))
    return {
        "spot_id": spot.id,
        "spot": spot.name,
        "city": spot.city,
        "tags": spot.tags or "",
        "price": float(spot.price or 0),
        "kind": "spot",
        "source": "spots#%s" % spot.id,
        "text": "；".join(parts),
    }


def review_doc(spot: Spot, comments) -> dict | None:
    """景点点评块：取点赞数最高的评论，附情感统计。"""
    if not comments:
        return None
    picked = sorted(comments, key=lambda c: (-(c.like_count or 0), c.id))[:MAX_REVIEWS]
    sentiment = Counter((c.sentiment or "neutral") for c in comments)
    texts = []
    for c in picked:
        content = _truncate(c.content or "", REVIEW_EXCERPT)
        if content:
            texts.append("%s. %s（%s分）" % (len(texts) + 1, content, c.score if c.score is not None else 5))
    if not texts:
        return None
    scores = [float(c.score) for c in comments if c.score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else None
    head = "景点「%s」点评：共 %d 条" % (spot.name, len(comments))
    if avg_score is not None:
        head += "，平均评分 %s" % avg_score
    head += "；情感分布：好评 %d / 中性 %d / 差评 %d" % (
        sentiment.get("positive", 0), sentiment.get("neutral", 0), sentiment.get("negative", 0)
    )
    return {
        "spot_id": spot.id,
        "spot": spot.name,
        "city": spot.city,
        "tags": spot.tags or "",
        "price": float(spot.price or 0),
        "kind": "review",
        "source": "comments#spot_%s" % spot.id,
        "text": head + "。" + "；".join(texts),
    }


def main() -> None:
    os.makedirs(RAG_DIR, exist_ok=True)
    db = SessionLocal()
    try:
        spots = db.query(Spot).all()
        print("景点总数：%d" % len(spots), flush=True)

        docs = []
        for spot in spots:
            docs.append(spot_doc(spot))
            comments = db.query(Comment).filter(Comment.spot_id == spot.id).all()
            review = review_doc(spot, comments)
            if review:
                docs.append(review)

        print("片段数量：%d（简介 %d / 点评 %d）" % (
            len(docs),
            sum(1 for d in docs if d["kind"] == "spot"),
            sum(1 for d in docs if d["kind"] == "review"),
        ), flush=True)
    finally:
        db.close()

    print("向量模型：%s，开始编码（首次会下载模型）…" % MODEL_NAME, flush=True)
    vectors = embed_texts([d["text"] for d in docs])
    print("编码完成，矩阵形状：%s" % (vectors.shape,), flush=True)

    with open(DOCS_PATH, "w", encoding="utf-8", newline="\n") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    import numpy as np
    np.savez_compressed(VECTORS_PATH, vectors=vectors)

    print("已写入：%s" % DOCS_PATH, flush=True)
    print("已写入：%s" % VECTORS_PATH, flush=True)
    print("\n样例片段：")
    for doc in docs[:2]:
        print("- [%s] %s" % (doc["kind"], doc["text"][:120]))


if __name__ == "__main__":
    main()
