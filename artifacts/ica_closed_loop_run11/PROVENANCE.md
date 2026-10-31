# ICA closed-loop pilot: workflow provenance

This file records the workflow attempts that preceded the accepted clean run. A GitHub Actions conclusion of "success" means only that the workflow exited successfully; it does not imply that the scientific output was valid.

The accepted clean dataset is workflow run 11, run ID 41167125568, at commit `a469ebc12e51e26fb21bc371adb591d2ecc21873`.

## Pre-clean attempts

| Run | Run ID | Conclusion | Head commit | Disposition |
|---:|---:|---|---|---|
| 1 | 41163845560 | failure | 11ccb724173a | infrastructure failure; excluded |
| 2 | 41163911221 | failure | cfbe0b0a4d1f | source-storage/infrastructure failure; excluded |
| 3 | 41163916450 | success | 57ed1b1dda64 | completed but later invalidated by nested-JSON parser bug; excluded |
| 4 | 41164067592 | success | bb1961f92a74 | completed but later invalidated by nested-JSON parser bug; excluded |
| 5 | 41164509565 | success | 9a03c3273968 | completed but later invalidated by nested-JSON parser bug; excluded |
| 6 | 41165645174 | cancelled | ed34fc2d75c8 | superseded while freezing protocol; excluded |
| 7 | 41165669258 | cancelled | d909deeb779b | superseded runner attempt; excluded |
| 8 | 41165883381 | failure | 80fb7e5a0138 | parser transport repair failed; excluded |
| 9 | 41165891900 | failure | ed6a4eab6d99 | transport/concurrency failure; excluded |
| 10 | 41165925340 | cancelled | 13da350b962e | superseded parser-transport attempt; excluded |

## Frozen scientific choices

The deterministic task/schema/scoring source was present in commit
`57ed1b1dda64a8c1e658bf0c1283e440d8b01ffa`.

The downstream 0.5 pass threshold was committed in
`bb1961f92a74bebbf004c1178ea4201ab9de3547` at 2026-10-31 03:22:02 UTC.

The accepted clean run began at 2026-10-31 04:05:48 UTC. After the threshold commit and before the clean run, changes were confined to parser, retry, cancellation, and concurrency/transport behavior; the paper's task set, tool schemas, threshold, scoring partitions, and target outcomes were not selected from clean-run results.

No pre-clean run is used in the reported analysis.
