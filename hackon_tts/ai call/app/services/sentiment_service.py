import re

def analyze_sentiment(text: str) -> str:
    """Simple rule-based sentiment detection for speed (no extra API call)."""
    text_lower = text.lower()

    negative_words = [
        "angry", "frustrated", "terrible", "awful", "worst", "hate", "useless",
        "disappointed", "bad", "horrible", "annoying", "waste", "never", "cancel",
        "refund", "complaint", "problem", "issue", "broken", "not working", "failed"
    ]
    positive_words = [
        "great", "excellent", "love", "amazing", "good", "happy", "satisfied",
        "perfect", "wonderful", "thanks", "thank you", "helpful", "awesome",
        "fantastic", "impressive", "interested", "yes", "sure", "absolutely"
    ]

    neg_count = sum(1 for w in negative_words if w in text_lower)
    pos_count = sum(1 for w in positive_words if w in text_lower)

    if neg_count > pos_count:
        return "Negative"
    elif pos_count > neg_count:
        return "Positive"
    return "Neutral"


def _clean_spoken_email(text: str) -> str:
    """Normalize spoken email to machine-readable form."""
    t = text.lower()
    t = re.sub(r"\bat\s+the\s+rate\b", "@", t)
    t = re.sub(r"@\s*the\s*rate\s*", "@", t)
    t = re.sub(r"@therate", "@", t)
    t = re.sub(r"\bat\b", "@", t)
    t = re.sub(r"\bdot\b", ".", t)
    t = re.sub(r"\bunderscore\b", "_", t)
    t = re.sub(r"\bhyphen\b|\bdash\b", "-", t)
    return t


def extract_email(text: str) -> str | None:
    """Extract email address from transcribed speech."""
    EMAIL_RE = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"

    # Clean spoken patterns first, then find email without stripping all spaces
    cleaned = _clean_spoken_email(text)

    # Remove spaces only around @ and . to avoid gluing surrounding words
    cleaned = re.sub(r"\s*@\s*", "@", cleaned)
    cleaned = re.sub(r"\s*\.\s*", ".", cleaned)

    # Find all email candidates and return the longest (most complete) one
    matches = re.findall(EMAIL_RE, cleaned)
    if matches:
        return max(matches, key=len)

    matches2 = re.findall(EMAIL_RE, text)
    if matches2:
        return max(matches2, key=len)

    return None


def extract_meeting_time(text: str) -> str | None:
    """Extract meeting day/time from speech."""
    DAYS = r"(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    MONTHS = r"(january|february|march|april|may|june|july|august|september|october|november|december)"
    TIME = r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))"

    patterns = [
        # "July 3 at 5PM" / "July 3, 5PM"
        rf"{MONTHS}\s+(\d{{1,2}})(?:st|nd|rd|th)?[,\s]+(?:at\s+)?{TIME}",
        # "3rd July at 5PM"
        rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+{MONTHS}[,\s]+(?:at\s+)?{TIME}",
        # "tomorrow at 3pm" / "Monday 2 PM"
        rf"{DAYS}[\s,]*(?:at\s+)?{TIME}",
        # time only with day: "5PM on Monday"
        rf"{TIME}\s+(?:on\s+)?{DAYS}",
        # just a day name (no time)
        rf"{DAYS}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parts = [g.strip() for g in match.groups() if g]
            return " ".join(parts)
    return None


def extract_name(text: str) -> str | None:
    """Extract name from phrases like 'my name is John' or 'I am Sarah'."""
    patterns = [
        r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)",
        r"i(?:'m| am) ([A-Z][a-z]+(?: [A-Z][a-z]+)?)",
        r"this is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)",
        r"call me ([A-Z][a-z]+(?: [A-Z][a-z]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
