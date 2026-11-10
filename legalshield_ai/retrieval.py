"""Small dependency-free BM25 retriever over statute rows.

NOTE: the plan names ChromaDB (embeddings). BM25 works offline and needs no model download,
and is fine for the sample/first dataset. Swap this module for a vector store later;
chat.py only depends on Bm25Index.search()."""
import math
import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9]+|[\u0600-\u06FF]+")
STOPWORDS = {
    "a", "an", "the", "of", "to", "in", "on", "at", "for", "and", "or", "is", "are", "was", "were", "be", "by",
    "it", "this", "that", "with", "as", "i", "me", "my", "you", "your", "can", "do", "does", "did", "what", "how",
    "when", "where", "who", "why", "which", "tell", "about", "please", "there", "any", "if", "not", "no", "so",
    "he", "she", "they", "them", "his", "her", "from", "have", "has", "had", "will", "would", "should", "could",
    "am", "been", "being", "than", "then", "also", "into", "out", "up", "such", "shall", "may", "must", "us",
}


def stem(tok: str) -> str:
    if len(tok) > 5 and tok.endswith("ing"):
        return tok[:-3]
    if len(tok) > 4 and tok.endswith("ied"):
        return tok[:-3] + "y"
    if len(tok) > 4 and tok.endswith("ed"):
        return tok[:-2]
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 4 and tok.endswith("es"):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokens(text: str) -> list[str]:
    return [stem(t) for t in _WORD.findall(text.lower()) if t not in STOPWORDS]


class Bm25Index:
    def __init__(self, docs: list[tuple[object, str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.keys = [k for k, _ in docs]
        self.doc_tokens = [Counter(tokens(t)) for _, t in docs]
        self.doc_len = [sum(c.values()) for c in self.doc_tokens]
        self.n = len(docs)
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        df: Counter = Counter()
        for c in self.doc_tokens:
            df.update(c.keys())
        self.idf = {t: math.log(1 + (self.n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int = 5) -> list[tuple[object, float]]:
        q = set(tokens(query))
        scored: list[tuple[object, float]] = []
        for i, counts in enumerate(self.doc_tokens):
            score = 0.0
            for t in q:
                tf = counts.get(t, 0)
                if not tf:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * self.doc_len[i] / (self.avgdl or 1))
                score += self.idf[t] * tf * (self.k1 + 1) / denom
            if score > 0:
                scored.append((self.keys[i], score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


def statute_doc(row) -> str:
    return " ".join(
        filter(None, [row.title, row.title, row.text_en, row.punishment, row.chapter, row.law, row.section_number])
    )
