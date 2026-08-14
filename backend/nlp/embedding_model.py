"""
Embedding Model Wrapper — Thin wrapper around sentence-transformers.
Uses cached miniLM model for computing semantic similarity between titles.
"""

import numpy as np
from loguru import logger

_model = None

def get_embedding_model():
    """Lazy load the sentence-transformers model to save memory/startup time."""
    global _model
    if _model is None:
        logger.info("Initializing SentenceTransformer 'all-MiniLM-L6-v2' (approx. 80MB download/load)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

class SemanticEmbedder:
    """Caches text embeddings to avoid redundant computation during a batch run."""
    def __init__(self):
        self._cache = {}
        
    def get_embedding(self, text: str) -> np.ndarray:
        if not text:
            # Return a zero vector of size 384 for empty text
            return np.zeros(384)
            
        MAX_CHARS = 2000  # keep well under the model's token limit for safety
        clean_text = text.strip().lower()[:MAX_CHARS]
        if clean_text not in self._cache:
            model = get_embedding_model()
            # encode returns a numpy array
            self._cache[clean_text] = model.encode(clean_text)
            
        return self._cache[clean_text]
        
    def compute_max_similarity(self, candidate_text: str, target_texts: list[str]) -> float:
        """
        Embed candidate_text and target_texts, compute cosine similarity,
        and return the maximum similarity score (0.0 to 1.0).
        """
        if not candidate_text or not target_texts:
            return 0.0
            
        cand_emb = self.get_embedding(candidate_text)
        
        best_sim = 0.0
        for target in target_texts:
            if not target:
                continue
            target_emb = self.get_embedding(target)
            
            # Compute cosine similarity
            dot_prod = np.dot(cand_emb, target_emb)
            norm_cand = np.linalg.norm(cand_emb)
            norm_target = np.linalg.norm(target_emb)
            
            if norm_cand > 0.0 and norm_target > 0.0:
                sim = float(dot_prod / (norm_cand * norm_target))
                # Bound similarity to [0.0, 1.0] range
                sim = max(0.0, min(1.0, sim))
                if sim > best_sim:
                    best_sim = sim
            
        return best_sim


# Alias for backward compatibility
TitleEmbedder = SemanticEmbedder

