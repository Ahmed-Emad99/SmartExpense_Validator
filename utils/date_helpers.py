from datetime import date, timedelta
from typing import Optional, Tuple
from models.chat_model import TravelSession

UPLOAD_WINDOW_DAYS = 30  # company policy: 30 days after return date


def build_travel_session(travel_start: date, travel_end: date) -> Tuple[Optional[TravelSession], Optional[str]]:
    """
    Validates the provided travel dates and builds a TravelSession.

    Returns:
        (TravelSession, None)        on success
        (None, error_message_str)    on validation failure
    """
    today = date.today()

    if travel_end < travel_start:
        return None, "Return date cannot be before the departure date."

    if travel_start > today:
        # Future trip — still valid, just means no invoices can be date-checked yet
        pass

    upload_deadline = travel_end + timedelta(days=UPLOAD_WINDOW_DAYS)

    if today > upload_deadline:
        return None, (
            f"Your receipt upload deadline was {upload_deadline.strftime('%B %d, %Y')} "
            f"(30 days after your return). Uploads are no longer accepted for this trip."
        )

    return TravelSession(
        travel_start=travel_start,
        travel_end=travel_end,
        upload_deadline=upload_deadline,
    ), None


def format_deadline_warning(session: TravelSession) -> Optional[str]:
    """
    Returns a warning string if fewer than 7 days remain before the deadline,
    or None if there is still plenty of time.
    """
    days_left = (session.upload_deadline - date.today()).days
    if days_left <= 0:
        return "⛔ Your upload window has closed."
    if days_left <= 7:
        return f"⚠️ Only {days_left} day(s) left to submit your receipts (deadline: {session.upload_deadline})."
    return None