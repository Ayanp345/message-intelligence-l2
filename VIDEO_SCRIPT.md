# 5-minute Loom demo script

0:00–0:30 — L1 → L2
Open the hosted application. Say: “This is the same message-intelligence pipeline from L1. In L2 I kept the original classifier, extractor and sensitive-data detector, then added chronological state updates, explainable priority, related-message grouping, semantic retrieval and privacy routing.”

0:30–1:20 — Priority
Open Priorities. Show a normal L2 deadline update and then the mandatory demo query DQ01. Explain that the interview-slot task becomes critical because the deadline is tomorrow, the message is explicitly urgent, and confirmation is required. Point to the message ID, task ID, signals and confidence.

1:20–2:10 — Related messages
Open Related Groups. Show the internship-orientation group and the interview-slot group. Explain that L1 creates task/event records, while L2 connects later messages to the same logical subject and updates state chronologically. Show that the orientation has a moved schedule followed by an uncertain update, so the latest state is not falsely marked as confirmed.

2:10–3:15 — Privacy
Open Mandatory Demo. Run DQ05. Show that DEMO_012, DEMO_013 and DEMO_024 are blocked because they contain an OTP, password and integration token.
Run DQ06. Show confirmation-required handling for personal/health information.
Open Privacy and show masked values only. Explicitly say: “The raw sensitive values are not written to these outputs.”

3:15–4:05 — Assistant
Run DQ07 and DQ08. For DQ07, show that DEMO_016 is connected to the interview-slot group and the latest status is uncertain rather than inventing completion. For DQ08, show the conservative answer: there is no evidence confirming finance-director approval.

4:05–4:35 — Benchmark
Open the benchmark report. Say the local TF-IDF retrieval is faster than the simple keyword baseline in this environment, and show the measured mean/p95 latency and index size. Do not claim a general speedup beyond this test environment.

4:35–5:00 — Challenge and takeaway
Show DQ04. Explain that conflicting deadlines are difficult because several messages can mention different dates. The system preserves chronology and does not resolve ambiguous “Monday or Wednesday” wording without evidence. Finish with: “The main L2 improvement is stateful reasoning over the message stream rather than treating every message as an independent classification.”
