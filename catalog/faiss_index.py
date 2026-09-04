"""
Semantic search over the product catalog using FAISS on top of TF-IDF
vectors (instead of a downloaded transformer model). This is a deliberate
robustness choice: a live demo should never depend on a network call to
HuggingFace succeeding at the exact moment you're presenting. TF-IDF is
fully local, deterministic, and more than adequate for a small catalog.

This is what the buyer agent's Retriever step calls to find candidate
products matching a natural-language user intent.
"""

import os
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from typing import List, Tuple, Optional

try:
    from catalog.schema import load_catalog, Product
except ImportError:
    try:
        from .schema import load_catalog, Product
    except ImportError:
        from schema import load_catalog, Product


class CatalogIndex:
    def __init__(self, catalog_path: Optional[str] = None):
        if catalog_path is None:
            here = os.path.dirname(os.path.abspath(__file__))
            catalog_path = os.path.join(here, "products.json")
        self.catalog_path = catalog_path
        self.catalog: list = load_catalog(catalog_path)
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self._build_index()


    def _build_index(self):
        texts = [p.searchable_text() for p in self.catalog]
        tfidf = self.vectorizer.fit_transform(texts).toarray().astype("float32")
        tfidf = normalize(tfidf)  # so inner product == cosine similarity
        self.dim = tfidf.shape[1]
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(tfidf)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05) -> list:
        """Returns top_k (Product, score) pairs above min_score, re-verifying
        provenance checksum on every hit before returning it to the agent.

        min_score matters: without it, a query with zero word-overlap
        against the catalog (e.g. "cheap plan") still returns candidates
        with score 0.000, and nothing downstream can tell those apart from
        a real match unless it inspects the score itself. Filtering here
        means the agent gets an honest empty list — "no matching product
        found" — instead of confidently-looking but meaningless results."""
        query_vec = self.vectorizer.transform([query]).toarray().astype("float32")
        query_vec = normalize(query_vec)
        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < min_score:
                continue
            product = self.catalog[idx]
            if not product.verify_integrity():
                # Provenance check failed — do not surface this candidate
                # to the agent. This is the S2I supply-chain defense.
                continue
            results.append((product, float(score)))
        return results


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    idx = CatalogIndex(os.path.join(here, "products.json"))
    for q in ["cheap plan for one person", "best plan for a big family", "4k with no ads"]:
        print(f"\nQuery: {q!r}")
        results = idx.search(q, top_k=2)
        if not results:
            print("  (no relevant match found — agent should say so, not guess)")
        for product, score in results:
            print(f"  {score:.3f}  {product.name} — ₹{product.price_inr}")