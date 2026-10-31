#!/usr/bin/env python3
import csv, json, random, re, statistics, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API_URL = "https://oai.aihorde.net/v1/chat/completions"
API_KEY = "0000000000"
MODELS = [
    "koboldcpp/Qwen2.5-Coder-3B-Instruct",
    "koboldcpp/llama-3.2-3b-instruct-q4_k_m",
]
TEMPERATURE = 0.0
MAX_TOKENS = 160
MAX_STEPS = 6
RETRIES = 6
TASKS = [
    {"id":"T01","sku":"AX-14","stock":17,"reserved":5,"incoming":9,"reorder":6,"needed":10},
    {"id":"T02","sku":"BK-22","stock":11,"reserved":4,"incoming":20,"reorder":8,"needed":8},
    {"id":"T03","sku":"CM-07","stock":23,"reserved":11,"incoming":3,"reorder":5,"needed":12},
    {"id":"T04","sku":"DN-31","stock":8,"reserved":1,"incoming":16,"reorder":4,"needed":9},
    {"id":"T05","sku":"EP-09","stock":19,"reserved":10,"incoming":12,"reorder":7,"needed":8},
    {"id":"T06","sku":"FQ-18","stock":14,"reserved":6,"incoming":5,"reorder":3,"needed":8},
    {"id":"T07","sku":"GR-25","stock":30,"reserved":17,"incoming":0,"reorder":10,"needed":14},
    {"id":"T08","sku":"HS-03","stock":9,"reserved":2,"incoming":30,"reorder":6,"needed":7},
]

FINE_TOOLS = {
    "read_on_hand": "read_on_hand(sku) -> integer current sellable on-hand units",
    "read_reserved": "read_reserved(sku) -> integer units already reserved",
    "read_incoming": "read_incoming(sku) -> integer units arriving later; NOT available immediately",
    "read_reorder_point": "read_reorder_point(sku) -> integer planning threshold; irrelevant to immediate fulfillment",
    "subtract": "subtract(a,b) -> a-b",
    "add": "add(a,b) -> a+b",
    "compare_ge": "compare_ge(a,b) -> true iff a>=b",
    "compare_le": "compare_le(a,b) -> true iff a<=b",
    "finish": "finish(answer) where answer is YES or NO",
}
MACRO_TOOLS = {
    "inventory_snapshot": "inventory_snapshot(sku) -> {on_hand,reserved}; exactly read_on_hand + read_reserved",
    "future_inventory_snapshot": "future_inventory_snapshot(sku) -> {on_hand,incoming}; exactly read_on_hand + read_incoming",
    "fulfillment_check": "fulfillment_check(on_hand,reserved,needed) -> {available,can_fulfill}; exactly subtract(on_hand,reserved) + compare_ge(available,needed)",
    "restock_check": "restock_check(on_hand,incoming,needed) -> {future_stock,can_fulfill_later}; exactly add(on_hand,incoming) + compare_ge(future_stock,needed)",
    "finish": "finish(answer) where answer is YES or NO",
}

def expected(task):
    available = task["stock"] - task["reserved"]
    ans = "YES" if available >= task["needed"] else "NO"
    return [
        ("read_on_hand", (task["sku"],)),
        ("read_reserved", (task["sku"],)),
        ("subtract", (task["stock"], task["reserved"])),
        ("compare_ge", (available, task["needed"])),
    ], ans

def prompt(task, interface):
    tools = FINE_TOOLS if interface == "fine" else MACRO_TOOLS
    tool_lines = "\n".join(f"- {v}" for v in tools.values())
    return f"""You are a tool-using inventory agent. Decide whether an order can be fulfilled IMMEDIATELY.

Task:
SKU: {task['sku']}
Requested units: {task['needed']}

Policy:
- Immediate available stock is current on-hand minus already-reserved units.
- Incoming stock arrives later and MUST NOT count.
- The reorder point is irrelevant to this decision.
- You must use tools to obtain/compute the answer. Do not guess.

Available tools:
{tool_lines}

Protocol:
- On every turn output exactly ONE line of the form:
CALL {{"tool":"tool_name","args":{{...}}}}
- Use only listed tools.
- Do not include explanations or markdown.
- When ready, call finish with answer YES or NO.
"""

