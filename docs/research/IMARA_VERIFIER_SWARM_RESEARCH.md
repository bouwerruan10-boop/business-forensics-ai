# Imara — Research Cycle: Verifier Swarms & "Check Everything Against Source"

**Date:** 21 June 2026
**Trigger:** a claim that the frontier is a 300-agent Kimi-K2.6 swarm with Opus checking every output against every source — a "triple/quadruple checker in a loop."

---

## 1. Fact-check of the claim

**The substrate is real.** Kimi K2.6 (Moonshot AI, April 2026) is a genuine 1T-parameter open-weight MoE model that explicitly ships **agent-swarm scaling to ~300 sub-agents and ~4,000 coordinated steps**, ties GPT-5.5 on SWE-Bench Pro, and leads Humanity's Last Exam (with tools). So "300-agent swarm of Kimi K2.6, checked by a stronger model" is a real architecture, not invented.

**But the framing mixes a real principle with hype.** Two parts are genuinely sound; one is marketing.

- ✅ **"Check every output against every source, in a loop" — sound.** This is the generator–verifier pattern, and the research backs it: self-verification with correction loops gives monotonic accuracy gains, and verification **against external tools/sources** (executable checks, citations) beats verification by opinion.
- ✅ **"Check through Opus" (a different, stronger model) — actually the *right* detail.** Cross-model verification (a *separate* verifier model) measurably beats a model checking itself. So routing outputs to a stronger, different checker is the correct move, not a gimmick.
- ⚠️ **"300 agents" for accuracy — mostly hype.** The accuracy ceiling of a swarm is set by **correlated errors**, not agent count. 300 *identical* Kimi agents share the same blind spots, so their errors correlate and accuracy **saturates early** — research finds diminishing/negative returns once single-agent accuracy exceeds ~45%, most of the gain captured by the first 5–10 agents, and an optimal cluster around 3–4. The thing that keeps paying off is **heterogeneity** (different models, prompts, tools, priors), not scale. So "300 agents" buys throughput and coverage, not 300× correctness.

**Net:** the valuable idea is *a diverse generator + a stronger, source-grounded verifier in a bounded loop*. The "300" is a throughput story dressed up as an accuracy story.

---

## 2. What the research actually says

1. **Generator–verifier loops work** — SETS, ReVeal, PAG (2025): a model proposes, then verifies/corrects, ideally against executable checks or external tools; accuracy rises with test-time compute, especially with correction + reranking.
2. **Source/tool-grounded verification > self-opinion** — the strongest verifiers check claims against something external (tests, citations, computed values), not the model's own confidence (which is poorly calibrated).
3. **Cross-model > self-consistency** — self-consistency hallucination detection saturates (~0.74–0.76 AUROC); a *separate* verifier model lifts the ceiling. (Hence "Opus checks Kimi.")
4. **Swarms are capped by correlated errors** — diversity beats scale; homogeneous swarms saturate fast; LLM-as-judge needs **human grounding** in expert/high-stakes domains.

---

## 3. How Imara already embodies the good parts (and is ahead of the hype)

This is the striking finding: **Imara already implements the research-backed version of "check everything against source" — and does it deterministically, which is stronger than any LLM-checks-LLM loop.**

- **Deterministic-first engine** = the ultimate source-grounded verifier. Every number comes from arithmetic on the actual figures, not LLM opinion. A swarm of LLM checkers is an *approximation* of what Imara's ratio engine does *exactly*. The numbers and the Imara Score are immune to model error by construction.
- **`faithfulness.py`** = a generator–verifier loop already: it cross-checks each finding's *claimed* metric against the deterministically computed ratio and flags conflicts. That is precisely "verify the output against the source," and the verifier can't itself hallucinate.
- **Cross-agent corroboration** (just shipped) = the *diversity* signal the research says matters — heterogeneous specialist agents independently corroborating an issue is exactly the "heterogeneity beats scale" result.
- **Judge evals with human labels** (`validate_judge`) = LLM-as-judge **with human grounding** — matching the research's explicit requirement for high-stakes domains.
- **~20 heterogeneous specialist agents**, not hundreds of clones = already sitting in the research's optimal zone (diverse, not homogeneous-at-scale).

So the reel's lesson, applied naively, would push Imara the *wrong* way (build a big homogeneous swarm). Imara's design is already the version the evidence supports.

---

## 4. The one genuine gap → the improvement worth making

Imara's verifier loop covers **numbers** but not **prose**. The pressure test already noted this: faithfulness guards figure-claims, but an LLM *narrative* finding could still contradict the deterministic facts (or another agent) without being flagged. That's the real, bounded place this research applies.

**Proposed: a deterministic "narrative-consistency" verifier (one bounded pass).**
- After findings are produced, check each finding's *prose* for claims that **contradict the computed ratios** (e.g., text says "margins are healthy" while the ratio engine has gross margin critically below benchmark) or contradict a corroborated cross-agent finding.
- Deterministic-first: detect numeric claims in the prose and compare to `financial_ratios` (extends faithfulness from the cited-metric field to the free text). Flag contradictions into the existing faithfulness/quality surface.
- *Optional, bounded* correction loop: for a flagged finding, run **one** re-prompt asking the agent to reconcile with the deterministic fact (the research is clear that one or two iterations capture the gain; more is diminishing returns + cost).
- *Optional* cross-model check on the single highest-stakes output (the synthesis/credit verdict) using a **different** model — only if a real need justifies the cost; the deterministic core already makes it low-priority.

This is the "checker in a loop" idea applied exactly where Imara has a gap, in Imara's own deterministic style — not a 300-agent swarm.

---

## 5. Recommendation

**Do:** extend the verifier from numbers to prose (deterministic narrative-contradiction check + optional one-pass correction). It's the genuine, bounded win from this research and closes a known gap.

**Don't:** build a large homogeneous agent swarm. The research is unambiguous — correlated errors cap the gain, the cost is real, and Imara's heterogeneous-specialist + deterministic-verifier design already occupies the evidence-backed sweet spot. "300 agents" is the wrong lesson for a focused, cost-sensitive SA SME tool.

**Reframe:** the headline isn't "more agents." It's "a diverse generator + a stronger, *source-grounded* verifier in a bounded loop" — and Imara's source is arithmetic, which beats any LLM checking another LLM.

---

## Sources
- Kimi K2.6 / 300-agent swarm: [MarkTechPost — Kimi K2.6 agent-swarm scaling](https://www.marktechpost.com/2026/04/20/moonshot-ai-releases-kimi-k2-6-with-long-horizon-coding-agent-swarm-scaling-to-300-sub-agents-and-4000-coordinated-steps/) · [InfoQ — Kimi K2.5 agent swarm](https://www.infoq.com/news/2026/02/kimi-k25-swarm/)
- Generator–verifier loops: [ReVeal — iterative generation-verification (arXiv 2506.11442)](https://arxiv.org/pdf/2506.11442) · [Multi-stage self-verification for factual accuracy & citations (arXiv 2509.05741)](https://arxiv.org/html/2509.05741v1)
- Swarm accuracy / correlated errors / diversity: [Agent scaling via diversity (arXiv 2602.03794)](https://arxiv.org/pdf/2602.03794) · [Information-theoretic LLM ensemble selection (arXiv 2602.08003)](https://arxiv.org/pdf/2602.08003)
- Verifier / judge reliability: [Verify when Uncertain — beyond self-consistency (arXiv 2502.15845)](https://arxiv.org/html/2502.15845v1)
