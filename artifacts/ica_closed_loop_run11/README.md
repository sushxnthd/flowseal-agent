# IEEE ICA closed-loop I×P pilot — verified clean run

## Frozen run and durable repository record

The scientific protocol was fixed before the clean run. The authoritative protocol file records the pre-outcome source anchors; the clean run itself executed at commit `a469ebc12e51e26fb21bc371adb591d2ecc21873`.

This directory now persists the run manifest, summary, and compressed raw trajectories in Git rather than relying on expiring GitHub Actions retention. Decode the raw trajectories with `base64 -d trajectories.jsonl.gz.b64 | gzip -d > trajectories.jsonl`.

Raw trajectory SHA-256: `e2bb4dbc39635758940af89de9720586e36ec1db55aa18d63b72be4739aaf719`.

- Workflow run: https://github.com/sushxnthd/flowseal-agent/actions/runs/41167125568
- Run head SHA: `a469ebc12e51e26fb21bc371adb591d2ecc21873`
- Artifact digest: `sha256:fb292dad02a2b5b8c24045b2535ea3e45e16d6b34924790c04a1ba533046ed26`
- Episodes: 32 = 2 models × 8 tasks × 2 interfaces
- Transport errors: 0
- Invalid canonical events: 0

An independent verifier recomputed every primitive-position score, two-block macro score, 0.5-threshold decision, and endpoint outcome from the raw canonical trajectories and matched the stored values exactly.

## Full 2×2 mean-score matrix

| Model | I_fine / P_fine | I_fine / P_macro | I_macro / P_fine | I_macro / P_macro |
|---|---:|---:|---:|---:|
| Qwen2.5-Coder-3B-Instruct | 1.000 | 1.000 | 0.375 | 0.1875 |
| Llama-3.2-3B-Instruct-Q4_K_M | 0.40625 | 0.1875 | 0.28125 | 0.250 |
| Pooled | 0.703125 | 0.59375 | 0.328125 | 0.21875 |

## Behavioral interface effect, I_macro − I_fine

Pooled, with 5,000-resample bootstrap clustered by the eight shared tasks:
- at P_fine: −0.375, 95% CI [−0.46875, −0.28125]
- at P_macro: −0.375, 95% CI [−0.46875, −0.28125]
- endpoint success: 0.5625 → 0.0625, difference −0.500, 95% CI [−0.6875, −0.3125]
- threshold decisions change on 9/16 model-task pairs at P_fine (7 pass→fail, 2 fail→pass)
- threshold decisions change on 11/16 at P_macro (8 pass→fail, 3 fail→pass)

## Measurement effect, P_macro − P_fine

Pooled:
- with I_fine: −0.109375, 95% CI [−0.15625, −0.0625]
- with I_macro: −0.109375, 95% CI [−0.171875, −0.046875]
- difference-in-differences interaction: 0.000, 95% CI [−0.078125, 0.078125]

Thus the pooled pilot cleanly separates a model-visible behavioral effect from a fixed-execution scoring effect.

## Model ordering

Qwen-minus-Llama paired task margins:
- I_fine / P_fine: +0.59375, 95% CI [0.4375, 0.750]
- I_fine / P_macro: +0.8125, 95% CI [0.625, 0.9375]
- I_macro / P_fine: +0.09375, 95% CI [−0.15625, 0.40625]
- I_macro / P_macro: −0.0625, 95% CI [−0.375, 0.3125]

The final cell has a point-estimate ordering reversal, but its interval crosses zero. The paper therefore does **not** claim a statistically established real-model ranking reversal.

## Integrity note

The original infrastructure run was invalid because a nested-JSON parser bug mislabeled valid calls and failed to apply them to the environment. Scientific choices were not tuned in response. Only the parser/retry/concurrency transport layer was repaired before the clean rerun. See `experiments/ica_closed_loop/EXPERIMENT_PROTOCOL.md` for the pre-outcome commit anchors and full provenance.


## Files persisted in Git

- `manifest.json`: frozen task/interface/scoring manifest used by the clean run.
- `summary.json`: stored run summary.
- `trajectories.jsonl.gz.b64`: gzip-compressed, base64-encoded raw trajectories including model responses, parsed calls, canonical events, states, and endpoint outcomes.

The Actions page is retained only as execution provenance; the repository commit containing these files is the durable citation target.
