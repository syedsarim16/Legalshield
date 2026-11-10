"""Module 3: statute lookup and offence classification (F-01, F-02).
Classification comes ONLY from the stored, reviewed data. The LLM never decides it."""
import re

from app.config import settings
from app.db import func, select
from app.models import StatuteSection

from .lexicon import normalise_query
from .retrieval import Bm25Index, statute_doc

_NUM = re.compile(r"\b(\d{1,3}(?:-?[A-Za-z]{1,2})?)\b")


def norm_law(law: str | None) -> str | None:
    if law is None:
        return None
    m = {"ppc": "PPC", "crpc": "CrPC"}
    return m.get(law.strip().lower())


def norm_number(number: str) -> str:
    return number.strip().upper()


def _visible(stmt):
    if not settings.allow_unreviewed_statutes:
        stmt = stmt.where(StatuteSection.reviewed_by_advisor == True)  # noqa: E712
    return stmt


def to_d01(r: StatuteSection) -> dict:
    return {
        "law": r.law,
        "section_number": r.section_number,
        "title": r.title,
        "chapter": r.chapter,
        "text_en": r.text_en,
        "kind": r.kind,
        "bailable": r.bailable,
        "cognizable": r.cognizable,
        "compoundable": r.compoundable,
        "punishment": r.punishment,
        "triable_by": r.triable_by,
        "source_ref": r.source_ref,
        "version": r.version,
        "reviewed_by_advisor": r.reviewed_by_advisor,
    }


def summary(r: StatuteSection) -> dict:
    return {
        "law": r.law,
        "section_number": r.section_number,
        "title": r.title,
        "kind": r.kind,
        "bailable": r.bailable,
        "cognizable": r.cognizable,
        "compoundable": r.compoundable,
    }


def get_section(db, law: str, number: str) -> StatuteSection | None:
    """F-01"""
    law_n = norm_law(law)
    if law_n is None:
        return None
    stmt = _visible(
        select(StatuteSection).where(
            StatuteSection.law == law_n, func.upper(StatuteSection.section_number) == norm_number(number)
        )
    )
    return db.scalar(stmt)


def all_rows(db, law: str | None = None) -> list[StatuteSection]:
    stmt = _visible(select(StatuteSection))
    if law:
        stmt = stmt.where(StatuteSection.law == law)
    return list(db.scalars(stmt))


def search_rows(db, query: str, law: str | None = None, limit: int = 10, min_score: float = 0.0) -> list[StatuteSection]:
    """F-02: exact section-number matches first, then keyword (BM25) matches."""
    q = (query or "").strip()
    if not q:
        return []
    law_n = norm_law(law) if law else None
    rows = all_rows(db, law_n)
    by_number: dict[str, list[StatuteSection]] = {}
    for r in rows:
        by_number.setdefault(r.section_number.upper(), []).append(r)

    out: list[StatuteSection] = []
    seen: set[str] = set()
    for m in _NUM.finditer(q):
        for r in by_number.get(m.group(1).upper(), []):
            if r.id not in seen:
                out.append(r)
                seen.add(r.id)

    index = Bm25Index([(r.id, statute_doc(r)) for r in rows])
    by_id = {r.id: r for r in rows}
    for rid, score in index.search(normalise_query(q), k=limit):
        if score >= min_score and rid not in seen:
            out.append(by_id[rid])
            seen.add(rid)
    return out[:limit]
