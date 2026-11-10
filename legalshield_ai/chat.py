"""Module 2: grounded legal chatbot (F-03). Retrieval -> grounded generation -> citation check."""
import re

from app.config import settings

from .disclaimers import REFUSALS, disclaimer
from .lexicon import ROMAN_URDU_MARKERS, normalise_query, tokenize_raw
from .llm import LlmClient, LlmUnavailable, ref
from .retrieval import Bm25Index, statute_doc
from .verification import all_rows, get_section, to_d01

UNSAFE = re.compile(
    r"ignore (all |your |the |any )?(previous |prior )?(rules|instructions)|disregard (the |your )?(rules|instructions)|"
    r"system prompt|jailbreak|pretend (you|to)|"
    r"(avoid|evade|escape|dodge|run from|bachna|bach ?(ke|kar)?) .{0,20}(arrest|police|giraft|pakr)|"
    r"(arrest|police|giraft)\w* se bach|hide (the )?evidence|destroy (the )?evidence|bribe|rishwat|"
    r"گرفتاری سے بچ|پولیس سے بچ",
    re.I,
)
OUT_OF_SCOPE = re.compile(
    r"\b(narcotic\w*|drugs?|charas|heroin|cocaine|anf|terror\w*|anti-?terrorism|atc|peca|cyber\w*|hacking|nab|"
    r"manshiyat|dehshat\w*|tax|divorce|khula|inheritance|custody of (the )?child)\b|منشیات|دہشت گردی|سائبر|طلاق",
    re.I,
)
REF_PREFIX = re.compile(r"(?i)\b(ppc|crpc|section|sec|dafa|dafah)\s*\.?\s*(\d{1,3}[a-z]?)\b|دفعہ\s*(\d{1,3}[a-z]?)")
REF_SUFFIX = re.compile(r"(?i)\b(\d{1,3}[a-z]?)\s*(ppc|crpc)\b")

INTENTS = [
    (re.compile(r"(?i)illegal(ly)? detain|unlawful(ly)? detain|habeas|kept .{0,20}(more than|over) 24|24 ghante|24 hours"),
     [("template", "illegal-detention-notice"), ("template", "habeas-corpus-draft")]),
    (re.compile(r"(?i)arrest|detain|custody|stopped|police|giraft|pakr|thana|حراست|گرفتار|پولیس"),
     [("guide", "lawful-arrest-steps"), ("sos", None)]),
    (re.compile(r"(?i)bail|zamanat|ضمانت"), [("guide", "bail-process-overview")]),
    (re.compile(r"(?i)harass|hiras|ہراس"), [("template", "harassment-complaint")]),
    (re.compile(r"(?i)\bfir\b|complain|shikayat|شکایت|ایف آئی آر"), [("template", "fir-application")]),
    (re.compile(r"(?i)lawyer|advocate|wakeel|wakil|وکیل"), [("directory", "lawyer")]),
]


def detect_language(text: str) -> str:
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    if arabic and arabic >= latin:
        return "ur"
    if any(t in ROMAN_URDU_MARKERS for t in tokenize_raw(text)):
        return "ur-Latn"
    return "en"


def _refs_in(text: str) -> list[tuple[str | None, str]]:
    low = text.lower()
    law = "CrPC" if "crpc" in low else "PPC" if "ppc" in low else None
    found: list[tuple[str | None, str]] = []
    for m in REF_PREFIX.finditer(text):
        num = m.group(2) or m.group(3)
        pref = (m.group(1) or "").lower()
        found.append(("PPC" if pref == "ppc" else "CrPC" if pref == "crpc" else law, num))
    for m in REF_SUFFIX.finditer(text):
        found.append(("PPC" if m.group(2).lower() == "ppc" else "CrPC", m.group(1)))
    return found


def _actions(text: str, normalised: str, first_ref: str | None) -> list[dict]:
    seen, out = set(), []
    hay = f"{text}\n{normalised}"
    for pattern, acts in INTENTS:
        if pattern.search(hay):
            for kind, target in acts:
                if (kind, target) not in seen:
                    seen.add((kind, target))
                    out.append({"type": kind, "target": target})
    if not out and first_ref:
        out.append({"type": "section", "target": first_ref})
    return out[:3]


def _response(lang, answer, citations, refused, actions=None) -> dict:
    return {
        "answer": answer,
        "language": lang,
        "citations": citations,
        "refused": refused,
        "suggested_actions": actions or [],
        "disclaimer": disclaimer(lang),
    }


def _refuse(lang: str, reason: str) -> dict:
    return _response(lang, REFUSALS[reason][lang], [], True)


def answer(db, messages: list[dict], llm: LlmClient, lang_hint: str | None = None) -> dict:
    question = messages[-1]["content"].strip()
    lang = lang_hint or detect_language(question)

    if UNSAFE.search(question):
        return _refuse(lang, "unsafe")
    if OUT_OF_SCOPE.search(question):
        return _refuse(lang, "out_of_scope")

    english = None
    if lang != "en" and settings.llm_provider != "mock":
        english = llm.rewrite_query(question, lang)
    english = english or normalise_query(question)

    chosen: list = []
    seen: set[str] = set()
    # 1) sections the user named explicitly ("PPC 302", "dafa 497")
    for law, num in _refs_in(question):
        for lw in ([law] if law else ["PPC", "CrPC"]):
            row = get_section(db, lw, num)
            if row and f"{row.law}/{row.section_number}" not in seen:
                chosen.append(row)
                seen.add(f"{row.law}/{row.section_number}")
    # 2) retrieval
    rows = all_rows(db)
    by_id = {r.id: r for r in rows}
    hits = Bm25Index([(r.id, statute_doc(r)) for r in rows]).search(english, k=5)
    for rid, score in hits:
        r = by_id[rid]
        key = f"{r.law}/{r.section_number}"
        if score >= settings.retrieval_min_score and key not in seen:
            chosen.append(r)
            seen.add(key)
    chosen = chosen[:5]
    if not chosen:
        return _refuse(lang, "no_match")

    records = [to_d01(r) for r in chosen]
    result = llm.grounded_answer(question, lang, records, messages)  # may raise LlmUnavailable

    valid = {ref(r): r for r in records}
    cited = [c for c in dict.fromkeys(result.cited) if c in valid]  # drop anything not retrieved
    if not result.can_answer or not cited or not result.answer.strip():
        return _refuse(lang, "no_match")

    citations = [{"law": valid[c]["law"], "section_number": valid[c]["section_number"], "title": valid[c]["title"]} for c in cited]
    return _response(lang, result.answer.strip(), citations, False, _actions(question, english, cited[0]))
