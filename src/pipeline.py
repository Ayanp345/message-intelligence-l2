"""
pipeline.py
-----------
Entry point. Reads the dataset in chronological order (the CSV is already
sorted by timestamp, we do not re-sort in case of ties -> preserves file
order) and runs, for every message:

  1. classifier.classify()          -> category + confidence + reason
  2. extractor.extract()            -> task/event record, or None
  3. sensitive_detector.build_sensitive_records() -> 0..n sensitive findings

All sensitive VALUES are masked before anything is written to disk, so the
generated JSON files (which may end up in screenshots/the repo) never
contain a real secret span, per the assignment's hard requirement.

Usage:
    python3 pipeline.py <messages.csv> <output_dir>
"""

import csv
import json
import sys
import os

from classifier import classify
from extractor import extract
from sensitive_detector import build_sensitive_records, mask_message


def run(messages_csv: str, mandatory_ids_csv: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    with open(messages_csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    mandatory_ids = []
    if mandatory_ids_csv and os.path.exists(mandatory_ids_csv):
        with open(mandatory_ids_csv, encoding="utf-8-sig", newline="") as f:
            mandatory_ids = [r["message_id"] for r in csv.DictReader(f)]

    classifications = []
    tasks_events = []
    sensitive_findings = []
    display_messages = []  # safe-for-UI copy: sensitive rows are pre-masked
    counter = {"task": 0, "event": 0}

    category_counts = {}

    for row in rows:
        mid = row["message_id"]
        ts = row["timestamp"]
        sender = row["sender"]
        text = row["message"]

        # 1. classify
        c = classify(mid, sender, text)
        classifications.append(c)
        category_counts[c["category"]] = category_counts.get(c["category"], 0) + 1

        # 2. extract task/event
        item = extract(mid, ts, text, counter)
        if item:
            tasks_events.append(item)

        # 3. sensitive detection (independent of category)
        recs = build_sensitive_records(mid, text)
        sensitive_findings.extend(recs)

        # display-safe copy for any UI / demo: never keep raw sensitive text
        display_messages.append(
            {
                "message_id": mid,
                "timestamp": ts,
                "sender": sender,
                "text": mask_message(text) if recs else text,
                "category": c["category"],
                "is_sensitive": bool(recs),
            }
        )

    with open(os.path.join(output_dir, "classifications.json"), "w") as f:
        json.dump(classifications, f, indent=2)

    with open(os.path.join(output_dir, "tasks_events.json"), "w") as f:
        json.dump(tasks_events, f, indent=2)

    with open(os.path.join(output_dir, "sensitive_findings.json"), "w") as f:
        json.dump(sensitive_findings, f, indent=2)

    with open(os.path.join(output_dir, "display_messages.json"), "w") as f:
        json.dump(display_messages, f, indent=2)

    # mandatory-id mini report, used directly in the video walkthrough
    by_id = {c["message_id"]: c for c in classifications}
    tasks_by_source = {}
    for item in tasks_events:
        tasks_by_source.setdefault(item["source_message_id"], []).append(item)
    sens_by_id = {}
    for s in sensitive_findings:
        sens_by_id.setdefault(s["message_id"], []).append(s)

    mandatory_report = []
    for mid in mandatory_ids:
        mandatory_report.append(
            {
                "message_id": mid,
                "classification": by_id.get(mid),
                "extracted_items": tasks_by_source.get(mid, []),
                "sensitive_findings": sens_by_id.get(mid, []),
            }
        )
    with open(os.path.join(output_dir, "mandatory_ids_report.json"), "w") as f:
        json.dump(mandatory_report, f, indent=2)

    summary = {
        "total_messages": len(rows),
        "category_counts": category_counts,
        "total_tasks_extracted": sum(1 for t in tasks_events if t["type"] == "task"),
        "total_events_extracted": sum(1 for t in tasks_events if t["type"] == "event"),
        "total_sensitive_findings": len(sensitive_findings),
    }
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    messages_csv = sys.argv[1] if len(sys.argv) > 1 else "messages.csv"
    mandatory_csv = sys.argv[2] if len(sys.argv) > 2 else "mandatory_demo_ids.csv"
    out_dir = sys.argv[3] if len(sys.argv) > 3 else "../output"
    run(messages_csv, mandatory_csv, out_dir)