def call_model(model, messages):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }).encode()
    last = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(
            API_URL, data=body,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type":"application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"], data
        except Exception as e:
            last = repr(e)
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(last)

CALL_RE = re.compile(r'CALL\s*(\{.*\})', re.S)
def parse_call(text):
    m = CALL_RE.search(text.strip())
    if not m:
        raise ValueError("missing CALL JSON")
    obj = json.loads(m.group(1))
    return obj["tool"], obj.get("args", {})

def fine_exec(task, tool, args):
    if tool == "read_on_hand": return task["stock"], [("read_on_hand",(args.get("sku"),))]
    if tool == "read_reserved": return task["reserved"], [("read_reserved",(args.get("sku"),))]
    if tool == "read_incoming": return task["incoming"], [("read_incoming",(args.get("sku"),))]
    if tool == "read_reorder_point": return task["reorder"], [("read_reorder_point",(args.get("sku"),))]
    if tool == "subtract":
        a,b = args.get("a"), args.get("b")
        return a-b, [("subtract",(a,b))]
    if tool == "add":
        a,b = args.get("a"), args.get("b")
        return a+b, [("add",(a,b))]
    if tool == "compare_ge":
        a,b = args.get("a"), args.get("b")
        return bool(a>=b), [("compare_ge",(a,b))]
    if tool == "compare_le":
        a,b = args.get("a"), args.get("b")
        return bool(a<=b), [("compare_le",(a,b))]
    raise ValueError("unknown fine tool")

def macro_exec(task, tool, args):
    if tool == "inventory_snapshot":
        sku=args.get("sku")
        return {"on_hand":task["stock"],"reserved":task["reserved"]}, [
            ("read_on_hand",(sku,)), ("read_reserved",(sku,))]
    if tool == "future_inventory_snapshot":
        sku=args.get("sku")
        return {"on_hand":task["stock"],"incoming":task["incoming"]}, [
            ("read_on_hand",(sku,)), ("read_incoming",(sku,))]
    if tool == "fulfillment_check":
        s,r,n=args.get("on_hand"),args.get("reserved"),args.get("needed")
        avail=s-r
        return {"available":avail,"can_fulfill":bool(avail>=n)}, [
            ("subtract",(s,r)), ("compare_ge",(avail,n))]
    if tool == "restock_check":
        s,i,n=args.get("on_hand"),args.get("incoming"),args.get("needed")
        future=s+i
        return {"future_stock":future,"can_fulfill_later":bool(future>=n)}, [
            ("add",(s,i)), ("compare_ge",(future,n))]
    raise ValueError("unknown macro tool")

def ordered_match_bits(canonical, expected_steps):
    bits=[]; pos=0
    for want in expected_steps:
        found=False
        while pos < len(canonical):
            got=canonical[pos]; pos += 1
            if got == want:
                found=True; break
        bits.append(1 if found else 0)
    return bits

def run_one(model, interface, task):
    messages=[{"role":"system","content":prompt(task,interface)}]
    canonical=[]; raw=[]; final=None; errors=[]
    for step in range(MAX_STEPS):
        try:
            text, meta=call_model(model,messages)
        except Exception as e:
            errors.append("model:"+repr(e)); break
        raw.append({"step":step,"assistant":text})
        messages.append({"role":"assistant","content":text})
        try:
            tool,args=parse_call(text)
            if tool=="finish":
                ans=str(args.get("answer","")).strip().upper()
                final = ans if ans in {"YES","NO"} else None
                raw[-1]["parsed"]={"tool":tool,"args":args}
                break
            allowed = FINE_TOOLS if interface=="fine" else MACRO_TOOLS
            if tool not in allowed:
                raise ValueError("unlisted tool")
            if interface=="fine":
                result, prims=fine_exec(task,tool,args)
            else:
                result, prims=macro_exec(task,tool,args)
            canonical.extend(prims)
            raw[-1]["parsed"]={"tool":tool,"args":args}
            raw[-1]["result"]=result
            messages.append({"role":"user","content":"TOOL_RESULT "+json.dumps(result,separators=(',',':'))})
        except Exception as e:
            errors.append(f"step{step}:"+repr(e))
            messages.append({"role":"user","content":"TOOL_ERROR Invalid call. Output exactly one valid CALL JSON line using the listed tools."})
    exp, expected_ans=expected(task)
    bits=ordered_match_bits(canonical,exp)
    fine_score=sum(bits)/4
    coarse_score=(int(bool(bits[0] and bits[1])) + int(bool(bits[2] and bits[3])))/2
    return {
        "model":model,"interface":interface,"task":task["id"],
        "expected_answer":expected_ans,"final_answer":final,
        "decision_correct": int(final==expected_ans),
        "primitive_bits":bits,"fine_score":fine_score,"coarse_score":coarse_score,
        "canonical_trace":canonical,"raw":raw,"errors":errors,
    }

def bootstrap_ci(vals, seed=20261031, B=10000):
    rng=random.Random(seed); n=len(vals)
    sims=[sum(vals[rng.randrange(n)] for _ in range(n))/n for _ in range(B)]
    sims.sort()
    return [sims[int(.025*B)], sims[int(.975*B)]]

def analyze(rows):
    out={}
    for model in MODELS:
        mr=[r for r in rows if r["model"]==model]
        cells={}
        for I in ["fine","macro"]:
            rr=[r for r in mr if r["interface"]==I]
            cells[I]={
                "P_fine":statistics.mean(r["fine_score"] for r in rr),
                "P_macro":statistics.mean(r["coarse_score"] for r in rr),
                "decision_accuracy":statistics.mean(r["decision_correct"] for r in rr),
            }
        by={(r["task"],r["interface"]):r for r in mr}
        beh_f=[]; beh_c=[]; meas_f=[]; meas_m=[]; inter=[]; decision_flips=[]
        for t in [x["id"] for x in TASKS]:
            f=by[(t,"fine")]; m=by[(t,"macro")]
            beh_f.append(m["fine_score"]-f["fine_score"])
            beh_c.append(m["coarse_score"]-f["coarse_score"])
            meas_f.append(f["coarse_score"]-f["fine_score"])
            meas_m.append(m["coarse_score"]-m["fine_score"])
            inter.append((m["coarse_score"]-m["fine_score"]) - (f["coarse_score"]-f["fine_score"]))
            decision_flips.append(int(f["final_answer"] != m["final_answer"]))
        out[model]={
            "cells":cells,
            "behavior_effect_at_P_fine":{"mean":statistics.mean(beh_f),"ci95":bootstrap_ci(beh_f)},
            "behavior_effect_at_P_macro":{"mean":statistics.mean(beh_c),"ci95":bootstrap_ci(beh_c)},
            "measurement_effect_at_I_fine":{"mean":statistics.mean(meas_f),"ci95":bootstrap_ci(meas_f)},
            "measurement_effect_at_I_macro":{"mean":statistics.mean(meas_m),"ci95":bootstrap_ci(meas_m)},
            "interaction":{"mean":statistics.mean(inter),"ci95":bootstrap_ci(inter)},
            "interface_decision_flip_rate":statistics.mean(decision_flips),
        }
    rankings={}
    for I in ["fine","macro"]:
        for P,key in [("fine","fine_score"),("macro","coarse_score")]:
            rankings[f"I_{I}_P_{P}"]={m:statistics.mean(r[key] for r in rows if r["model"]==m and r["interface"]==I) for m in MODELS}
    out["rankings"]=rankings
    return out

def main():
    outdir=Path("results"); outdir.mkdir(exist_ok=True)
    jobs=[(m,I,t) for m in MODELS for I in ["fine","macro"] for t in TASKS]
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(run_one,*j):j for j in jobs}
        for fut in as_completed(futs):
            j=futs[fut]
            try: r=fut.result()
            except Exception as e: r={"model":j[0],"interface":j[1],"task":j[2]["id"],"fatal":repr(e)}
            rows.append(r)
            print(json.dumps({k:r.get(k) for k in ("model","interface","task","fine_score","coarse_score","decision_correct","fatal")}),flush=True)
    rows.sort(key=lambda r:(r["model"],r["interface"],r["task"]))
    (outdir/"raw_results.json").write_text(json.dumps(rows,indent=2))
    good=[r for r in rows if "fatal" not in r]
    summary=analyze(good) if len(good)==len(rows) else {"fatal_count":len(rows)-len(good)}
    (outdir/"summary.json").write_text(json.dumps(summary,indent=2))
    with open(outdir/"scores.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["model","interface","task","fine_score","coarse_score","decision_correct","final_answer","expected_answer","primitive_bits"])
        for r in good:
            w.writerow([r["model"],r["interface"],r["task"],r["fine_score"],r["coarse_score"],r["decision_correct"],r["final_answer"],r["expected_answer"],"".join(map(str,r["primitive_bits"]))])
    print("SUMMARY")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
