#!/usr/bin/env python3
import argparse, json, math, random, statistics
from collections import defaultdict
from pathlib import Path

MODELS = ["granite4:3b", "llama3.2:3b", "qwen2.5:3b"]
DOMAINS = ["smarthome","industrial","fleet","agriculture","energy","warehouse","surveillance","healthcare","robotics"]
GRANS = ["primitive","composite_4","composite_2","composite_1"]
GLABEL = {"primitive":"L4","composite_4":"L3","composite_2":"L2","composite_1":"L1"}
REPS = [0,1,2]
SCENARIOS = [f"{d}-{i:03d}" for d in DOMAINS for i in range(1,10)]
SEED = 267
B = 10000

def strict_success(r):
    m = r.get("metrics", {})
    t = r.get("trace_summary", {})
    ok = (
        r.get("error") in (None, "")
        and not bool(t.get("timed_out", False))
        and float(m.get("task_completion", 0)) == 1.0
        and float(m.get("tool_selection_f1", 0)) == 1.0
        and float(m.get("argument_accuracy", 0)) == 1.0
        and abs(float(m.get("sequence_edit_distance", 1))) <= 1e-12
    )
    return 1.0 if ok else 0.0

def metric(r, name):
    if name == "strict_success":
        return strict_success(r)
    if name in ("num_tool_calls","wall_time_seconds"):
        return float(r.get("trace_summary", {}).get(name, 0) or 0)
    return float(r.get("metrics", {}).get(name, 0) or 0)

def percentile(xs, q):
    if not xs: return None
    ys = sorted(xs)
    if len(ys) == 1: return ys[0]
    p = q*(len(ys)-1)
    lo, hi = int(math.floor(p)), int(math.ceil(p))
    if lo == hi: return ys[lo]
    w = p-lo
    return ys[lo]*(1-w)+ys[hi]*w

def mean(xs):
    return sum(xs)/len(xs) if xs else float("nan")

def load_rows(root):
    root=Path(root)
    rows=[]
    files=sorted(root.rglob("results.jsonl"))
    for f in files:
        for ln in f.read_text(errors="replace").splitlines():
            if not ln.strip(): continue
            try:
                x=json.loads(ln)
                x["_source"]=str(f)
                rows.append(x)
            except Exception as e:
                raise RuntimeError(f"bad JSON in {f}: {e}")
    return rows, files

def key(r):
    c=r["condition"]
    return (c["model"],c["domain"],c["granularity"],c["scenario_id"],int(c["repetition"]))

def expected_keys():
    return {
        (m,d,g,f"{d}-{i:03d}",rep)
        for m in MODELS for d in DOMAINS for g in GRANS
        for i in range(1,10) for rep in REPS
    }

def cell_means(rows, metric_name):
    # average repetitions within model x scenario x interface
    vals=defaultdict(list)
    for r in rows:
        c=r["condition"]
        vals[(c["model"],c["scenario_id"],c["granularity"])].append(metric(r,metric_name))
    return {k:mean(v) for k,v in vals.items()}

def stratified_bootstrap_contrast(cell, metric_name, model=None, g1="composite_4", g0="primitive", B=B, seed=SEED):
    rng=random.Random(seed)
    by_domain={d:[f"{d}-{i:03d}" for i in range(1,10)] for d in DOMAINS}
    models=[model] if model else MODELS
    def est(sampled):
        diffs=[]
        for sid in sampled:
            for m in models:
                a=cell.get((m,sid,g1))
                b=cell.get((m,sid,g0))
                if a is not None and b is not None:
                    diffs.append(a-b)
        return mean(diffs)
    observed=est(SCENARIOS)
    boots=[]
    for _ in range(B):
        samp=[]
        for d in DOMAINS:
            sids=by_domain[d]
            samp.extend(rng.choice(sids) for _ in sids)
        boots.append(est(samp))
    return {"estimate":observed,"ci95":[percentile(boots,.025),percentile(boots,.975)],"n_scenarios":81,"bootstrap":"domain-stratified scenario"}

