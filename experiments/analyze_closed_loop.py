#!/usr/bin/env python3
import json, random, statistics
from pathlib import Path
from ica_closed_loop import TASKS

def paired_bootstrap(a,b,seed=20261031,B=20000):
    rnd=random.Random(seed); n=len(a); ds=[]
    for _ in range(B):
        idx=[rnd.randrange(n) for _ in range(n)]
        ds.append(sum(b[i]-a[i] for i in idx)/n)
    ds.sort()
    return {
      "difference":sum(y-x for x,y in zip(a,b))/n,
      "ci95":[ds[int(.025*B)],ds[min(B-1,int(.975*B))]]
    }

def summarize(rows):
    out={}
    models=sorted(set(r["model"] for r in rows))
    for model in models:
        mr=[r for r in rows if r["model"]==model]
        by={(r["task_id"],r["interface"]):r for r in mr}
        cells={}
        for interface in ("fine","macro"):
            rr=[by[(t["id"],interface)] for t in TASKS]
            cells[interface]={
              "n":len(rr),
              "P_fine":statistics.mean(r["score_fine"] for r in rr),
              "P_macro":statistics.mean(r["score_coarse"] for r in rr),
              "endpoint_success":statistics.mean(r["endpoint_success"] for r in rr),
              "exact_trace":statistics.mean(r["exact_trace"] for r in rr)
            }
        iface={}
        for metric in ("score_fine","score_coarse","endpoint_success","exact_trace"):
            a=[by[(t["id"],"fine")][metric] for t in TASKS]
            b=[by[(t["id"],"macro")][metric] for t in TASKS]
            z=paired_bootstrap(a,b,seed=20261031)
            z["task_flips"]=sum(x!=y for x,y in zip(a,b))
            iface[metric]=z
        meas={}
        for interface in ("fine","macro"):
            rr=[by[(t["id"],interface)] for t in TASKS]
            a=[r["score_fine"] for r in rr]
            b=[r["score_coarse"] for r in rr]
            z=paired_bootstrap(a,b,seed=20261032 if interface=="macro" else 20261031)
            z["threshold_flips_at_0.5"]=sum((x>=.5)!=(y>=.5) for x,y in zip(a,b))
            meas[interface]=z
        interaction=(cells["macro"]["P_macro"]-cells["macro"]["P_fine"])-(
                     cells["fine"]["P_macro"]-cells["fine"]["P_fine"])
        out[model]={"cells":cells,"interface_effects":iface,"measurement_effects":meas,"interaction":interaction}

    by={(r["model"],r["task_id"],r["interface"]):r for r in rows}
    units=[(m,t["id"]) for m in models for t in TASKS]
    pooled={}
    for metric in ("score_fine","score_coarse","endpoint_success","exact_trace"):
        a=[by[(m,t,"fine")][metric] for m,t in units]
        b=[by[(m,t,"macro")][metric] for m,t in units]
        z=paired_bootstrap(a,b,seed=20261033)
        z["unit_flips"]=sum(x!=y for x,y in zip(a,b))
        pooled[metric]=z
    out["POOLED"]={"interface_effects":pooled}
    return out

rows=[]
for p in ("results/qwen.json","results/llama.json"):
    rows += json.loads(Path(p).read_text())
summary=summarize(rows)
Path("results/summary.json").write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
