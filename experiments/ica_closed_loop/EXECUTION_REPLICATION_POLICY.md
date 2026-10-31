# Confirmatory execution replication policy

Frozen before inspecting any confirmatory outcomes.

The scientific protocol, code, 32 tasks, model IDs, interfaces, scoring rules, threshold, and task-cluster analysis are identical to the already-frozen confirmatory branch.

The original execution uses four concurrent workers. A second execution is launched with eight workers only to reduce public-provider queue latency. Concurrency is infrastructure scheduling, not an experimental factor.

Selection rule: use the first run that completes all 128 predeclared episodes cleanly. Do not select a run based on effect size, significance, ranking direction, or any reported outcome. If both complete, retain both artifacts and treat the second as an execution replicate.
