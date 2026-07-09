"""
Knowledge Retrieval (RAG)
-------------------------
Each role has its own knowledge-base text file (a curated corpus/textbook
excerpt). At ingest time we chunk it and store embeddings in a per-role
ChromaDB collection. At query time we retrieve the top-K most relevant
chunks for a generated query string.
"""
import os
import pickle
import logging
from typing import List

import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import settings

logger = logging.getLogger("rag_engine")

_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


class TfidfEmbeddingFunction:
    """
    Fully offline embedding function based on TF-IDF.

    Chroma's bundled embedding models require a one-time download from the
    internet, and heavier alternatives (sentence-transformers) require torch.
    Since this system is designed to run fully locally alongside Ollama, we
    embed with a TF-IDF vectorizer fit on each role's own knowledge base at
    ingest time and persist it to disk so queries reuse the exact same
    vector space. Swap this out for SentenceTransformerEmbeddingFunction if
    you have GPU/network available and want stronger semantic retrieval.
    """

    def __init__(self, role_key: str, dim: int = 384):
        self.role_key = role_key
        self.dim = dim
        self._path = os.path.join(settings.CHROMA_PERSIST_DIR, f"tfidf_{role_key}.pkl")
        self.vectorizer: TfidfVectorizer | None = self._load()

    def _load(self):
        if os.path.exists(self._path):
            with open(self._path, "rb") as f:
                return pickle.load(f)
        return None

    def fit(self, documents: List[str]):
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        vectorizer = TfidfVectorizer(max_features=self.dim, stop_words="english")
        vectorizer.fit(documents)
        with open(self._path, "wb") as f:
            pickle.dump(vectorizer, f)
        self.vectorizer = vectorizer

    def __call__(self, input: List[str]):
        if self.vectorizer is None:
            raise RuntimeError(
                f"TF-IDF vectorizer for role '{self.role_key}' is not fitted yet. "
                f"Run scripts/ingest_kb.py first."
            )
        matrix = self.vectorizer.transform(input).toarray()
        # Pad to a fixed dimensionality so short vocabularies still match self.dim.
        if matrix.shape[1] < self.dim:
            pad = self.dim - matrix.shape[1]
            import numpy as np
            matrix = np.pad(matrix, ((0, 0), (0, pad)))
        return matrix.tolist()


_embedders: dict = {}


def _get_embedder(role_key: str) -> TfidfEmbeddingFunction:
    if role_key not in _embedders:
        _embedders[role_key] = TfidfEmbeddingFunction(role_key)
    return _embedders[role_key]


def _collection_name(role_key: str) -> str:
    return f"kb_{role_key}"


def get_or_create_collection(role_key: str):
    return _client.get_or_create_collection(
        name=_collection_name(role_key),
        embedding_function=_get_embedder(role_key),
        metadata={"role": role_key},
    )


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Prefer chunking on natural paragraph boundaries (each paragraph in our
    knowledge base corresponds to one coherent sub-topic), since that keeps
    retrieved context focused. Falls back to a fixed word-window with
    overlap for any paragraph that's still larger than chunk_size.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    for para in paragraphs:
        words = para.split()
        if len(words) <= chunk_size:
            chunks.append(para)
            continue
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            start += chunk_size - overlap
    return chunks


def ingest_role_kb(role_key: str, file_path: str) -> int:
    """Reads a role's knowledge base file, chunks it, and (re)indexes it in Chroma."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    if not chunks:
        return 0

    # Reset the collection so re-running ingestion doesn't duplicate chunks.
    try:
        _client.delete_collection(_collection_name(role_key))
    except Exception:
        pass

    # Fit (or re-fit) the TF-IDF vectorizer on this role's corpus first, so
    # both documents and future queries are embedded in the same space.
    embedder = _get_embedder(role_key)
    embedder.fit(chunks)

    collection = get_or_create_collection(role_key)

    ids = [f"{role_key}_{i}" for i in range(len(chunks))]
    metadatas = [{"role": role_key, "chunk_index": i} for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    logger.info("Ingested %d chunks for role '%s'", len(chunks), role_key)
    return len(chunks)


def retrieve_context(role_key: str, query: str, top_k: int = None) -> List[str]:
    top_k = top_k or settings.TOP_K_CHUNKS
    try:
        collection = get_or_create_collection(role_key)
        if collection.count() == 0:
            return []
        results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))
        return results.get("documents", [[]])[0]
    except Exception as exc:
        logger.warning("Retrieval failed for role=%s query=%s: %s", role_key, query, exc)
        return []


def kb_is_ready(role_key: str) -> bool:
    try:
        return get_or_create_collection(role_key).count() > 0
    except Exception:
        return False
