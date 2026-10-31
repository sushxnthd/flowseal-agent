# IEEE ICA 2026 camera-ready artifact: boundary sensitivity audit

This directory supports the camera-ready paper **"Exact Audits of Boundary Sensitivity in Step-Level Agent Evaluation."**

## What is here

- `EXPERIMENT_PROTOCOL.md` - original eight-task closed-loop pilot protocol.
- `CONFIRMATORY_PROTOCOL.md` - frozen 32-new-task confirmatory protocol.
- `SHARDED_EXECUTION_AMENDMENT.md` - transport-only sharding amendment committed before confirmatory outcomes were accessible.
- `TEMPLATE_CLUSTER_SENSITIVITY.md` - predeclared secondary inference clustering the 32 instances into eight operation-pair templates.
- `experiment.py` - canonical task generator, interfaces, executor, canonicalization, and scoring.
- `experiment_shard.py` - deterministic task-slice runner used only to parallelize the frozen confirmatory execution.
- `analyze_combined.py` - aggregate 32-task analysis with task-level resampling.
- `../../docs/ica_camera_ready_proofs.md` - full proofs compressed from the six-page paper.

## Factorial design

The paper separates two effects:

- **Behavioral axis**: change the model-visible interface (I), rerun the agent, and observe a possibly different execution (Y(I)).
- **Measurement axis**: hold a realized execution fixed and change only the scoring partition (P).

The reported score is

`E(I,P) = M_P(Y(I))`.

The fine interface exposes four primitive calls. The macro interface exposes fixed two-operation composites with two calls. The interfaces intentionally differ in decision/observation granularity, so the vertical contrast is a behavioral comparison rather than a claim of identical execution.

Every realized trajectory is canonicalized to four primitive positions and rescored under both:

- `P_fine`: primitive-position accuracy.
- `P_macro`: mean of two predeclared all-correct blocks [1,2] and [3,4].

## Confirmatory extension status

A 32-new-task confirmatory extension was frozen before inference and then re-executed through the transport-only four-shard workflow in `.github/workflows/ica-closed-loop-sharded.yml`. The public-model transport did not complete all predeclared cells before the workflow limits, so the confirmatory dataset is incomplete.

**The camera-ready paper does not analyze or report partial outcomes from that extension.** Its closed-loop claims use only the completed, predeclared eight-task / 32-episode pilot. The confirmatory protocol, execution amendment, and incomplete workflow history are retained for transparency.

The 32 frozen tasks were partitioned deterministically into four disjoint blocks of eight. Sharding changed scheduling only; no task, model, interface, score, threshold, or comparison was selected from outcomes.

## Inference

Primary intervals use 10,000 bootstrap resamples of whole task instances. Both models and both interfaces are retained together within each resampled task.

A stricter predeclared sensitivity analysis additionally averages the four instances belonging to each of the eight operation-pair templates and bootstraps those eight template-level effects.

A model-order reversal is reported only if the predeclared Qwen-minus-Llama intervals exclude zero in opposite directions under the two interfaces. Otherwise the artifact reports a point-order change or no reversal.

## Reproduction

The GitHub Actions workflow is the recommended reproduction route because the two public model endpoints are remote.

For local structural checks:

```bash
python -m py_compile experiments/ica_closed_loop/experiment.py
python -m py_compile experiments/ica_closed_loop/experiment_shard.py
```

The controlled GRIT audits, archived LLM-plan audits, DeepEval/AgentEvals adapters, and AgentProcessBench reanalysis are reported separately in the main research artifact used for the accepted paper. The camera-ready uses the completed closed-loop pilot, adds the proof note, and retains the incomplete larger extension only as a transparent frozen follow-up.
