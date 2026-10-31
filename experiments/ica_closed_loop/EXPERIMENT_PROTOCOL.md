# ICA closed-loop I×P experiment — authoritative protocol and provenance

## Scope

This is the experiment reported in the IEEE ICA camera-ready paper. The scientific design was encoded in the executable source before any usable result:

- `57ed1b1dda64a8c1e658bf0c1283e440d8b01ffa` — deterministic register tasks, seed 267, two model IDs, primitive/macro interfaces, canonical primitive targets, endpoint metric, and crossed scoring.
- `bb1961f92a74bebbf004c1178ea4201ab9de3547` — adds the downstream 0.5 pass threshold before outcomes were read.
- `9a03c3273968456702c5328ec4f0995a76e439c0` — changes workflow concurrency only; scientific design unchanged.

A later inventory-fulfillment draft was accidentally written to this prose file after those source anchors. It was never used by the workflow or paper and has been removed. The pre-outcome executable commits above are the authoritative record.

## Question

Does a model-visible change in tool granularity change closed-loop behavior, and how does that behavioral effect interact with a separately chosen scoring partition?

## Models

Exactly two public AI Horde model identifiers:
1. `koboldcpp/Qwen2.5-Coder-3B-Instruct`
2. `koboldcpp/llama-3.2-3b-instruct-q4_k_m`

## Tasks

Eight deterministic register-edit workflows generated with seed 267. Each task has four canonical primitive operations and a deterministic target state over registers `amber`, `cobalt`, `jade`, and `violet`.

## Interface factor I

`I_fine` exposes primitive operations:
- `ADD key delta`
- `COPY src dst`
- `SET key value`
- `SWAP a b`

The fine interface has exactly four model calls.

`I_macro` exposes fixed two-operation macros:
- `ADD_COPY = ADD; COPY`
- `COPY_ADD = COPY; ADD`
- `SET_COPY = SET; COPY`
- `SWAP_ADD = SWAP; ADD`

The macro interface has exactly two model calls. Every macro deterministically expands to two primitives, so either interface maps to exactly four canonical primitive events. After every model call the deterministic executor updates state and the next model turn sees the resulting register state.

## Scoring factor P

Every realized canonical trajectory is scored under both representations:

- `P_fine`: mean exact positional correctness of the four primitive events.
- `P_macro`: fixed blocks [1,2] and [3,4]; a block passes iff both constituent primitive events are correct; score is the mean of the two block bits.

The downstream pass threshold is 0.5. Endpoint success is exact final-state equality.

## Parser/transport correction

The first infrastructure run was invalid because a flat-brace regex truncated nested JSON calls such as
`{"tool":"ADD","args":{"key":"amber","delta":3}}`, so valid actions were mislabeled and not applied to the environment.

Only transport implementation was repaired:
- nested JSON uses `json.JSONDecoder().raw_decode`;
- a parser self-test was added;
- request retries were increased;
- concurrency was reduced to avoid anonymous-endpoint HTTP 429s;
- the clean result is accepted only if independent validation finds zero transport errors and zero `INVALID` canonical events.

Tasks, seed, model IDs, schemas, call budgets, targets, scoring partitions, and threshold were unchanged.

## Valid run

Clean workflow run: https://github.com/sushxnthd/flowseal-agent/actions/runs/41167125568

Head SHA: `a469ebc12e51e26fb21bc371adb591d2ecc21873`

Artifact digest: `sha256:fb292dad02a2b5b8c24045b2535ea3e45e16d6b34924790c04a1ba533046ed26`

All 32 declared episodes completed with no transport errors or invalid canonical events. Independent re-analysis recomputes every stored score from the raw canonical traces. For pooled confidence intervals the two model observations are treated as one task cluster, because both models share the same eight tasks; this changes only the resampling unit, not any point estimate or qualitative conclusion.
