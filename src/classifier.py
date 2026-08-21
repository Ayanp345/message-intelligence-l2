"""
classifier.py
--------------
Classifies a message into one of six categories:

  action_required, meeting_or_event, personal_information,
  general_information, promotional, sensitive_information

Approach: ordered rule cascade (a decision list), not a statistical
model. Each rule is a plain regex/keyword check with a human-readable
reason string attached, and every message gets a confidence score based
on HOW the rule matched (exact known template vs. weaker keyword-only
match). This is deliberate: the brief asks candidates to "understand and
explain everything submitted", and a small ordered rule list is something
you can walk through, line by line, on camera.

Rule order matters (first match wins), because some content overlaps,
e.g. a message can both request a reply (action) AND be inside a
"For today:" wrapper. Order, most-specific-first:

  1. promotional              (marketing code / offer language)
  2. sensitive_information    (credentials, financial data, health data,
                                address/phone -> reuses sensitive_detector)
  3. meeting_or_event         (has a recognised event template)
  4. action_required          (has a recognised task template)
  5. personal_information     (soft profile/preference statement)
  6. general_information      (fallback: a plain informational statement)
"""

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
