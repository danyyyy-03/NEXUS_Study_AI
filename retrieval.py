"""Small, fully local lexical retrieval index with source labels."""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import math
import re
from .documents import Passage, StudyDocument

STOPWORDS = set("a an and are as at be but by can do for from have how in into is it its of on or our the their there these this those to was were what when where which who why will with your you about could would should please explain tell me does did i we my it that is a some under over than then between using use if not no more less from this that".split())


@dataclass(frozen=True)
class Chunk:
    source: str
    locator: str
    text: str
    part: int

    @property
    def label(self) -> str:
        return f"{self.source} — {self.locator}, part {self.part}"


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[^\W_]+", text.casefold(), re.UNICODE) if len(w) > 1 and w not in STOPWORDS]


def split_passage(p: Passage, max_chars: int = 1350, overlap: int = 130) -> list[Chunk]:
    if not 0 <= overlap < max_chars:
        raise ValueError("overlap must be smaller than max_chars")
    result: list[Chunk] = []
    s = p.text
    start = 0
    while start < len(s):
        end = min(start + max_chars, len(s))
        if end < len(s):
            # Prefer a word or paragraph boundary within the latter third.
            cut = max(s.rfind("\n", start + max_chars // 2, end), s.rfind(" ", start + max_chars // 2, end))
            if cut > start + max_chars // 2:
                end = cut + 1
        result.append(Chunk(p.source, p.locator, s[start:end].strip(), len(result) + 1))
        if end == len(s):
            break
        start = max(start + 1, end - overlap)
    return result


def build_index(documents: list[StudyDocument]) -> list[Chunk]:
    return [part for document in documents for page in document.passages for part in split_passage(page)]


def retrieve(chunks: list[Chunk], question: str, limit: int = 5, max_total_chars: int = 6200) -> list[Chunk]:
    terms = Counter(tokens(question))
    if not terms or not chunks:
        return []
    document_frequencies = Counter(t for chunk in chunks for t in set(tokens(chunk.text)))
    scored = []
    n = len(chunks)
    for i, chunk in enumerate(chunks):
        counts = Counter(tokens(chunk.text))
        length = max(sum(counts.values()), 1)
        score = sum(freq * math.log(1 + (n - document_frequencies[word] + 0.5) / (document_frequencies[word] + 0.5)) * (2.2 * counts[word]) / (counts[word] + 1.2 * (0.25 + 0.75 * length / 180)) for word, freq in terms.items() if counts[word])
        if score > 0:
            scored.append((score, i, chunk))
    scored.sort(key=lambda x: (-x[0], x[1]))
    picked, total = [], 0
    for _, _, chunk in scored:
        if len(picked) >= limit:
            break
        if total + len(chunk.text) > max_total_chars:
            continue
        picked.append(chunk)
        total += len(chunk.text)
    return picked


def representative_chunks(chunks: list[Chunk], count: int = 5, max_chars: int = 6200) -> list[Chunk]:
    if not chunks:
        return []
    count = max(1, min(count, len(chunks)))
    if count == 1:
        indices = [0]
    else:
        indices = list(dict.fromkeys(round(i * (len(chunks) - 1) / (count - 1)) for i in range(count)))
    chosen, total = [], 0
    for idx in indices:
        c = chunks[idx]
        if total + len(c.text) <= max_chars:
            chosen.append(c)
            total += len(c.text)
    return chosen


def format_sources(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[SOURCE {i}] {chunk.label}\n{chunk.text}" for i, chunk in enumerate(chunks, start=1))
