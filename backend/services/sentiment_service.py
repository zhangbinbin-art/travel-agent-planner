import re

from snownlp import SnowNLP

_PUNCT_ONLY = re.compile(r"[\W_]+")


def classify(text) -> str:
    if text is None:
        return "neutral"
    s = str(text).strip()
    if not s:
        return "neutral"
    # pure punctuation / symbols must not crash SnowNLP
    if _PUNCT_ONLY.fullmatch(s):
        return "neutral"
    try:
        score = float(SnowNLP(s).sentiments)
    except Exception:
        # third-party SnowNLP can raise on unusual input; treat as neutral
        return "neutral"
    if score > 0.6:
        return "positive"
    if score < 0.4:
        return "negative"
    return "neutral"


def analyze_comments(texts: list[str]) -> dict:
    positive = 0
    neutral = 0
    negative = 0
    for t in texts or []:
        c = classify(t)
        if c == "positive":
            positive += 1
        elif c == "negative":
            negative += 1
        else:
            neutral += 1
    total = positive + neutral + negative
    if total == 0:
        return {
            "total": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "positive_percent": 0.0,
            "neutral_percent": 0.0,
            "negative_percent": 0.0,
        }
    p = round(positive / total * 100.0, 2)
    n = round(neutral / total * 100.0, 2)
    neg = round(negative / total * 100.0, 2)
    # adjust largest bucket to make sum exactly 100.0
    s = round(p + n + neg, 2)
    if abs(s - 100.0) > 1e-9:
        # find largest
        buckets = [("p", p, positive), ("n", n, neutral), ("neg", neg, negative)]
        # sort by count desc then by current percent desc
        buckets_sorted = sorted(buckets, key=lambda x: (x[2], x[1]), reverse=True)
        diff = round(100.0 - s, 2)
        # apply diff to largest
        if buckets_sorted[0][0] == "p":
            p = round(p + diff, 2)
        elif buckets_sorted[0][0] == "n":
            n = round(n + diff, 2)
        else:
            neg = round(neg + diff, 2)
    return {
        "total": total,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "positive_percent": float(p),
        "neutral_percent": float(n),
        "negative_percent": float(neg),
    }


def get_spot_sentiment(db, spot_id: int) -> dict:
    from models import Comment, Post
    import json

    seen_ids = set()
    texts = []

    def _collect(comments):
        for c in comments:
            if c.id in seen_ids:
                continue
            seen_ids.add(c.id)
            if getattr(c, "status", 0) == 2:
                continue
            texts.append(c.content)

    # comments with spot_id directly
    _collect(db.query(Comment).filter(Comment.spot_id == spot_id).all())

    # comments from posts whose spot_ids contains spot_id (parse JSON in Python for cross-DB)
    post_ids_with_spot = []
    for post in db.query(Post).all():
        try:
            spot_ids = json.loads(post.spot_ids) if post.spot_ids else []
        except (ValueError, TypeError):
            spot_ids = []
        if isinstance(spot_ids, list) and spot_id in spot_ids:
            post_ids_with_spot.append(post.id)
    if post_ids_with_spot:
        _collect(db.query(Comment).filter(Comment.post_id.in_(post_ids_with_spot)).all())

    result = analyze_comments(texts)
    result["spot_id"] = spot_id
    return result
