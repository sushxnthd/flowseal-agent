from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque


@dataclass(frozen=True)
class Node:
    name: str
    kind: str = "transform"
    source_labels: frozenset[str] = field(default_factory=frozenset)
    removes: frozenset[str] = field(default_factory=frozenset)
    adds: frozenset[str] = field(default_factory=frozenset)
    allowed_labels: frozenset[str] | None = None


@dataclass(frozen=True)
class FlowViolation:
    sink: str
    label: str
    path: tuple[str, ...]


@dataclass(frozen=True)
class AuditResult:
    labels_at: dict[str, frozenset[str]]
    violations: tuple[FlowViolation, ...]

    @property
    def valid(self) -> bool:
        return not self.violations


class FlowGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, set[str]] = {}

    def add_node(self, node: Node) -> None:
        if node.kind not in {"source", "transform", "sink"}:
            raise ValueError("kind must be source, transform, or sink")
        self.nodes[node.name] = node
        self.edges.setdefault(node.name, set())

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError("both edge endpoints must exist")
        self.edges[src].add(dst)

    def audit(self) -> AuditResult:
        labels = {name: set(node.source_labels) for name, node in self.nodes.items()}
        changed = True
        rounds = 0
        while changed:
            changed = False; rounds += 1
            if rounds > max(2, len(self.nodes) * len(self.nodes) + 1):
                raise RuntimeError("label propagation did not converge")
            for src, children in self.edges.items():
                outgoing = (labels[src] - set(self.nodes[src].removes)) | set(self.nodes[src].adds)
                for dst in children:
                    before = len(labels[dst]); labels[dst].update(outgoing)
                    if len(labels[dst]) != before: changed = True
        frozen = {k: frozenset((v - set(self.nodes[k].removes)) | set(self.nodes[k].adds)) for k, v in labels.items()}
        violations: list[FlowViolation] = []
        for name, node in self.nodes.items():
            if node.kind != "sink" or node.allowed_labels is None:
                continue
            for label in sorted(frozen[name] - node.allowed_labels):
                path = self._path_for_label(label, name)
                violations.append(FlowViolation(name, label, path or (name,)))
        return AuditResult(frozen, tuple(violations))

    def _path_for_label(self, label: str, sink: str) -> tuple[str, ...] | None:
        starts = [n for n, node in self.nodes.items() if label in node.source_labels]
        q = deque((s, (s,)) for s in starts)
        seen = set(starts)
        while q:
            node, path = q.popleft()
            if node == sink:
                return path
            if label in self.nodes[node].removes:
                continue
            for nxt in self.edges[node]:
                if nxt not in seen:
                    seen.add(nxt); q.append((nxt, path + (nxt,)))
        return None
