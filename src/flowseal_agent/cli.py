import argparse, json
from pathlib import Path
from .core import FlowGraph, Node

def main() -> None:
    p=argparse.ArgumentParser(description="Audit label flow through a tool graph"); p.add_argument("graph"); a=p.parse_args()
    data=json.loads(Path(a.graph).read_text()); g=FlowGraph()
    for n in data["nodes"]:
        g.add_node(Node(n["name"],n.get("kind","transform"),frozenset(n.get("source_labels",[])),frozenset(n.get("removes",[])),frozenset(n.get("adds",[])),None if "allowed_labels" not in n else frozenset(n["allowed_labels"])))
    for src,dst in data["edges"]: g.add_edge(src,dst)
    r=g.audit(); print(json.dumps({"valid":r.valid,"labels_at":{k:sorted(v) for k,v in r.labels_at.items()},"violations":[{"sink":v.sink,"label":v.label,"path":v.path} for v in r.violations]},indent=2)); raise SystemExit(0 if r.valid else 2)
if __name__ == "__main__": main()
