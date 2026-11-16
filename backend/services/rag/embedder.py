"""RAG 向量化：本地 fastembed（BAAI/bge-small-zh-v1.5），无需 torch。

首次调用会下载模型（约 100MB），之后离线可用。
若下载缓慢，可设置环境变量 HF_ENDPOINT=https://hf-mirror.com 后重试。
"""
import os
import threading
from typing import List

import numpy as np

MODEL_NAME = os.getenv("RAG_EMBED_MODEL", "BAAI/bge-small-zh-v1.5")

_lock = threading.Lock()
_model = None


def _get_model():
    """懒加载并复用模型实例（fastembed 初始化较慢）。"""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding
                _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """批量编码，返回 (n, dim) float32 矩阵，已做 L2 归一化。"""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    vectors = np.array(list(_get_model().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def embed_query(text: str) -> np.ndarray:
    """单条查询编码，返回 (dim,) 归一化向量。"""
    return embed_texts([text])[0]
