#!/usr/bin/env python3
import argparse, json, random, statistics, urllib.request
from pathlib import Path

TASKS = [
 {"id":"T1","source":"alpha","source_value":7,"op1":"mul","v1":3,"op2":"add","v2":4,"dest":"omega","target":25},
 {"id":"T2","source":"beta","source_value":18,"op1":"sub","v1":5,"op2":"mul","v2":2,"dest":"theta","target":26},
 {"id":"T3","source":"gamma","source_value":9,"op1":"add","v1":8,"op2":"sub","v2":3,"dest":"kappa","target":14},
 {"id":"T4","source":"delta","source_value":6,"op1":"mul","v1":4,"op2":"sub","v2":7,"dest":"sigma","target":17},
 {"id":"T5","source":"eta","source_value":15,"op1":"sub","v1":6,"op2":"add","v2":11,"dest":"tau","target":20},
 {"id":"T6","source":"iota","source_value":5,"op1":"add","v1":7,"op2":"mul","v2":3,"dest":"upsilon","target":36},
 {"id":"T7","source":"lambda","source_value":21,"op1":"sub","v1":9,"op2":"mul","v2":4,"dest":"phi","target":48},
 {"id":"T8","source":"mu","source_value":8,"op1":"mul","v1":5,"op2":"add","v2":6,"dest":"psi","target":46}
]

SYSTEM = """You are an agent operating a deterministic register workspace. Select the next tool from the supplied schema. Never invent a tool. Do not explain. Return exactly one JSON object. Use observations from prior tool calls."""

FINE_TOOLS = """Available tools:
read: {"tool":"read","key":"alpha"}
add: {"tool":"add","value":4}
sub: {"tool":"sub","value":5}
mul: {"tool":"mul","value":3}
write: {"tool":"write","key":"omega"}
check: {"tool":"check","key":"omega","target":25}
Use exactly the operations requested by the task, in order. Return JSON only."""

MACRO_TOOLS = """Available tools:
read_transform: {"tool":"read_transform","key":"alpha","op":"mul","value":3}
Semantics: read(key), then exactly one arithmetic transform op from add/sub/mul.
transform_write_check: {"tool":"transform_write_check","op":"add","value":4,"key":"omega","target":25}
Semantics: exactly one arithmetic transform, then write(key), then check(key,target).
The macros compile to the same primitive operations as the fine interface. Return JSON only."""

def post_json(url, payload, timeout=180):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def chat(base, messages):
    out = post_json(base.rstrip("/") + "/v1/chat/completions", {
        "model":"local","messages":messages,"temperature":0.0,
        "max_tokens":96,"seed":17})
    return out["choices"][0]["message"]["content"]

def parse_json(text):
    t=text.strip()
    if "~~~" in t:
        t=t.replace("~~~json","").replace("~~~","").strip()
    a=t.find("{"); b=t.rfind("}")
    if a >= 0 and b > a:
        t=t[a:b+1]
    try:
        return json.loads(t), None
    except Exception as e:
        return None, type(e).__name__ + ": " + str(e)

def apply_op(x, op, v):
    if op=="add": return x+v
    if op=="sub": return x-v
    if op=="mul": return x*v
    raise ValueError(op)

class Env:
    def __init__(self, task):
        self.mem={task["source"]:task["source_value"]}
        self.work=None
        self.events=[]
        self.done=False

    def prim(self, name, **kw):
        ok=True
        try:
            if name=="read":
                self.work=self.mem[kw["key"]]
                obs="value="+str(self.work)
            elif name in ("add","sub","mul"):
                if self.work is None: raise ValueError("no working value")
                self.work=apply_op(self.work,name,int(kw["value"]))
                obs="value="+str(self.work)
            elif name=="write":
                if self.work is None: raise ValueError("no working value")
                self.mem[kw["key"]]=self.work
                obs="wrote="+str(self.work)
            elif name=="check":
                got=self.mem.get(kw["key"])
                target=int(kw["target"])
                passed=(got==target)
                obs="check="+("PASS" if passed else "FAIL")+" got="+str(got)+" target="+str(target)
                self.done=True
            else:
                raise ValueError("unknown primitive")
        except Exception as e:
            ok=False
            obs="ERROR "+str(e)
        self.events.append({"tool":name,**kw,"executor_ok":ok,"observation":obs})
        return obs

    def call(self, call, interface):
        if not isinstance(call,dict) or "tool" not in call:
            return "ERROR malformed call"
        t=call["tool"]
        try:
            if interface=="fine":
                if t=="read": return self.prim("read",key=str(call["key"]))
                if t in ("add","sub","mul"): return self.prim(t,value=int(call["value"]))
                if t=="write": return self.prim("write",key=str(call["key"]))
                if t=="check": return self.prim("check",key=str(call["key"]),target=int(call["target"]))
                return "ERROR tool not in fine schema"
            if t=="read_transform":
                o1=self.prim("read",key=str(call["key"]))
                if o1.startswith("ERROR"): return o1
                o2=self.prim(str(call["op"]),value=int(call["value"]))
                return o1+"; "+o2
            if t=="transform_write_check":
                o1=self.prim(str(call["op"]),value=int(call["value"]))
                if o1.startswith("ERROR"): return o1
                o2=self.prim("write",key=str(call["key"]))
                o3=self.prim("check",key=str(call["key"]),target=int(call["target"]))
                return o1+"; "+o2+"; "+o3
            return "ERROR tool not in macro schema"
        except Exception as e:
            return "ERROR "+str(e)

