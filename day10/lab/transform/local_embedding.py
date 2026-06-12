"""Local embedding fallback for Day 10.

Uses a deterministic hash bag-of-words embedding so the lab can run offline
without downloading SentenceTransformers from Hugging Face.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from hashlib import sha256
from typing import Iterable, List


class LocalHashEmbeddingFunction:
    """Small deterministic embedding function for Chroma."""

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = int(dimension or os.environ.get("LOCAL_EMBED_DIM", "512"))

    def name(self) -> str:
        return "local-hash"

    def __call__(self, input: Iterable[str]) -> List[List[float]]:
        return [self._embed_one(text or "") for text in input]

    def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        return [self._embed_one(text or "") for text in texts]

    def embed_query(self, input: Iterable[str] | str) -> List[float] | List[List[float]]:
        if isinstance(input, str):
            return self._embed_one(input)
        return [self._embed_one(text or "") for text in input]

    def _embed_one(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        tokens = self._tokens(text)
        if not tokens:
            return vec

        for token in tokens:
            digest = sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign

        # Add a couple of n-grams so phrase-level overlap still matters.
        for left, right in zip(tokens, tokens[1:]):
            digest = sha256(f"{left}_{right}".encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            vec[idx] += 0.5 if digest[4] & 1 else -0.5

        norm = math.sqrt(sum(v * v for v in vec))
        if norm:
            vec = [v / norm for v in vec]
        return vec

    def _tokens(self, text: str) -> List[str]:
        normalized = unicodedata.normalize("NFKC", text).lower()
        normalized = re.sub(r"[^\w\d]+", " ", normalized, flags=re.UNICODE)
        return [tok for tok in normalized.split() if tok]


def build_embedding_function(model_name: str | None = None, log=None):
    """Prefer SentenceTransformers when available, otherwise fall back offline."""
    model_name = (model_name or "").strip()
    if model_name and model_name != "local-hash":
        try:
            from chromadb.utils import embedding_functions

            return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
        except Exception as exc:  # pragma: no cover - network / model availability
            if log:
                log(f"WARN: sentence-transformers unavailable for {model_name}; fallback local-hash ({exc})")
    return LocalHashEmbeddingFunction()