def model_margin_bootstrap(cell, m1, m2, g, B=B, seed=SEED):
    rng=random.Random(seed)
    by_domain={d:[f"{d}-{i:03d}" for i in range(1,10)] for d in DOMAINS}
    def est(sampled):
        ds=[]
        for sid in sampled:
            a=cell.get((m1,sid,g)); b=cell.get((m2,sid,g))
            if a is not None and b is not None: ds.append(a-b)
        return mean(ds)
    obs=est(SCENARIOS)
    boots=[]
    for _ in range(B):
        samp=[]
        for d in DOMAINS:
            sids=by_domain[d]
            samp.extend(rng.choice(sids) for _ in sids)
        boots.append(est(samp))
    return {
        "estimate":obs,
        "ci95":[percentile(boots,.025),percentile(boots,.975)],
        "ci99":[percentile(boots,.005),percentile(boots,.995)],
        "n_scenarios":81
    }

def summarize(rows):
    exp=expected_keys()
    seen=defaultdict(list)
    for r in rows:
        try: seen[key(r)].append(r)
        except Exception: pass
    duplicates={str(k):len(v) for k,v in seen.items() if len(v)>1}
    # Deterministic dedup: retain first lexicographic source only, never outcome-select.
    uniq=[]
    for k in sorted(seen):
        vv=sorted(seen[k], key=lambda r:r.get("_source",""))
        uniq.append(vv[0])
    actual=set(seen)
    missing=sorted(exp-actual)
    unexpected=sorted(actual-exp)

    errors=sum(1 for r in uniq if r.get("error") not in (None,""))
    timeouts=sum(1 for r in uniq if bool(r.get("trace_summary",{}).get("timed_out",False)))

    out={
        "protocol":{"models":MODELS,"domains":DOMAINS,"granularities":GRANS,"repetitions":3,"expected_conditions":2916,"bootstrap_resamples":B,"seed":SEED},
        "completeness":{"jsonl_records_raw":len(rows),"unique_condition_records":len(uniq),"errors":errors,"timeouts":timeouts,"duplicate_keys":duplicates,"missing_count":len(missing),"missing_keys":[list(x) for x in missing[:100]],"unexpected_count":len(unexpected),"unexpected_keys":[list(x) for x in unexpected[:100]]},
        "means":{},
        "contrasts_vs_L4":{},
        "rank_margins":{},
        "established_rank_reversals":[],
        "domain_strict_success":{}
    }

    metrics=["strict_success","task_completion","tool_selection_f1","argument_accuracy","sequence_edit_distance","num_tool_calls","wall_time_seconds"]
    for met in metrics:
        out["means"][met]={}
        for m in ["POOLED"]+MODELS:
            out["means"][met][m]={}
            for g in GRANS:
                rr=[r for r in uniq if r["condition"]["granularity"]==g and (m=="POOLED" or r["condition"]["model"]==m)]
                out["means"][met][m][GLABEL[g]]=mean([metric(r,met) for r in rr])

    for met in ["strict_success","task_completion"]:
        cell=cell_means(uniq,met)
        out["contrasts_vs_L4"][met]={}
        for g in ["composite_4","composite_2","composite_1"]:
            out["contrasts_vs_L4"][met][f"{GLABEL[g]}-L4"]={
                "POOLED":stratified_bootstrap_contrast(cell,met,None,g,"primitive",seed=SEED+GRANS.index(g)),
                **{m:stratified_bootstrap_contrast(cell,met,m,g,"primitive",seed=SEED+100+MODELS.index(m)*10+GRANS.index(g)) for m in MODELS}
            }

    cell=cell_means(uniq,"strict_success")
    pairs=[]
    for i in range(len(MODELS)):
        for j in range(i+1,len(MODELS)):
            pairs.append((MODELS[i],MODELS[j]))
    for m1,m2 in pairs:
        pk=f"{m1} minus {m2}"
        out["rank_margins"][pk]={}
        for g in GRANS:
            out["rank_margins"][pk][GLABEL[g]]=model_margin_bootstrap(cell,m1,m2,g,seed=SEED+1000+i*100+j*10+GRANS.index(g))
        labs=list(out["rank_margins"][pk])
        for a in range(len(labs)):
            for b in range(a+1,len(labs)):
                x=out["rank_margins"][pk][labs[a]]
                y=out["rank_margins"][pk][labs[b]]
                if x["estimate"]*y["estimate"] < 0:
                    x_ex=(x["ci99"][0]>0 or x["ci99"][1]<0)
                    y_ex=(y["ci99"][0]>0 or y["ci99"][1]<0)
                    if x_ex and y_ex:
                        out["established_rank_reversals"].append({"pair":pk,"interface_a":labs[a],"interface_b":labs[b],"margin_a":x,"margin_b":y})

    for d in DOMAINS:
        out["domain_strict_success"][d]={}
        for g in GRANS:
            rr=[r for r in uniq if r["condition"]["domain"]==d and r["condition"]["granularity"]==g]
            out["domain_strict_success"][d][GLABEL[g]]=mean([strict_success(r) for r in rr])

    return out, uniq

