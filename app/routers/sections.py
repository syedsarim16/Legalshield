"""Module 3: PPC / CrPC section verification (E-14, E-15)."""
from fastapi import APIRouter, Depends, Query

from legalshield_ai import verification
from legalshield_ai.disclaimers import disclaimer

from ..db import get_db
from ..deps import require_roles
from ..errors import ApiError

router = APIRouter(prefix="/sections", tags=["M3 Section verification"])
ROLES = ("citizen", "lawyer", "ngo_monitor", "admin")


def _lang(lang: str) -> str:
    return lang if lang in ("en", "ur", "ur-Latn") else "en"


@router.get("/search")  # E-14
def search(
    q: str = Query(..., min_length=1, max_length=200),
    law: str | None = Query(None, description="PPC or CrPC"),
    limit: int = Query(10, ge=1, le=25),
    lang: str = "en",
    _user=Depends(require_roles(*ROLES)),
    db=Depends(get_db),
):
    if law is not None and verification.norm_law(law) is None:
        raise ApiError(422, "INVALID_LAW", "law must be PPC or CrPC.")
    rows = verification.search_rows(db, q, law, limit)
    return {"results": [verification.summary(r) for r in rows], "disclaimer": disclaimer(_lang(lang))}


@router.get("/{law}/{number}")  # E-15
def get_section(
    law: str,
    number: str,
    lang: str = "en",
    _user=Depends(require_roles(*ROLES)),
    db=Depends(get_db),
):
    if verification.norm_law(law) is None:
        raise ApiError(422, "INVALID_LAW", "law must be PPC or CrPC.")
    row = verification.get_section(db, law, number)
    if row is None:
        # "not covered" is an honest answer, not an error: never guess a classification
        return {"covered": False, "section": None, "disclaimer": disclaimer(_lang(lang))}
    return {"covered": True, "section": verification.to_d01(row), "disclaimer": disclaimer(_lang(lang))}
