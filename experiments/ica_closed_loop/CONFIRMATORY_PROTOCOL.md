# ICA closed-loop I x P confirmatory extension - frozen protocol

Frozen before inference on 2026-10-31.

## Status
This is a confirmatory extension of the earlier 8-task exploratory pilot. None of the 32 tasks below have been used in the pilot. The extension is committed before any model calls are made.

## Primary question
Does changing the model-visible tool interface I change closed-loop behavior across a broader set of tasks, and how large is the independent measurement effect of changing scoring partition P while holding each realized execution fixed?

## Models
Exactly the same two public models as the pilot:
1. koboldcpp/Qwen2.5-Coder-3B-Instruct
2. koboldcpp/llama-3.2-3b-instruct-q4_k_m

No model is added, removed, or replaced based on outcomes.

## Tasks
Thirty-two new deterministic register-workflow tasks generated from seed 310267. The eight operation-pair templates used in the pilot are repeated four times with independently generated register states, operands, and constants. All 32 concrete task instances are written to the run manifest before inference.

The tasks are not selected or filtered based on model performance.

## Interface factor I
I_fine exposes one primitive operation per call: ADD, COPY, SET, SWAP.

I_macro exposes the same four predeclared two-operation composites as the pilot: ADD_COPY, COPY_ADD, SET_COPY, SWAP_ADD. Every macro deterministically expands into exactly two canonical primitive events.

The fine interface has a four-call budget; the macro interface has a two-call budget. After every call, the model receives the resulting register state. The interfaces therefore intentionally differ in model-visible decision and observation granularity. The vertical I contrast is a behavioral contrast, not a claim of identical realized execution.

## Scoring factor P
Every realized trajectory is canonicalized to four primitive positions.

P_fine is mean exact positional primitive correctness over the four positions.

P_macro is the mean of two all-correct binary blocks over positions [1,2] and [3,4].

The decision threshold is fixed at 0.5 before inference.

## Primary inference
The independent statistical unit is the task. Bootstrap resampling samples whole tasks and retains both models and both interfaces within every resampled task.

Primary reported contrasts:
- endpoint-success change under I_macro minus I_fine;
- score change under I_macro minus I_fine at P_fine;
- measurement change P_macro minus P_fine within each interface;
- I x P interaction;
- Qwen-minus-Llama paired task margin in each I x P cell.

Ten thousand paired task-cluster bootstrap resamples are used. No ranking-reversal or significance claim is made unless the corresponding predeclared interval excludes zero.

## Reproducibility
The action artifact retains the manifest, all raw trajectories, canonical events, model-returned identifiers/metadata, and the summary. No failed task is silently removed; an incomplete run is reported as incomplete rather than analyzed as a reduced dataset.