def fmt(x):
    if x is None or (isinstance(x,float) and math.isnan(x)): return "NA"
    return f"{x:.4f}"

def markdown(s):
    lines=[]
    c=s["completeness"]
    lines += ["# Broad MCP-GRANITE closed-loop replication", "",
              f"- Unique conditions: {c['unique_condition_records']} / 2916",
              f"- Errors: {c['errors']}; timeouts: {c['timeouts']}; missing: {c['missing_count']}; duplicate keys: {len(c['duplicate_keys'])}", "",
              "## Strict execution success", "",
              "| Model | L4 primitive | L3 4-tool | L2 2-tool | L1 1-tool |",
              "|---|---:|---:|---:|---:|"]
    for m in ["POOLED"]+MODELS:
        z=s["means"]["strict_success"][m]
        lines.append(f"| {m} | {fmt(z['L4'])} | {fmt(z['L3'])} | {fmt(z['L2'])} | {fmt(z['L1'])} |")
    lines += ["","## Pooled interface contrasts vs L4", "",
              "| Endpoint | Contrast | Estimate | 95% CI |",
              "|---|---|---:|---:|"]
    for met in ["strict_success","task_completion"]:
        for k,v in s["contrasts_vs_L4"][met].items():
            z=v["POOLED"]
            lines.append(f"| {met} | {k} | {fmt(z['estimate'])} | [{fmt(z['ci95'][0])}, {fmt(z['ci95'][1])}] |")
    lines += ["","## Model-order stability on strict success","",
              "| Pair | Interface | Margin | 99% CI |",
              "|---|---|---:|---:|"]
    for pair,zz in s["rank_margins"].items():
        for lab,z in zz.items():
            lines.append(f"| {pair} | {lab} | {fmt(z['estimate'])} | [{fmt(z['ci99'][0])}, {fmt(z['ci99'][1])}] |")
    lines += ["",f"Established rank reversals (predeclared criterion): **{len(s['established_rank_reversals'])}**.","",
              "## Domain strict success (pooled models/repetitions)","",
              "| Domain | L4 | L3 | L2 | L1 |","|---|---:|---:|---:|---:|"]
    for d,z in s["domain_strict_success"].items():
        lines.append(f"| {d} | {fmt(z['L4'])} | {fmt(z['L3'])} | {fmt(z['L2'])} | {fmt(z['L1'])} |")
    return "\n".join(lines)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out",default="analysis")
    a=ap.parse_args()
    rows,files=load_rows(a.root)
    if not files: raise SystemExit("No results.jsonl files found")
    s,uniq=summarize(rows)
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(s,indent=2,sort_keys=True))
    (out/"summary.md").write_text(markdown(s))
    with (out/"deduplicated_results.jsonl").open("w") as f:
        for r in uniq:
            r=dict(r); r.pop("_source",None)
            f.write(json.dumps(r,sort_keys=True)+"\n")
    print(markdown(s))
    # Hard fail only for missing declared conditions; scientific errors/timeouts stay in data.
    if s["completeness"]["missing_count"] or s["completeness"]["unexpected_count"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()
