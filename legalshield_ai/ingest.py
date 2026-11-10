"""F-06: validate and upsert statute records. Rejects incomplete offence records."""
from typing import Literal, Optional

from pydantic import BaseModel, ValidationError, model_validator

from app.config import settings
from app.db import select
from app.models import StatuteSection


class StatuteRecord(BaseModel):
    law: Literal["PPC", "CrPC"]
    section_number: str
    title: str
    chapter: Optional[str] = None
    text_en: str
    kind: Literal["offence", "procedure"]
    bailable: Optional[bool] = None
    cognizable: Optional[bool] = None
    compoundable: Optional[Literal["yes", "no", "with_court_permission"]] = None
    punishment: Optional[str] = None
    triable_by: Optional[str] = None
    source_ref: str = ""
    version: str = ""
    reviewed_by_advisor: bool = False

    @model_validator(mode="after")
    def _offence_needs_classification(self):
        if self.kind == "offence" and (self.bailable is None or self.cognizable is None or self.compoundable is None):
            raise ValueError("offence records need bailable, cognizable and compoundable")
        return self


def upsert_statutes(db, records: list[dict], allow_unreviewed: bool | None = None) -> dict:
    if allow_unreviewed is None:
        allow_unreviewed = settings.allow_unreviewed_statutes
    upserted, rejected = 0, []
    for i, raw in enumerate(records):
        try:
            rec = StatuteRecord(**{k: v for k, v in raw.items() if not k.startswith("_")})
        except ValidationError as e:
            rejected.append({"index": i, "law": raw.get("law"), "section_number": raw.get("section_number"), "errors": [x["msg"] for x in e.errors()]})
            continue
        if not rec.reviewed_by_advisor and not allow_unreviewed:
            rejected.append({"index": i, "law": rec.law, "section_number": rec.section_number, "errors": ["not reviewed by legal advisor"]})
            continue
        rec.section_number = rec.section_number.strip().upper()
        row = db.scalar(select(StatuteSection).where(StatuteSection.law == rec.law, StatuteSection.section_number == rec.section_number))
        if row is None:
            db.add(StatuteSection(**rec.model_dump()))
        else:
            for k, v in rec.model_dump().items():
                setattr(row, k, v)
        upserted += 1
    db.commit()
    indexed = db.query(StatuteSection).count()
    return {"upserted": upserted, "indexed": indexed, "rejected": rejected}
