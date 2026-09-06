import re

from sensitive_detector import detect_sensitive
from extractor import strip_prefix, EVENT_PATTERNS, TASK_PATTERNS

PROMO_RE = re.compile(r"Use code SAVE\w*|You may like our new student plan", re.I)
PERSONAL_MARKER_RE = re.compile(
    r"^(For my profile,|Personal note:|Remember that|Just so you know,)", re.I
)


def classify(message_id: str, sender: str, text: str):
    core = strip_prefix(text)

    # 1. Promotional -----------------------------------------------------
    if PROMO_RE.search(text):
        return {
            "message_id": message_id,
            "category": "promotional",
            "confidence": 0.97,
            "reason": "Message contains marketing language and/or a discount code ('Use code ...') typical of a promotional blast.",
        }

    # 2. Sensitive information -------------------------------------------
    sensitive_hits = detect_sensitive(message_id, text)
    if sensitive_hits:
        types = ", ".join(sorted({h.sensitivity_type for h in sensitive_hits}))
        return {
            "message_id": message_id,
            "category": "sensitive_information",
            "confidence": 0.95,
            "reason": f"Message contains sensitive data matching pattern(s): {types}.",
        }

    # 3. Meeting or event --------------------------------------------------
    for pat in EVENT_PATTERNS:
        if pat.search(core):
            return {
                "message_id": message_id,
                "category": "meeting_or_event",
                "confidence": 0.93,
                "reason": "Message matches a known scheduling template (calendar update / reminder / invite / 'scheduled for').",
            }

    # 4. Action required ---------------------------------------------------
    for pat, _ in TASK_PATTERNS:
        if pat.search(core):
            return {
                "message_id": message_id,
                "category": "action_required",
                "confidence": 0.9,
                "reason": "Message asks the recipient to do something (request, reminder, or deadline phrasing).",
            }

    # 5. Personal information ----------------------------------------------
    if PERSONAL_MARKER_RE.search(core):
        return {
            "message_id": message_id,
            "category": "personal_information",
            "confidence": 0.88,
            "reason": "Message is a self-reported personal preference/profile statement (not a secret/credential).",
        }

    # 6. General information (fallback) ------------------------------------
    return {
        "message_id": message_id,
        "category": "general_information",
        "confidence": 0.7,
        "reason": "Message is a plain factual/status statement with no request, schedule, secret, or personal-preference marker detected.",
    }
