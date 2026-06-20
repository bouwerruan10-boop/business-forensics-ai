"""
Parallel specialist execution (Phase 2 of the improvement plan).

The Phase-2 specialists are run in two PARALLEL waves:
  * Wave 1 — base analysts that work from the source data.
  * Wave 2 — synthesis-leaning agents that benefit from seeing Wave 1's findings
    (they run after Wave 1 is merged into shared memory).
Within a wave the agents are independent, so we fan them out across a thread pool
(LLM calls are I/O-bound). Findings are merged back in DECLARED order so output is
deterministic regardless of which agent finishes first. Each agent is isolated:
a failure yields no findings and never sinks the run.
"""
import contextvars
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Agents that synthesise across earlier findings — run in the second wave.
WAVE2_NAMES = {
    "Strategy Agent",
    "Legal Risk Agent",
    "Fraud & Anomaly Detection Agent",
    "Credit Readiness Agent",
    "Valuation Agent",
    "Forecast Agent",
}


def _run_one(AgentClass, business_data, memory):
    agent = AgentClass()
    t = time.perf_counter()
    try:
        fnds = agent.analyze(business_data, memory)
    except Exception as exc:  # isolate: one agent must not sink the analysis
        print("[pipeline] {} failed, skipping: {}".format(getattr(agent, "name", "?"), exc))
        fnds = []
    return agent.name, fnds, round(time.perf_counter() - t, 1)


def _run_wave(classes, business_data, memory, progress_callback, label, max_workers):
    if not classes:
        return
    if progress_callback:
        progress_callback(label, "Running {} specialist agents in parallel...".format(len(classes)))
    collected = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(classes))) as ex:
        futs = [ex.submit(contextvars.copy_context().run, _run_one, C, business_data, memory) for C in classes]
        for fut in as_completed(futs):
            name, fnds, secs = fut.result()
            collected.append((name, fnds, secs))
            if progress_callback:
                progress_callback(name, "{} complete".format(name))
    # Merge in declared order for stable, reproducible output.
    order = {getattr(C, "name", ""): i for i, C in enumerate(classes)}
    for name, fnds, secs in sorted(collected, key=lambda r: order.get(r[0], 99)):
        for fnd in fnds:
            memory.add_finding(fnd)
        memory.agent_timings.append({"agent": name, "seconds": secs})


def run_agent_waves(all_agents, business_data, memory, progress_callback=None,
                    wave2_names=WAVE2_NAMES, max_workers=8):
    """Run all specialists as two parallel waves, mutating `memory` in place."""
    wave1 = [C for C in all_agents if getattr(C, "name", "") not in wave2_names]
    wave2 = [C for C in all_agents if getattr(C, "name", "") in wave2_names]
    _run_wave(wave1, business_data, memory, progress_callback, "Specialist Agents", max_workers)
    _run_wave(wave2, business_data, memory, progress_callback, "Specialist Agents", max_workers)


def run_independent_agents(items, business_data, memory, progress_callback=None,
                           header=None, max_workers=3):
    """Run a set of MUTUALLY-INDEPENDENT agent instances concurrently.

    Each item is (agent, label, message). Every agent.analyze() reads the existing
    findings read-only and writes its OWN disjoint scalar fields on memory, so the
    agents don't interfere. Findings are collected and merged back in list order for
    deterministic output. Used for the pre-synthesis tail (market deep-dive + SA tax
    + SA legal), which previously ran sequentially.
    """
    if not items:
        return
    if progress_callback and header:
        progress_callback(header[0], header[1])

    def _one(item):
        agent, label, _msg = item
        try:
            fnds = agent.analyze(business_data, memory)
        except Exception as exc:
            print("[pipeline] {} failed, skipping: {}".format(label, exc))
            fnds = []
        if progress_callback:
            progress_callback(label, "{} complete".format(label))
        return fnds

    results = [[] for _ in items]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as ex:
        futs = {ex.submit(contextvars.copy_context().run, _one, item): i for i, item in enumerate(items)}
        for fut in as_completed(futs):
            results[futs[fut]] = fut.result() or []
    for fnds in results:
        for f in fnds:
            memory.add_finding(f)
