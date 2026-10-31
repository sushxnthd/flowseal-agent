# Confirmatory execution amendment - transport only

Committed before any confirmatory outcomes were accessible.

The scientific protocol in CONFIRMATORY_PROTOCOL.md is unchanged: same 32 generated tasks, same two models, same two interfaces, same scoring rules, same threshold, same task-cluster inference, and same primary comparisons.

The first monolithic GitHub Actions attempt (run 41186171896) is abandoned for transport/runtime reasons before its job logs or outcomes are available. Its results will not be inspected, analyzed, or reported, regardless of whether that run later completes.

The official confirmatory dataset will be produced by a four-shard workflow. The 32 already-frozen tasks are partitioned deterministically by task index into four disjoint blocks of eight. Each task is run exactly once for each model-interface cell. The four raw trajectory artifacts are then concatenated without filtering, and all inference is run once on the complete 32-task dataset.

Sharding changes only execution scheduling. It does not change any scientific factor or analysis choice.
