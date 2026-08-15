import json, random
from flowseal_agent import FlowGraph, Node
rng=random.Random(9); total=300; detected=0
for i in range(total):
    g=FlowGraph(); g.add_node(Node("source","source",frozenset({"public","secret"}))); g.add_node(Node("prep")); g.add_node(Node("sink","sink",allowed_labels=frozenset({"public"}))); g.add_edge("source","prep")
    leak=(i%2==0)
    if leak: g.add_edge("prep","sink")
    else:
        g.add_node(Node("redact",removes=frozenset({"secret"}))); g.add_edge("prep","redact"); g.add_edge("redact","sink")
    flagged=not g.audit().valid; detected += (flagged==leak)
result={"graphs":total,"leak_classification_accuracy":detected/total}
print(json.dumps(result,indent=2)); open("benchmarks/results.json","w").write(json.dumps(result,indent=2)+"\n")
