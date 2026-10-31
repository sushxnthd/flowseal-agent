# ICA closed-loop I×P experiment — frozen protocol

Frozen before inference on 2026-10-31.

## Question
Does a model-visible change in tool granularity change closed-loop behavior, and how does that behavioral effect interact with a separately chosen scoring partition?

## Models
Exactly two currently-online public AI Horde models:
1. `koboldcpp/Qwen2.5-Coder-3B-Instruct`
2. `koboldcpp/llama-3.2-3b-instruct-q4_k_m`

No model is added, removed, or replaced based on outcomes.

## Tasks
Eight deterministic inventory-fulfillment tasks T01–T08. The decision rule is fixed:
`available = on_hand - reserved`; answer YES iff `available >= needed`.
Incoming stock and reorder point are distractors and never count toward immediate fulfillment.

## Interface factor I
- `I_fine`: primitive tools `read_on_hand`, `read_reserved`, `read_incoming`, `read_reorder_point`, `subtract`, `add`, `compare_ge`, `compare_le`, plus `finish`.
- `I_macro`: fixed two-operation composites. `inventory_snapshot` expands to `read_on_hand + read_reserved`; `fulfillment_check` expands to `subtract + compare_ge`. Two distractor macros, `future_inventory_snapshot` and `restock_check`, are likewise fixed compositions of the corresponding distractor primitives. Macro outputs expose both component results.

The macro interface is defined before inference and is never selected from observed errors.

## Canonical primitive trace
Every executed macro is deterministically expanded into its underlying primitive operations. Thus trajectories from either interface are mapped to the same primitive vocabulary before scoring.

## Scoring factor P
The expected primitive sequence has four steps:
1. read_on_hand(sku)
2. read_reserved(sku)
3. subtract(on_hand,reserved)
4. compare_ge(available,needed)

`P_fine`: mean correctness of the four required primitive steps.

`P_macro`: two predeclared contiguous blocks, [1,2] and [3,4]. A block scores 1 iff both constituent primitive steps are correct; the final score is the mean of the two block labels.

Extra distractor operations do not erase a correctly executed required step, but they are retained in the raw trajectory and can be analyzed separately.

## Closed-loop protocol
Each model sees one interface only. It emits one tool call at a time, receives the deterministic tool result, and continues until `finish(YES|NO)` or six model turns. Temperature is 0.0 and max output is 160 tokens. Invalid calls receive one deterministic error message and consume a turn.

## Analysis
For each model report the full 2×2 matrix:
- E(I_fine,P_fine)
- E(I_fine,P_macro)
- E(I_macro,P_fine)
- E(I_macro,P_macro)

Also report:
- behavioral contrasts at fixed P,
- measurement contrasts within each I,
- difference-in-differences interaction,
- end-to-end decision accuracy,
- interface-induced decision flip rate,
- pairwise model ordering in all four cells,
- paired task-bootstrap 95% confidence intervals for contrasts.

No claim of ranking reversal or statistical significance will be made unless it appears under this frozen protocol.
