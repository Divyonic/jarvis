import re
from datetime import datetime, timedelta
import dateparser
from config import PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW


# Keywords that indicate priority
HIGH_KEYWORDS = {"urgent", "asap", "important", "critical", "immediately", "right away"}
LOW_KEYWORDS = {"whenever", "someday", "eventually", "low priority", "no rush", "later"}

# Recurring patterns
RECURRING_PATTERNS = {
    r"\bevery\s+day\b": "daily",
    r"\bdaily\b": "daily",
    r"\bevery\s+week\b": "weekly",
    r"\bweekly\b": "weekly",
    r"\bevery\s+month\b": "monthly",
    r"\bmonthly\b": "monthly",
    r"\bevery\s+monday\b": "weekly:monday",
    r"\bevery\s+tuesday\b": "weekly:tuesday",
    r"\bevery\s+wednesday\b": "weekly:wednesday",
    r"\bevery\s+thursday\b": "weekly:thursday",
    r"\bevery\s+friday\b": "weekly:friday",
    r"\bevery\s+saturday\b": "weekly:saturday",
    r"\bevery\s+sunday\b": "weekly:sunday",
    r"\bevery\s+morning\b": "daily:09:00",
    r"\bevery\s+evening\b": "daily:18:00",
}

# Phrases to strip from the task title
STRIP_PHRASES = [
    r"\bremind\s+me\s+to\b",
    r"\bremember\s+to\b",
    r"\bdon'?t\s+forget\s+to\b",
    r"\bi\s+need\s+to\b",
    r"\bi\s+have\s+to\b",
    r"\bi\s+should\b",
    r"\bplease\b",
]


def parse_input(text):
    """
    Parse natural language input into a structured task.

    Returns dict with: title, due_at, priority, recurring
    """
    original = text.strip()
    working = original.lower()

    # Detect priority
    priority = PRIORITY_MEDIUM
    if any(kw in working for kw in HIGH_KEYWORDS):
        priority = PRIORITY_HIGH
    elif any(kw in working for kw in LOW_KEYWORDS):
        priority = PRIORITY_LOW

    # Detect recurring
    recurring = None
    for pattern, value in RECURRING_PATTERNS.items():
        if re.search(pattern, working):
            recurring = value
            original = re.sub(pattern, "", original, flags=re.IGNORECASE).strip()
            break

    # Parse date/time using dateparser
    due_at = None
    # Try to find time expressions in the text
    time_expressions = _extract_time_expression(working)
    if time_expressions:
        # Normalize phrases dateparser doesn't handle well
        normalized = _normalize_time_phrase(time_expressions)
        parsed_date = dateparser.parse(
            normalized,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.now(),
            },
        )
        if parsed_date:
            # If the parsed date is in the past, push to tomorrow
            if parsed_date < datetime.now():
                parsed_date += timedelta(days=1)
            due_at = parsed_date
            # Remove the time expression from the title
            original = _remove_time_from_title(original, time_expressions)

    # Clean up the title
    title = original
    for phrase in STRIP_PHRASES:
        title = re.sub(phrase, "", title, flags=re.IGNORECASE)

    # Remove priority keywords from title
    for kw in HIGH_KEYWORDS | LOW_KEYWORDS:
        title = re.sub(r"\b" + re.escape(kw) + r"\b", "", title, flags=re.IGNORECASE)

    # Clean whitespace and punctuation
    title = re.sub(r"\s+", " ", title).strip()
    title = title.strip(" ,-.")
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    return {
        "title": title,
        "due_at": due_at.isoformat() if due_at else None,
        "priority": priority,
        "recurring": recurring,
    }


def _normalize_time_phrase(phrase):
    """Convert phrases like 'tomorrow morning' into forms dateparser understands."""
    replacements = {
        "tomorrow morning": "tomorrow at 9am",
        "tomorrow afternoon": "tomorrow at 14:00",
        "tomorrow evening": "tomorrow at 18:00",
        "tomorrow night": "tomorrow at 21:00",
        "today morning": "today at 9am",
        "today afternoon": "today at 14:00",
        "today evening": "today at 18:00",
        "tonight": "today at 21:00",
    }
    lower = phrase.lower().strip()
    return replacements.get(lower, phrase)


def _extract_time_expression(text):
    """Extract time-related expressions from text."""
    time_patterns = [
        # "at 3pm", "at 15:00"
        r"at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
        # "by 5pm", "by tomorrow"
        r"by\s+(?:tomorrow|tonight|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
        # "tomorrow at 3pm"
        r"tomorrow\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
        # "today at 3pm"
        r"today\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
        # "tonight"
        r"\btonight\b",
        # "tomorrow morning/evening/afternoon"
        r"tomorrow\s+(?:morning|afternoon|evening|night)",
        # "tomorrow"
        r"\btomorrow\b",
        # "next monday", "next week"
        r"next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month)",
        # "in 30 minutes", "in 2 hours"
        r"in\s+\d+\s+(?:minutes?|hours?|days?|weeks?)",
        # Specific dates: "april 15", "march 3rd"
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?",
        # "on monday"
        r"on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        # Bare time: "3pm", "5:30am" (at end of string or before comma)
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    ]

    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _remove_time_from_title(title, time_expr):
    """Remove the time expression from the task title."""
    # Escape the time expression for regex use
    escaped = re.escape(time_expr)
    result = re.sub(escaped, "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", result).strip()
