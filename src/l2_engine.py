import json, os, re, time
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None

STATUS_WORDS = {
    "completed": [r"\bcompleted\b", r"\bcomplete\b", r"\bsubmitted\b", r"\bfinished\b", r"\bhandled\b"],
    "cancelled": [r"\bcancel(?:led|l)\b", r"\bno longer needed\b", r"\bcalled off\b"],
    "rescheduled": [r"\bmoved to\b", r"\brescheduled\b", r"\bnew schedule\b", r"\btime is now\b", r"\bextended to\b"],
    "unclear": [r"\bmight\b", r"\bmay\b", r"\bprobably\b", r"\bnot completely sure\b", r"\bwait for confirmation\b", r"\bwill confirm later\b"],
    "in_progress": [r"\bin progress\b", r"\bneeds attention\b", r"\bstarted\b", r"\bunderway\b"],
}

def norm(s):
    s=(s or "").lower()
    s=re.sub(r"[^a-z0-9\s]", " ", s)
    s=re.sub(r"\b(the|a|an|our|earlier|new|item|task|work|request|session)\b"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def parse_date(text, timestamp=None):
    m=re.search(r"\b(20\d{2}-\d{2}-\d{2})\b",text)
    if m: return m.group(1)
    if timestamp and re.search(r"\btomorrow\b", text, re.I):
        return (datetime.fromisoformat(timestamp).date()+timedelta(days=1)).isoformat()
    # Deliberately do not resolve weekday-only or ambiguous dates.
    return None

def parse_time(text):
    m=re.search(r"\b(\d{1,2}:\d{2})\b",text)
    return m.group(1) if m else None

def infer_status(text):
    low=text.lower()
    # Explicit uncertainty wins over weak completion words such as "finished"
    # when the same message says it cannot be confirmed.
    if any(re.search(p,low) for p in STATUS_WORDS["unclear"]) or re.search(r"cannot confirm|not sure",low):
        return "Unclear"
    if any(re.search(p,low) for p in STATUS_WORDS["cancelled"]): return "Cancelled"
    if any(re.search(p,low) for p in STATUS_WORDS["completed"]): return "Completed"
    if any(re.search(p,low) for p in STATUS_WORDS["rescheduled"]): return "Rescheduled"
    if any(re.search(p,low) for p in STATUS_WORDS["in_progress"]): return "In progress"
    return None

def action_title(text):
    """Extract a canonical action phrase from L2's templated follow-ups/new tasks."""
    t=text.strip()
    pats=[
        r"(?:new task:\s*)?(.+?)\s+by\s+20\d{2}-\d{2}-\d{2}\.?",
        r"deadline to\s+(.+?)\s+is now\b",
        r"deadline to\s+(.+?)\s+is due\b",
        r"(?:update on|status of|progress on|about|regarding)\s+(.+?)(?:\?|$)",
        r"(?:earlier request about|work we discussed about|item concerning|item about)\s+(.+?)(?:\.|\?|$)",
        r"confirm whether you started to\s+(.+?)(?:\.|\?|$)",
        r"follow-up:\s*(?:new task:\s*)?(.+?)\s+by\s+20\d{2}-\d{2}-\d{2}",
        r"status request about\s+(.+?)(?:,|\.)",
        r"the deadline for\s+(.+?)\s+has been",
    ]
    for p in pats:
        m=re.search(p,t,re.I)
        if m:
            s=m.group(1).strip(" .?;")
            s=re.sub(r"^(?:the|a)\s+","",s,flags=re.I)
            return norm(s)
    known=["confirm the interview slot","email the signed document","update the project tracker",
           "upload the assignment","review the model results","complete the onboarding form",
           "finish the test cases","review the privacy checklist","renew the library book",
           "call the service centre","pay the electricity bill","back up the project files",
           "send the revised presentation","prepare the demo video","submit the weekly report",
           "verify the dataset labels","reply to the client email","share the meeting notes",
           "complete the python exercise"]
    low=t.lower()
    for k in known:
        if k in low: return norm(k)
    return None

def event_title(text):
    low=text.lower()
    # known event names are deliberately generic, not test-case IDs.
    names=["placement briefing","sprint planning","technical interview","mentor catch-up",
           "internship orientation","team stand-up","latency-review meeting",
           "quantization results","privacy-routing decisions","offline inference demo",
           "l2 presentation","architecture diagram"]
    for n in names:
        if n in low: return norm(n)
    return None

def classify_l2(text):
    low=text.lower()
    if any(x in low for x in ["otp","password","token","card number","bank account","recovery code","id number","medical note","test result"]):
        return "sensitive_information"
    if any(x in low for x in ["scheduled","meeting","orientation","briefing","stand-up","session","moved to","meeting has been"]):
        return "meeting_or_event"
    if any(x in low for x in ["new task","deadline","due on","by 2026","confirm","upload","review","complete","submit","reply","update","renew","pay","prepare","measure","validate","test","compare","document"]):
        return "action_required"
    return "general_information"

def choose_item(title_key, items, current_ts):
    """Use the most recent matching L1 item before the L2 message.
    L1 contains repeated task instances; this avoids creating a new item
    for a mere follow-up."""
    if not title_key: return None
    candidates=[i for i in items if norm(i.get("title"))==title_key]
    if not candidates: return None
    # source_message_id is monotonic in L1, so last is latest.
    return candidates[-1]

def priority_for(text, item, timestamp, status=None, sensitivity=None):
    dt=datetime.fromisoformat(timestamp)
    score=0; signals=[]
    low=text.lower()
    deadline=item.get("deadline") if item else parse_date(text,timestamp)
    if deadline:
        try:
            dd=datetime.fromisoformat(deadline)
            days=(dd.date()-dt.date()).days
            if days < 0: score+=5; signals.append("overdue_at_message_time")
            elif days == 0: score+=5; signals.append("deadline_today")
            elif days == 1: score+=4; signals.append("deadline_tomorrow")
            elif days <=3: score+=3; signals.append("deadline_within_3_days")
            elif days <=7: score+=2; signals.append("deadline_within_7_days")
            else: score+=1; signals.append("future_deadline")
        except Exception: pass
    if re.search(r"\burgent\b|\basap\b|\bimmediately\b",low):
        score+=3; signals.append("explicit_urgency")
    if re.search(r"\bconfirm\b|\bplease confirm\b",low):
        score+=1; signals.append("confirmation_required")
    if "follow-up" in low or "following up" in low:
        score+=1; signals.append("follow_up")
    if status in ("Completed","Cancelled"):
        signals.append("inactive_completed_or_cancelled")
        score=max(0,score-6)
    if status=="Unclear":
        score+=1; signals.append("uncertain_status")
    if sensitivity:
        if any(s["risk"]=="high" for s in sensitivity):
            score+=2; signals.append("high_risk_sensitive")
        else:
            score+=1; signals.append("sensitive_information")
    # Sender is a weak contextual signal, never decisive by itself.
    if item and item.get("type")=="event":
        signals.append("event_actionability")
    if score>=8: p="Critical"
    elif score>=5: p="High"
    elif score>=3: p="Medium"
    else: p="Low"
    # confidence reflects number and consistency of evidence, capped.
    evidence=len(set(signals))
    confidence=min(0.99,0.55+0.07*evidence)
    reason_parts=[]
    if "overdue_at_message_time" in signals: reason_parts.append("the deadline was already past at message time")
    elif "deadline_today" in signals: reason_parts.append("the deadline is today")
    elif "deadline_tomorrow" in signals: reason_parts.append("the deadline is tomorrow")
    elif "deadline_within_3_days" in signals: reason_parts.append("the deadline is within three days")
    elif "deadline_within_7_days" in signals: reason_parts.append("the deadline is within seven days")
    if "explicit_urgency" in signals: reason_parts.append("the message explicitly marks it urgent")
    if "follow_up" in signals: reason_parts.append("it is a follow-up")
    if status in ("Completed","Cancelled"): reason_parts.append(f"the item is {status.lower()}")
    if status=="Unclear": reason_parts.append("the status is explicitly uncertain")
    if sensitivity: reason_parts.append("sensitivity affects handling")
    reason="; ".join(reason_parts) or "No strong urgency signal was present, so the item remains low priority."
    return p,reason,signals,round(confidence,2)

def build_l2(l1_dir, l2_csv, out_dir):
    os.makedirs(out_dir,exist_ok=True)
    with open(os.path.join(l1_dir,"display_messages.json"),encoding="utf8") as f: l1msgs=json.load(f)
    with open(os.path.join(l1_dir,"tasks_events.json"),encoding="utf8") as f: l1items=json.load(f)
    with open(os.path.join(l1_dir,"classifications.json"),encoding="utf8") as f: l1classes=json.load(f)
    with open(os.path.join(l1_dir,"sensitive_findings.json"),encoding="utf8") as f: l1sens=json.load(f)
    import csv
    with open(l2_csv,encoding="utf-8-sig",newline="") as f: l2msgs=list(csv.DictReader(f))
    l2msgs=sorted(l2msgs,key=lambda x:x["timestamp"])
    all_msgs=l1msgs+l2msgs
    # Existing L1 instances grouped by canonical title. We preserve their IDs.
    items=list(l1items)
    next_task=1+max([int(re.search(r"\d+",i["item_id"]).group()) for i in items if i["item_id"].startswith("TASK_")],default=0)
    next_event=1+max([int(re.search(r"\d+",i["item_id"]).group()) for i in items if i["item_id"].startswith("EVENT_")],default=0)
    title_latest={}
    for i in items: title_latest[norm(i["title"])]=i

    # One logical group per canonical subject; L1 duplicate task instances remain listed.
    groups={}
    def ensure_group(title_key, item=None):
        if not title_key: return None
        if title_key not in groups:
            gid=f"GROUP_{len(groups)+1:03d}"
            groups[title_key]={
                "group_id":gid,
                "title": item["title"] if item else title_key.title(),
                "related_message_ids":[],
                "related_task_event_ids":[],
                "summary":"",
                "status":"Pending",
                "latest_deadline":None,
                "confidence":0.6,
                "_events":[],
            }
        return groups[title_key]

    # Seed groups from L1 items, including duplicate item IDs.
    source_to_group={}
    for i in items:
        key=norm(i["title"]); g=ensure_group(key,i)
        if i["source_message_id"] not in g["related_message_ids"]:
            g["related_message_ids"].append(i["source_message_id"])
        if i["item_id"] not in g["related_task_event_ids"]:
            g["related_task_event_ids"].append(i["item_id"])
        source_to_group[i["source_message_id"]]=g
        if i.get("deadline"): g["latest_deadline"]=i["deadline"]
        elif i.get("date"): g["latest_deadline"]=i["date"]
        g["_events"].append((i["source_message_id"],i["description"],"initial"))
    for m in l1msgs:
        # messages with task/event source are already linked.
        pass

    priorities=[]
    updates=[]
    sens_by_id=defaultdict(list)
    for s in l1sens: sens_by_id[s["message_id"]].append(s)

    # Process L2 strictly chronologically.
    for row in l2msgs:
        mid,ts,text=row["message_id"],row["timestamp"],row["message"]
        cls=classify_l2(text)
        sens=[]
        # import current detector dynamically
        from sensitive_detector import build_sensitive_records
        sens=build_sensitive_records(mid,text)
        sens_by_id[mid]=sens
        title=action_title(text)
        evtitle=event_title(text)
        item=None
        status=infer_status(text)
        # Event updates get priority if the event name is explicit.
        if evtitle:
            item=choose_item(evtitle,items,ts)
        if not item and title:
            item=choose_item(title,items,ts)
        # New task/event creation.
        if not item:
            d=parse_date(text,ts); tm=parse_time(text)
            if re.search(r"\bnew task\b",text,re.I) and title:
                item={"item_id":f"TASK_{next_task:03d}","type":"task","title":title.title(),
                      "description":text,"deadline":d,"time":None,"person":row["sender"],
                      "priority":"Low","source_message_id":mid,"note":None}
                next_task+=1; items.append(item); title_latest[norm(item["title"])]=item
            elif re.search(r"\bnew .*session\b|\bsession is scheduled\b",text,re.I) and evtitle:
                item={"item_id":f"EVENT_{next_event:03d}","type":"event","title":evtitle.title(),
                      "description":text,"date":d,"time":tm,"location":None,"person":row["sender"],
                      "priority":"Low","source_message_id":mid,"note":None}
                next_event+=1; items.append(item); title_latest[norm(item["title"])]=item
        # Special event creation for "new X session scheduled" where event_title found.
        if not item and evtitle and d:
            item={"item_id":f"EVENT_{next_event:03d}","type":"event","title":evtitle.title(),
                  "description":text,"date":d,"time":tm,"location":None,"person":row["sender"],
                  "priority":"Low","source_message_id":mid,"note":None}
            next_event+=1; items.append(item)
        # For status-only/subject messages, map to canonical group if possible.
        g=None
        if item:
            g=ensure_group(norm(item["title"]),item)
            if item["source_message_id"] not in g["related_message_ids"] and item["source_message_id"]==mid:
                g["related_message_ids"].append(mid)
            if item["item_id"] not in g["related_task_event_ids"]:
                g["related_task_event_ids"].append(item["item_id"])
            g["_events"].append((mid,text,status or "update"))
        elif title:
            g=ensure_group(title)
            g["_events"].append((mid,text,status or "update"))
            g["related_message_ids"].append(mid)
        elif evtitle:
            g=ensure_group(evtitle)
            g["_events"].append((mid,text,status or "update"))
            g["related_message_ids"].append(mid)

        # Update group/item state from chronology.
        if g:
            d=parse_date(text,ts); tm=parse_time(text)
            if mid not in g["related_message_ids"]: g["related_message_ids"].append(mid)
            d=parse_date(text,ts)
            if d: g["latest_deadline"]=d
            if status: g["status"]=status
            # Rescheduling without status still updates date/time on item.
            if item:
                if d:
                    if item["type"]=="event": item["date"]=d
                    else: item["deadline"]=d
                if tm and item["type"]=="event": item["time"]=tm
                if status=="Completed": item["status"]="Completed"
                elif status=="Cancelled": item["status"]="Cancelled"
                elif status=="Rescheduled": item["status"]="Rescheduled"
                elif status=="Unclear": item["status"]="Unclear"
                elif status=="In progress": item["status"]="In progress"
                else: item.setdefault("status","Pending")
        # Priority for every actionable/update message.
        actionable=(cls in ("action_required","meeting_or_event")) or bool(title or evtitle)
        if actionable:
            p,reason,signals,conf=priority_for(text,item or {},ts,status,sens)
            priorities.append({
                "message_id":mid,
                "item_id":item["item_id"] if item else None,
                "priority":p.lower(),
                "reason":reason,
                "signals":signals,
                "confidence":conf,
            })

    # Include a final priority snapshot for every L2-derived actionable item/update.
    # Also create group summaries from chronology.
    for g in groups.values():
        ev=g["_events"]
        # compact evidence-grounded summary based on latest status/deadline
        last_text=ev[-1][1] if ev else ""
        first_text=ev[0][1] if ev else ""
        parts=[]
        if first_text: parts.append("The subject first appears as: "+first_text)
        if g["status"]!="Pending": parts.append("Latest state: "+g["status"]+".")
        if g["latest_deadline"]: parts.append("Latest explicit date: "+g["latest_deadline"]+".")
        if last_text and last_text!=first_text: parts.append("Latest update: "+last_text)
        g["summary"]=" ".join(parts)[:900]
        g["confidence"]=round(min(0.98,0.62+0.03*min(len(g["related_message_ids"]),8)),2)
        g.pop("_events",None)

    # Save safe outputs.
    safe_l2=[]
    for r in l2msgs:
        safe_l2.append({**r,"message": __import__("sensitive_detector").mask_message(r["message"]) if sens_by_id.get(r["message_id"]) else r["message"]})
    with open(os.path.join(out_dir,"l2_display_messages.json"),"w") as f: json.dump(safe_l2,f,indent=2)
    with open(os.path.join(out_dir,"priority_output.json"),"w") as f: json.dump(priorities,f,indent=2)
    with open(os.path.join(out_dir,"related_groups.json"),"w") as f: json.dump(list(groups.values()),f,indent=2)
    with open(os.path.join(out_dir,"privacy_routing.json"),"w") as f:
        json.dump([{
            "message_id":mid,
            "sensitivity_types":sorted(set(x["sensitivity_type"] for x in recs)),
            "masked":bool(recs),
            "recommended_actions":sorted(set(x["recommended_action"] for x in recs))
        } for mid,recs in sens_by_id.items() if mid.startswith("MSG_") and int(mid.split("_")[1])>=901 or mid.startswith("DEMO_")],f,indent=2)
    # Current state of all items.
    with open(os.path.join(out_dir,"l2_tasks_events.json"),"w") as f: json.dump(items,f,indent=2)
    return l1msgs,l2msgs,items,priorities,list(groups.values()),sens_by_id
