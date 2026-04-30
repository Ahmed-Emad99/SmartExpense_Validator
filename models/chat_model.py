from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class ChatMessage(BaseModel):
    """Represents a single message in the chat history."""
    role: str  # "user" or "assistant"
    content: str


class TravelSession(BaseModel):
    """
    Holds the user's travel window and the computed upload deadline.
    All invoice-level checks reference these dates.
    """
    travel_start: date
    travel_end: date
    upload_deadline: date  # travel_end + 30 days

    @property
    def is_within_upload_window(self) -> bool:
        """Returns True if today is still within the allowed upload period."""
        return date.today() <= self.upload_deadline