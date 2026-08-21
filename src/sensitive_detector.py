"""
L2 privacy-aware sensitive detector.
All raw sensitive values exist only in process memory and are never serialized.
"""
import re
from dataclasses import dataclass
from typing import List

@dataclass
class SensitiveMatch:
    sensitivity_type: str
    risk: str
    recommended_action: str
    raw_value: str
    reason: str

RULES = [
    ("password", re.compile(r"\b(?:password|temporary password)\s+(?:is\s+)?([^\s.]+)", re.I),
     "high","do_not_store","Message contains an account password."),
    ("one_time_password", re.compile(r"\bOTP\b(?:\s+is)?\s+([\w\-]+)", re.I),
     "high","do_not_store","Message contains a one-time authentication code."),
    ("bank_card_number", re.compile(r"\bcard number(?:\s+is)?\s+([\d][\d\s\-]{5,})", re.I),
     "high","do_not_store","Message contains a payment card number."),
    ("bank_account_number", re.compile(r"\bbank account(?: number)?\s+(?:is\s+)?([\d\-]+)", re.I),
     "high","do_not_store","Message contains a bank account identifier."),
    ("auth_token", re.compile(r"\baccess token(?:\s+is)?\s+([A-Za-z0-9_\-]+)", re.I),
     "high","do_not_store","Message contains an authentication/API token."),
    ("auth_token", re.compile(r"\bintegration token:\s*([A-Za-z0-9_\-]+)", re.I),
     "high","do_not_store","Message contains an integration token."),
    ("account_recovery_code", re.compile(r"\brecovery code\s+(?:is\s+)?([\w\-]+)", re.I),
     "high","do_not_store","Message contains an account recovery code."),
    ("personal_identification_number", re.compile(r"\b(?:fictional )?ID number\s+(?:is\s+)?([\w\-]+)", re.I),
     "high","do_not_store","Message contains an identification number."),
    ("private_address", re.compile(r"\b(?:home address is|deliver(?: the demo device)? to)\s+(.+?)(?:\.\s*$|$)", re.I),
     "medium","ask_for_confirmation","Message contains a private address."),
    ("private_phone_number", re.compile(r"\b(?:contact me on|call me on)\s+([\d\s\-]+)", re.I),
     "medium","ask_for_confirmation","Message contains a private phone/contact number."),
    ("health_information", re.compile(r"\b(?:test result says|medical note mentions)\s+(.+?)(?:\.\s*$|$)", re.I),
     "medium","ask_for_confirmation","Message contains personal health information."),
]

def detect_sensitive(message_id, text) -> List[SensitiveMatch]:
    out=[]
    for typ,pat,risk,action,reason in RULES:
        for m in pat.finditer(text):
            out.append(SensitiveMatch(typ,risk,action,m.group(1),reason))
    return out

def _mask_match(m):
    a,b=m.start(1),m.end(1)
    return m.string[m.start(0):m.start(1)] + "*"*min(8,b-a) + m.string[m.end(1):m.end(0)]

def mask_message(text):
    # Apply all rules to current text; raw value never leaves this function.
    masked=text
    for typ,pat,risk,action,reason in RULES:
        masked=pat.sub(_mask_match,masked)
    return masked

def build_sensitive_records(message_id,text):
    matches=detect_sensitive(message_id,text)
    masked=mask_message(text)
    return [{
        "message_id":message_id,
        "sensitivity_type":m.sensitivity_type,
        "risk":m.risk,
        "masked_text":masked,
        "recommended_action":m.recommended_action,
        "reason":m.reason,
    } for m in matches]