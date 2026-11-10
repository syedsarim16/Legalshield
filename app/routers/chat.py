"""Module 2: AI legal chatbot (E-13)."""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from legalshield_ai import chat as chat_engine
from legalshield_ai.llm import LlmClient, get_llm

from ..config import settings
from ..db import get_db
from ..deps import require_roles
from ..errors import ApiError
from ..models import User
from ..ratelimit import RateLimiter

router = APIRouter(prefix="/chat", tags=["M2 Chatbot"])
chat_limiter = RateLimiter(settings.chat_rate_limit_per_hour, 3600, "CHAT_RATE_LIMITED", "Too many questions this hour. Please try again later.")


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    messages: list[Turn] = Field(min_length=1, max_length=50)
    language: Literal["en", "ur", "ur-Latn"] | None = None


@router.post("/messages")  # E-13
def chat_messages(
    body: ChatRequest,
    user: User = Depends(require_roles("citizen")),
    db=Depends(get_db),
    llm: LlmClient = Depends(get_llm),
):
    if body.messages[-1].role != "user":
        raise ApiError(422, "VALIDATION_ERROR", "The last message must be from the user.")
    chat_limiter.check(user.id)
    history = [m.model_dump() for m in body.messages[-10:]]
    return chat_engine.answer(db, history, llm, lang_hint=body.language)
