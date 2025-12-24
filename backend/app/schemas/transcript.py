"""Pydantic schemas for transcript-related data."""

from typing import Optional
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """A segment of the transcript with timing."""
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    """Transcript data."""
    content: str
    segments: list[TranscriptSegment] = []
    source: str  # youtube_manual, youtube_auto, whisper
    language: str
    word_count: int


class LanguageInfo(BaseModel):
    """Available transcript language."""
    code: str
    name: str
    is_generated: bool


class TranscriptAvailability(BaseModel):
    """Information about transcript availability for a video."""
    has_manual: bool
    has_auto: bool
    available_languages: list[LanguageInfo]
    can_use_whisper: bool