def expected(task):
    return [
      {"tool":"read","key":task["source"]},
      {"tool":task["op1"],"value":task["v1"]},
      {"tool":task["op2"],"value":task["v2"]},
      {"tool":"write","key":task["dest"]},
      {"tool":"check","key":task["dest"],"target":task["target"]}
    ]

def match(e,x):
    if e.get("tool") != x.get("tool"): return 0
    for k,v in x.items():
        if k!="tool" and e.get(k)!=v: return 0
    return 1

def score(task, events):
    exp=expected(task)
    bits=[match(events[i],x) if i < len(events) else 0 for i,x in enumerate(exp)]
    fine=sum(bits)/5.0
    coarse=(int(all(bits[:2]))+int(all(bits[2:])))/2.0
    endpoint=0
    for e in reversed(events):
        if e.get("tool")=="check":
            endpoint=int("check=PASS" in e.get("observation","") and
                         e.get("key")==task["dest"] and int(e.get("target",-999))==task["target"])
            break
    exact=int(bits==[1,1,1,1,1] and len(events)==5)
    return bits,fine,coarse,endpoint,exact,max(0,len(events)-5)

def make_prompt(task, interface):
    tasktxt=("Task: read key "+task["source"]+"; "+task["op1"]+" "+str(task["v1"])+
             "; then "+task["op2"]+" "+str(task["v2"])+"; write the result to key "+
             task["dest"]+"; then verify key "+task["dest"]+" equals "+str(task["target"])+".")
    return tasktxt+"\n\n"+(FINE_TOOLS if interface=="fine" else MACRO_TOOLS)

def run_episode(base, model_name, task, interface):
    env=Env(task)
    msgs=[{"role":"system","content":SYSTEM},{"role":"user","content":make_prompt(task,interface)}]
    max_turns=7 if interface=="fine" else 4
    raw=[]
    for turn in range(max_turns):
        txt=chat(base,msgs)
        call,err=parse_json(txt)
        raw.append({"turn":turn,"raw":txt,"parsed":call,"parse_error":err})
        obs="ERROR invalid JSON" if call is None else env.call(call,interface)
        msgs.append({"role":"assistant","content":txt})
        msgs.append({"role":"user","content":"Observation: "+obs+"\nReturn the next tool call as one JSON object."})
        if env.done: break
    bits,fine,coarse,endpoint,exact,extra=score(task,env.events)
    return {"model":model_name,"task_id":task["id"],"interface":interface,
            "events":env.events,"raw_turns":raw,"bits":bits,"score_fine":fine,
            "score_coarse":coarse,"endpoint_success":endpoint,
            "exact_trace":exact,"extra_events":extra}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",default="http://127.0.0.1:8080")
    ap.add_argument("--model-name",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    rows=[]
    for task in TASKS:
        for interface in ("fine","macro"):
            print("RUN",args.model_name,task["id"],interface,flush=True)
            try:
                row=run_episode(args.base,args.model_name,task,interface)
            except Exception as e:
                row={"model":args.model_name,"task_id":task["id"],"interface":interface,
                     "fatal_error":repr(e),"events":[],"raw_turns":[],"bits":[0]*5,
                     "score_fine":0.0,"score_coarse":0.0,
                     "endpoint_success":0,"exact_trace":0,"extra_events":0}
            rows.append(row)
            Path(args.out).write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows,indent=2))

if __name__=="__main__":
    main()
