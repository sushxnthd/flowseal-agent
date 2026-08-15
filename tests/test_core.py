from flowseal_agent import FlowGraph, Node

def test_secret_leak_path():
    g=FlowGraph(); g.add_node(Node("user","source",frozenset({"secret"}))); g.add_node(Node("tool")); g.add_node(Node("public","sink",allowed_labels=frozenset({"public"}))); g.add_edge("user","tool"); g.add_edge("tool","public")
    r=g.audit(); assert not r.valid; assert r.violations[0].path == ("user","tool","public")

def test_sanitizer_removes_label():
    g=FlowGraph(); g.add_node(Node("user","source",frozenset({"secret"}))); g.add_node(Node("redact",removes=frozenset({"secret"}),adds=frozenset({"public"}))); g.add_node(Node("public","sink",allowed_labels=frozenset({"public"}))); g.add_edge("user","redact"); g.add_edge("redact","public"); assert g.audit().valid

def test_missing_endpoint_rejected():
    g=FlowGraph(); g.add_node(Node("a"));
    try: g.add_edge("a","b")
    except KeyError: pass
    else: raise AssertionError("expected KeyError")
