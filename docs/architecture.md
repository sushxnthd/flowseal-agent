# Architecture

```mermaid
flowchart LR
  A[Labeled sources] --> B[Flow graph]
  B --> C[Fixed-point propagation]
  C --> D[Sink policy check]
  D --> E[Violation path]
```
