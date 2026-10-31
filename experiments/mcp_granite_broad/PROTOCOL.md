# ICA broad closed-loop replication — frozen protocol

## Purpose

Replace the eight-task register pilot as the primary evidence that model-visible tool granularity changes real closed-loop agent behavior. The original controlled pilot remains a mechanism check for the crossed I x P decomposition; this replication is the broad external behavioral study.

## Upstream benchmark

MCP-GRANITE, pinned to commit `fbc29280813e9f091e2933b66dc0474c7f6f2cfd`.

Upstream benchmark facts used here:
- 81 multi-step scenarios.
- 9 domains: smarthome, industrial, fleet, agriculture, energy, warehouse, surveillance, healthcare, robotics.
- 4 alternative MCP tool-interface granularities over the same domain logic:
  - L4 = `primitive`
  - L3 = `composite_4`
  - L2 = `composite_2`
  - L1 = `composite_1`
- Deterministic mock stores; no injected faults in this study.
- Per-granularity gold-standard tool calls are supplied by the benchmark.

No scenario is selected or removed after outcomes are observed.

## Models

Three public locally served Ollama models, all pulled by exact tag at execution time:

1. `granite4:3b`
2. `llama3.2:3b`
3. `qwen2.5:3b`

The workflow records Ollama model metadata after pull. Model tags are part of the frozen protocol.

## Experimental matrix

Full factorial:

- 3 models
- 81 scenarios
- 4 interface granularities
- 3 repetitions
- fault rate = 0
- max agent turns = 20
- per-condition timeout = 120 s

Total declared conditions: **2,916**.

Execution is sharded only for transport/runtime. Sharding does not change the scientific design.

## Outcomes

All declared conditions are retained. Errors/timeouts count as failures; they are never dropped.

### Primary behavioral endpoint: strict execution success

For a condition, strict success = 1 iff all of the following hold:

- upstream `task_completion == 1`;
- `tool_selection_f1 == 1`;
- `argument_accuracy == 1`;
- `sequence_edit_distance == 0`;
- no execution error or timeout.

Otherwise strict success = 0.

This is intentionally stricter than MCP-GRANITE's text-level task-completion field.

### Secondary endpoints

- upstream task completion;
- tool-selection F1;
- argument accuracy;
- normalized sequence edit distance;
- number of tool calls;
- wall-clock time (descriptive only on shared GitHub-hosted CPU runners).

## Primary estimands

For each interface, first average the three repetitions within each model x scenario cell.

Primary interface contrasts compare each coarser interface with L4 primitive:

- L3 - L4
- L2 - L4
- L1 - L4

for strict success and upstream task completion.

The pooled estimand gives equal weight to each model and scenario. Uncertainty uses a domain-stratified scenario bootstrap: within each of the nine domains, resample its nine scenarios with replacement, retain all models and repetitions for each sampled scenario, and recompute the contrast. 10,000 resamples, seed 267. Report percentile 95% intervals.

Per-model contrasts use the same stratified scenario bootstrap and are secondary.

## Model-order stability

For each interface and each of the three model pairs, compute the scenario-averaged strict-success margin (first model minus second), after averaging repetitions. Use the same domain-stratified scenario bootstrap.

A real-interface ranking reversal is called **established** only if the two compared interfaces give opposite point signs and both corresponding 99% bootstrap intervals exclude zero. Otherwise any sign flip is reported only as a point-order change.

No model pair or interface pair will be selected after seeing outcomes.

## Domain heterogeneity

Report strict-success means by domain x interface, pooled equally over the three models and three repetitions. Domain results are descriptive; no domain is promoted as a primary endpoint.

## Completeness and exclusions

Expected record count is 2,916. The analysis must enumerate:
- completed records,
- errors,
- timeouts,
- duplicate condition keys,
- missing declared keys.

No post-outcome task filtering, model filtering, or "clean-run" subset is permitted. If a model/domain shard fails at infrastructure level, rerun that exact shard with the same frozen design; retain all valid condition records and deduplicate only exact condition keys from retried transport copies.

## Interpretation boundary

This study tests the behavioral axis I: the model sees different tool decompositions and is rerun. It does not claim that executions across interfaces are identical. Fixed-execution scoring-boundary sensitivity P remains tested by the separate GRIT audits in the paper.

The upstream benchmark's own `task_completion` checks expected strings in the final answer rather than simulator-state equivalence. For that reason the predeclared primary endpoint is the stricter trace-based conjunction above, while upstream task completion is reported separately.
