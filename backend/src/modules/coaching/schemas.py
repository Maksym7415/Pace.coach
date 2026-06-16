"""Pydantic request schemas for coaching endpoints."""
from pydantic import BaseModel


class InviteAthleteRequest(BaseModel):
    athlete_id: int
