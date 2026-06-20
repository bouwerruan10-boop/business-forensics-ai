# Imara finding-quality rubric (LLM-as-judge)

The judge scores each finding **1 (poor) → 5 (excellent)** on four criteria:

| Criterion | 5 = excellent | 1 = poor |
|---|---|---|
| **specificity** | Cites concrete ZAR figures, dates, thresholds | Vague generality, no numbers |
| **actionability** | Owner could act on the recommendation today | No clear next step |
| **grounding** | Claims tied to the data / cited SA law; no fabrication | Invented facts or law |
| **severity_fit** | Severity matches the stated financial impact | Mismatched (e.g. "critical" on a trivial issue) |

## How the judge is kept trustworthy
An LLM judge is only useful if it correlates with humans. Process (per the research):
1. **Pin model versions** — both the agent model and `JUDGE_MODEL` are pinned, so a silent provider update is detected as a score change, not absorbed silently.
2. **Validate against a human-labelled set** — label ~20 findings by hand, run the judge, and require **75–90% agreement** before trusting the judge to scale. Read the disagreements: they reveal whether the *rubric* is unclear or the *judge* lacks context.
3. **Humans own the golden assertions** — never let an LLM write the regression expectations (it locks in current bugs). The deterministic graders below are the human-authored truth.

## Layers (defence in depth)
- **`grade_deterministic`** (no API, CI) — extraction + ratio correctness vs known-correct expectations.
- **`grade_structure`** (no API, CI) — % of findings meeting the FINDING_RULES contract (ZAR quantified, recommendation, benchmark, valid severity). Catches prompt drift.
- **`grade_sa_citation`** (no API, CI) — % of SA findings citing a specific Act/section. Measures the RAG grounding (Build 1) actually taking effect.
- **`grade_report`** (paid) — coverage of planted issues + faithfulness conflicts + Imara band sanity.
- **`grade_findings_with_judge`** (paid) — the semantic rubric above.
