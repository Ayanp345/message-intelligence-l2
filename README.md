# Message Intelligence Pipeline — L2 Extension

This repository is an extension of the submitted L1 message-intelligence system. It keeps the original classifier, extractor and sensitive-data detector, then adds chronological state tracking, explainable priority, related-message grouping, local semantic retrieval, evidence-grounded QA, privacy routing and benchmarking.

## L1 → L2

The original 900 L1 messages are represented by the structured L1 outputs already in `output/`:

- `classifications.json`
- `tasks_events.json`
- `sensitive_findings.json`
- `display_messages.json`

L2 messages are processed strictly after those 900 messages. A later L2 message can update an existing task/event instead of creating a duplicate. Repeated L1 task instances are retained, while related-message groups provide the logical subject-level view.

The supplied L1/L2 datasets are **not committed**. Place the private L2 CSVs under `data/private/` locally when running the pipeline.

## Running

```bash
pip install -r requirements.txt
python src/run_l2.py
python app/app.py
```

The web application runs on the configured Flask port. For production/Render:

```bash
gunicorn app.app:app --bind 0.0.0.0:$PORT
```

## Priority engine

`src/l2_engine.py` calculates priority from multiple signals:

- deadline proximity
- overdue status
- explicit urgency
- confirmation requirement
- follow-up status
- completed/cancelled state
- uncertainty
- sensitivity
- whether the record is an event/action

The output is `output/l2/priority_output.json`.

Every decision contains:

```text
message_id
item_id
priority
reason
signals
confidence
```

Relative dates such as "tomorrow" are resolved only when the reference timestamp makes them deterministic. Ambiguous weekday alternatives are deliberately left unresolved.

Priority is recalculated when a later message changes the deadline, urgency or state.

## Related-message grouping

Groups are subject/task/event level state containers. Matching uses canonical action/event meaning and chronology rather than one common word.

A group retains:

- group ID
- title
- related message IDs
- task/event IDs
- current status
- latest explicit date
- chronological summary
- confidence

Statuses include Pending, In progress, Completed, Rescheduled, Cancelled and Unclear.

The output is `output/l2/related_groups.json`.

## Semantic retrieval

`src/retrieval.py` builds a local TF-IDF index over:

- safe L1 messages
- safe L2 messages
- task/event records
- related groups

Sensitive values are masked before indexing.

The assistant returns:

- answer
- supporting message IDs
- related task/event/group IDs
- relevance scores
- evidence-selection reason

If evidence is insufficient, it explicitly says so rather than inventing an answer.

## Privacy-aware routing

`src/privacy_router.py` has three routes:

1. `local` — ordinary requests stay local.
2. `confirmation_required` — personal/health information requires confirmation.
3. `blocked` — credentials, tokens, passwords, OTPs, financial identifiers and recovery codes are blocked from external processing.

The sensitive detector masks values before anything is written to output or shown in the UI.

The output is `output/l2/privacy_routing.json`.

## Benchmarking

`src/benchmark.py` compares the original simple keyword retrieval approach with the optimized local TF-IDF index on the supplied mandatory queries.

The measured report is:

`output/l2/benchmark_report.json`

The benchmark records mean/p95 retrieval latency and index statistics. It is a retrieval-performance comparison, not a fabricated accuracy claim.

## Current measured run

On the supplied eight demo queries in this environment:

- keyword baseline mean: ~6.47 ms
- keyword baseline p95: ~8.53 ms
- TF-IDF retrieval mean: ~1.37 ms
- TF-IDF retrieval p95: ~1.68 ms
- indexed documents: 1,570
- vocabulary: 2,368 terms

These are environment-specific measurements and should be rerun on the final deployment machine before presenting them as deployment benchmarks.

## Privacy verification

The generated output was checked for the supplied sensitive-looking demo values. No raw OTP, password, token, card number or recovery code appears in `output/` or `src/`.

## Important assumptions and limitations

- L1 raw CSV was not included in the supplied L1 project archive; the safe L1 `display_messages.json` plus structured L1 outputs are used as the L1 evidence layer.
- L1 contains repeated task/event instances with the same title. L2 uses the most recent matching instance for state updates while retaining all historical IDs in the related group.
- Semantic retrieval is intentionally local and lightweight; no external API is required.
- Ambiguous dates are not guessed.
- The assistant is deliberately conservative when evidence does not support a definitive answer.
- A production deployment should add authenticated access, encrypted storage and stronger access controls if real user data is used.

## Files submitted

- `output/l2/priority_output.json`
- `output/l2/related_groups.json`
- `output/l2/privacy_routing.json`
- `output/l2/benchmark_report.json`
- `output/l2/assistant_results.json`
- `output/l2/l2_tasks_events.json`
- `output/l2/l2_display_messages.json`

## AI-tool usage declaration

AI assistance was used for code review, implementation scaffolding and debugging. The supplied datasets were processed locally. No supplied dataset was uploaded to an external model/API by this project. Final system behavior, outputs, assumptions and limitations were inspected against the supplied assignment data.
