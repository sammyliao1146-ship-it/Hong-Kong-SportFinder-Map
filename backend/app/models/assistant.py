from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000, pattern=r"\S")
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)


class ChatResponse(BaseModel):
    answer: str
    model: str
