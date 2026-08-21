"""
privacy_router.py
-----------------
Routes assistant queries without exposing sensitive values.
"""
import re
BLOCK_PATTERNS=[
    r"\botp\b",r"\bpassword\b",r"\baccess token\b",r"\bintegration token\b",
    r"\bcard number\b",r"\bbank account\b",r"\brecovery code\b",r"\bid number\b"
]
CONFIRM_PATTERNS=[r"\baddress\b",r"\bphone\b",r"\bmedical\b",r"\bhealth\b",r"\btest result\b"]
def route_query(query):
    low=query.lower()
    if any(re.search(p,low) for p in BLOCK_PATTERNS):
        return {"route":"blocked","reason":"The request targets high-risk credentials or financial/authentication identifiers; it must not be sent to external processing.","confirmation_required":False}
    if any(re.search(p,low) for p in CONFIRM_PATTERNS):
        return {"route":"confirmation_required","reason":"The request may expose or process personal/health information; user confirmation is required before processing.","confirmation_required":True}
    return {"route":"local","reason":"No high-risk secret or personal-data request was detected; process with the local retrieval index.","confirmation_required":False}
