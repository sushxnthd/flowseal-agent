# ICA 2026 broad MCP-GRANITE closed-loop study

This directory records the camera-ready broad closed-loop study used in "Exact Audits of Boundary Sensitivity in Step-Level Agent Evaluation."

## Frozen design

- Upstream benchmark: MCP-GRANITE commit `fbc29280813e9f091e2933b66dc0474c7f6f2cfd`.
- Protocol: `experiments/mcp_granite_broad/PROTOCOL.md`.
- Pre-outcome reporting plan: `experiments/mcp_granite_broad/REPORTING_PLAN.md`.
- Models: `granite4:3b`, `llama3.2:3b`, `qwen2.5:3b`.
- Scenarios: all 81 benchmark scenarios across nine domains.
- Interfaces: L4 primitive, L3 composite_4, L2 composite_2, L1 composite_1.
- Repetitions: one frozen realization per model x scenario x interface.
- Declared conditions: 972.
- No post-outcome scenario/model filtering.

## Authoritative completed run

GitHub Actions run: `41272234268`.
Head commit: `fe7f10029371992b43cf6501771fade883453e9e`.
Completed: 2026-11-01 05:30 UTC.
All 27 model-domain shards succeeded and the aggregate job succeeded.

Aggregate analysis artifact ID: `13072145222`.
Aggregate artifact SHA-256: `8a46a18daad7e0f33041a4513fa649cafc8d23446d8a08732d3184f1c06a1f20`.

Completeness:
- unique conditions: 972 / 972
- missing: 0
- duplicate keys: 0
- errors: 143
- timeouts: 143

Errors/timeouts were retained as failures exactly as predeclared.

## Pooled results

Strict execution success:
- L4 primitive: 0.0494
- L3 composite_4: 0.1770
- L2 composite_2: 0.1276
- L1 composite_1: 0.0494

Domain-stratified scenario-bootstrap contrasts versus L4, 10,000 resamples:
- strict success L3-L4: +0.1276, 95% CI [0.0576, 0.1975]
- strict success L2-L4: +0.0782, 95% CI [0.0206, 0.1358]
- strict success L1-L4: 0.0000, 95% CI [-0.0370, 0.0329]
- task completion L3-L4: +0.0905, 95% CI [0.0206, 0.1605]
- task completion L2-L4: +0.0082, 95% CI [-0.0658, 0.0864]
- task completion L1-L4: -0.1070, 95% CI [-0.1893, -0.0288]

The predeclared model-order criterion found zero established ranking reversals. Point sign changes are not promoted to robust reversals.

## Interpretation

The broad study establishes that model-visible tool-interface granularity can materially change closed-loop agent performance across a public multi-domain benchmark. The effect is non-monotonic: moderate composition improves strict execution relative to primitive tools, while the coarsest single-dispatch interface removes that gain and significantly reduces benchmark-native task completion.

The separate eight-task register study remains only a controlled I x P mechanism check. It is not used as prevalence evidence.
