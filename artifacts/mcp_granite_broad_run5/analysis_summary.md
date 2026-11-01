# Broad MCP-GRANITE analysis summary

Authoritative completed run: 41272234268  
Upstream MCP-GRANITE commit: `fbc29280813e9f091e2933b66dc0474c7f6f2cfd`

- Unique conditions: 972 / 972
- Missing: 0
- Duplicate keys: 0
- Errors/timeouts retained as failures: 143

## Pooled strict execution success

| Interface | Mean |
|---|---:|
| L4 primitive | 0.0494 |
| L3 composite_4 | 0.1770 |
| L2 composite_2 | 0.1276 |
| L1 composite_1 | 0.0494 |

## Predeclared pooled contrasts vs L4

| Endpoint | Contrast | Estimate | 95% CI |
|---|---|---:|---:|
| Strict success | L3-L4 | +0.1276 | [0.0576, 0.1975] |
| Strict success | L2-L4 | +0.0782 | [0.0206, 0.1358] |
| Strict success | L1-L4 | 0.0000 | [-0.0370, 0.0329] |
| Task completion | L3-L4 | +0.0905 | [0.0206, 0.1605] |
| Task completion | L2-L4 | +0.0082 | [-0.0658, 0.0864] |
| Task completion | L1-L4 | -0.1070 | [-0.1893, -0.0288] |

Established model-order reversals under the predeclared 99% criterion: **0**.

The compressed condition-level aggregate is stored alongside this file as `deduplicated_results.jsonl.gz.b64`. Decode with:

`base64 -d deduplicated_results.jsonl.gz.b64 | gzip -d > deduplicated_results.jsonl`
