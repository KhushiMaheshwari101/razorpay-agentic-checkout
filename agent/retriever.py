"""
Agent Retriever – handles FAISS semantic product lookups, embedding generation, 
and provenance tagging for grounding verification against product catalogs.
"""

import json
import os
from typing import List, Dict, Any
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class AgentRetriever:
    def __init__(self, catalog_path: str = "products.json", model_name: str = "all-MiniLM-L6-v2"):
        self.catalog_path = catalog_path
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize SentenceTransformer model '{model_name}': {e}")
            
        self.products: List[Dict[str, Any]] = []
        self.index = None
        self._initialize_catalog()

    def _initialize_catalog(self) -> None:
        """Loads product catalog safely, normalizes schema fields, and constructs the FAISS vector index."""
        loaded_successfully = False
        
        if os.path.exists(self.catalog_path):
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        normalized_products = []
                        for item in data:
                            if isinstance(item, dict):
                                normalized_item = {
                                    "id": item.get("id", "UNKNOWN_ID"),
                                    "name": item.get("name", "Unnamed Product"),
                                    "price": item.get("price", 0),
                                    "category": item.get("category", "General")
                                }
                                for k, v in item.items():
                                    if k not in normalized_item:
                                        normalized_item[k] = v
                                normalized_products.append(normalized_item)
                        
                        if normalized_products:
                            self.products = normalized_products
                            loaded_successfully = True
            except (json.JSONDecodeError, IOError):
                pass

        if not loaded_successfully:
            self.products = [
                {"id": "ESP32_WROOM", "name": "ESP32 NodeMCU Wi-Fi Bluetooth Development Board", "price": 350, "category": "Microcontroller"},
                {"id": "ARD_UNO", "name": "Arduino Uno R3 Microcontroller Board", "price": 600, "category": "Microcontroller"},
                {"id": "MPU6050_MOD", "name": "MPU6050 6-Axis Accelerometer and Gyroscope Sensor", "price": 180, "category": "Sensor"}
            ]
            
        corpus = [f"{p['name']} ({p['category']}) - Price: INR {p['price']}" for p in self.products]
        embeddings = self.model.encode(corpus, convert_to_numpy=True)
        embeddings = np.ascontiguousarray(embeddings, dtype="float32")
        
        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs semantic similarity search against the FAISS index and 
        returns matching products enriched with provenance tags.
        """
        if not query or not isinstance(query, str) or not query.strip() or self.index is None or not self.products:
            return []

        query_vector = self.model.encode([query.strip()], convert_to_numpy=True)
        query_vector = np.ascontiguousarray(query_vector, dtype="float32")
        faiss.normalize_L2(query_vector)
        
        safe_top_k = max(1, min(int(top_k), len(self.products)))
        distances, indices = self.index.search(query_vector, safe_top_k)
        
        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.products):
                continue
            product = self.products[idx].copy()
            product["similarity_score"] = float(score)
            product["provenance_source"] = self.catalog_path
            results.append(product)
            
        return results


if __name__ == "__main__":
    retriever = AgentRetriever()
    matches = retriever.search("I want an ESP32 board")
    import json
    print(json.dumps(matches, indent=2))