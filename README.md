# flowseal-agent

[![CI](https://img.shields.io/github/actions/workflow/status/sushxnthd/flowseal-agent/ci.yml?branch=main&label=CI)](.github/workflows/ci.yml) [![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Live demo](https://sushxnthd.github.io/flowseal-agent/) | [Architecture](docs/architecture.md) | [Benchmark](benchmarks/results.json)

`flowseal-agent` propagates explicit data labels through an agent or tool graph and reports labels that reach sinks where they are not allowed. Violations include a source-to-sink path so the report is actionable.

```bash
pip install -e .
flowseal-agent examples/graph.json
```

## Model

Nodes can introduce labels, remove labels, or declare which labels a sink accepts. Edges represent possible data flow. The audit computes a fixed point over the graph, so cycles are supported as long as label propagation converges.

Typical labels include `public`, `internal`, `pii`, `secret`, or domain-specific tags.

## Scope

This is explicit-label information-flow checking. It does not inspect arbitrary program semantics and cannot detect a sensitive value that was never labeled.

## Roadmap

- structured declassification policies
- trace-to-graph adapters
- policy bundles for common agent architectures
- graph export with highlighted leak paths
