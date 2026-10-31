#!/usr/bin/env python3
import argparse, json, random, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

API='https://oai.aihorde.net/v1/chat/completions'
ANON='0000000000'
MODELS=[
    'koboldcpp/Qwen2.5-Coder-3B-Instruct',
    'koboldcpp/llama-3.2-3b-instruct-q4_k_m',
]
REGS=['amber','cobalt','jade','violet']
SEED=267

MACROS={
 'ADD_COPY': lambda a:[('ADD',a['src'],int(a['delta'])),('COPY',a['src'],a['dst'])],
 'COPY_ADD': lambda a:[('COPY',a['src'],a['dst']),('ADD',a['dst'],int(a['delta']))],
 'SET_COPY': lambda a:[('SET',a['src'],int(a['value'])),('COPY',a['src'],a['dst'])],
 'SWAP_ADD': lambda a:[('SWAP',a['a'],a['b']),('ADD',a['a'],int(a['delta']))],
}
TEMPLATES=[
 ('ADD_COPY','COPY_ADD'),('COPY_ADD','ADD_COPY'),('SET_COPY','COPY_ADD'),('SWAP_ADD','ADD_COPY'),
 ('ADD_COPY','SET_COPY'),('COPY_ADD','SWAP_ADD'),('SET_COPY','ADD_COPY'),('SWAP_ADD','COPY_ADD'),
]

def distinct(rng,n): return rng.sample(REGS,n)

def instantiate(idx,pair,rng):
    state={k:rng.randint(1,9) for k in REGS}
    specs=[]; clauses=[]
    for m in pair:
        if m=='ADD_COPY':
            src,dst=distinct(rng,2); d=rng.choice([-4,-3,-2,2,3,4])
            a={'src':src,'dst':dst,'delta':d}; clauses.append(f"increase {src} by {d} and copy the resulting value into {dst}")
        elif m=='COPY_ADD':
            src,dst=distinct(rng,2); d=rng.choice([-4,-3,-2,2,3,4])
            a={'src':src,'dst':dst,'delta':d}; clauses.append(f"copy {src} into {dst} and then increase {dst} by {d}")
        elif m=='SET_COPY':
            src,dst=distinct(rng,2); v=rng.randint(2,15)
            a={'src':src,'dst':dst,'value':v}; clauses.append(f"set {src} to {v} and copy that value into {dst}")
        else:
            a1,b=distinct(rng,2); d=rng.choice([-4,-3,-2,2,3,4])
            a={'a':a1,'b':b,'delta':d}; clauses.append(f"swap {a1} with {b} and then increase {a1} by {d}")
        specs.append((m,a))
    target=[]
    for m,a in specs: target.extend(MACROS[m](a))
    s=deepcopy(state)
    for ev in target: apply_primitive(s,ev)
    instruction=f"First {clauses[0]}. Then {clauses[1]}. Do exactly those operations in order and do not alter any other register."
    return {'task_id':idx+1,'initial':state,'specs':specs,'target':target,'goal':s,'instruction':instruction}

def build_tasks():
    rng=random.Random(SEED)
    return [instantiate(i,p,rng) for i,p in enumerate(TEMPLATES)]

def apply_primitive(state,ev):
    op=ev[0]
    if op=='ADD': state[ev[1]] += int(ev[2])
    elif op=='COPY': state[ev[2]] = state[ev[1]]
    elif op=='SET': state[ev[1]] = int(ev[2])
    elif op=='SWAP': state[ev[1]],state[ev[2]]=state[ev[2]],state[ev[1]]
    elif op=='INVALID': pass
    else: raise ValueError(op)

def schema_text(interface):
    if interface=='fine':
        return """Available tools (one primitive operation per call):
ADD key delta
COPY src dst
SET key value
SWAP a b"""
    return """Available tools (each call atomically executes the two listed primitive operations):
ADD_COPY src dst delta   = ADD src delta; COPY src dst
COPY_ADD src dst delta   = COPY src dst; ADD dst delta
SET_COPY src dst value   = SET src value; COPY src dst
SWAP_ADD a b delta       = SWAP a b; ADD a delta"""

def parse_call(text):
    m=re.search(r'\{[^{}]*\}',text,re.S)
    if m:
        try:
            obj=json.loads(m.group(0)); tool=str(obj.get('tool','')).upper(); args=obj.get('args',{})
            if isinstance(args,dict): return tool,{str(k):v for k,v in args.items()}
        except Exception: pass
    m=re.search(r'CALL\s+([A-Za-z_]+)\s*(.*)',text,re.I)
    if not m: return 'INVALID',{}
    tool=m.group(1).upper(); rest=m.group(2); args={}
    for k,v in re.findall(r'(\w+)\s*=\s*([^,\s}]+)',rest):
        try: v=int(v)
        except: v=v.strip('"\'')
        args[k]=v
    return tool,args

def canonicalize(interface,tool,args):
    try:
        if interface=='fine':
            if tool=='ADD' and args.get('key') in REGS: return [('ADD',args['key'],int(args['delta']))]
            if tool=='COPY' and args.get('src') in REGS and args.get('dst') in REGS: return [('COPY',args['src'],args['dst'])]
            if tool=='SET' and args.get('key') in REGS: return [('SET',args['key'],int(args['value']))]
            if tool=='SWAP' and args.get('a') in REGS and args.get('b') in REGS: return [('SWAP',args['a'],args['b'])]
            return [('INVALID',)]
        if tool not in MACROS: return [('INVALID',),('INVALID',)]
        if tool in ('ADD_COPY','COPY_ADD'):
            aa={'src':args.get('src'),'dst':args.get('dst'),'delta':int(args.get('delta'))}
            if aa['src'] not in REGS or aa['dst'] not in REGS: raise ValueError
        elif tool=='SET_COPY':
            aa={'src':args.get('src'),'dst':args.get('dst'),'value':int(args.get('value'))}
            if aa['src'] not in REGS or aa['dst'] not in REGS: raise ValueError
        else:
            aa={'a':args.get('a'),'b':args.get('b'),'delta':int(args.get('delta'))}
            if aa['a'] not in REGS or aa['b'] not in REGS: raise ValueError
        return MACROS[tool](aa)
    except Exception:
        return [('INVALID',)] if interface=='fine' else [('INVALID',),('INVALID',)]

def call_model(model,messages,max_retries=4):
    body={'model':model,'messages':messages,'temperature':0,'max_tokens':96}
    data=json.dumps(body).encode()
    headers={'Authorization':'Bearer '+ANON,'Content-Type':'application/json','User-Agent':'ica-grit-audit/1.0'}
    err=None
    for attempt in range(max_retries):
        try:
            req=urllib.request.Request(API,data=data,headers=headers,method='POST')
            with urllib.request.urlopen(req,timeout=240) as r:
                obj=json.loads(r.read().decode())
            return obj['choices'][0]['message']['content'],obj
        except Exception as e:
            err=repr(e); time.sleep(5*(attempt+1))
    raise RuntimeError(err)

def run_episode(model,task,interface):
    budget=4 if interface=='fine' else 2
    state=deepcopy(task['initial'])
    messages=[
      {'role':'system','content':'You are a deterministic tool-using agent. Output exactly one tool call each turn, no explanation. Use JSON: {"tool":"NAME","args":{...}}. You must use the available call budget; the environment stops after the last call.'},
      {'role':'user','content':f"Initial registers: {json.dumps(state,sort_keys=True)}\nTask: {task['instruction']}\n{schema_text(interface)}\nCall budget: exactly {budget}. Give call 1 now."}
    ]
    canonical=[]; raw=[]; api_meta=[]
    for step in range(budget):
        try: out,obj=call_model(model,messages)
        except Exception as e: out=''; obj={'error':repr(e)}
        tool,args=parse_call(out)
        events=canonicalize(interface,tool,args)
        for ev in events:
            if ev[0] != 'INVALID':
                try: apply_primitive(state,ev)
                except Exception: pass
        canonical.extend(events)
        raw.append({'step':step+1,'response':out,'tool':tool,'args':args,'events':events,'state_after':deepcopy(state)})
        api_meta.append({k:obj.get(k) for k in ('id','model','usage','error') if isinstance(obj,dict) and k in obj})
        if step+1<budget:
            messages.append({'role':'assistant','content':out})
            messages.append({'role':'user','content':f"OBSERVATION after call {step+1}: registers={json.dumps(state,sort_keys=True)}. Give call {step+2} now. JSON only."})
    assert len(canonical)==4,(interface,canonical)
    target=task['target']; y=[int(canonical[i]==target[i]) for i in range(4)]
    p_fine=sum(y)/4; p_macro=((y[0]*y[1])+(y[2]*y[3]))/2
    threshold=0.5
    return {
      'model':model,'task_id':task['task_id'],'interface':interface,
      'initial':task['initial'],'goal':task['goal'],'instruction':task['instruction'],
      'target':[list(x) for x in target],'canonical':[list(x) for x in canonical],
      'y':y,'P_fine':p_fine,'P_macro':p_macro,'pass_Pfine':int(p_fine>=threshold),'pass_Pmacro':int(p_macro>=threshold),'endpoint_success':int(state==task['goal']),'exact_plan':int(all(y)),
      'final_state':state,'raw_calls':raw,'api_meta':api_meta
    }

def bootstrap_diff(rows,a,b,field,B=5000,seed=267):
    rng=random.Random(seed); by={}
    for r in rows: by.setdefault((r['model'],r['task_id']),{})[r['interface']]=r
    pairs=[v for v in by.values() if a in v and b in v]
    vals=[v[b][field]-v[a][field] for v in pairs]
    if not vals: return None
    mean=sum(vals)/len(vals); boots=[]
    for _ in range(B):
        s=[rng.choice(vals) for _ in vals]; boots.append(sum(s)/len(s))
    boots.sort(); return {'n':len(vals),'mean':mean,'ci95':[boots[int(.025*B)],boots[min(B-1,int(.975*B))]]}

def summ_group(rows):
    o={}
    for I in ('fine','macro'):
      rr=[r for r in rows if r['interface']==I]
      if rr:
        o[I]={k:sum(float(x[k]) for x in rr)/len(rr) for k in ('endpoint_success','exact_plan','P_fine','P_macro','pass_Pfine','pass_Pmacro')}
        o[I]['n']=len(rr)
    return o

def summarize(rows):
    out={'n_episodes':len(rows),'models':{},'overall':{}}
    for model in sorted(set(r['model'] for r in rows)):
        mr=[r for r in rows if r['model']==model]; out['models'][model]=summ_group(mr)
    out['overall']=summ_group(rows)
    out['paired_macro_minus_fine_interface']={f:bootstrap_diff(rows,'fine','macro',f) for f in ['endpoint_success','exact_plan','P_fine','P_macro','pass_Pfine','pass_Pmacro']}
    by={}
    for r in rows: by.setdefault((r['model'],r['task_id']),{})[r['interface']]=r
    pairs=[v for v in by.values() if 'fine' in v and 'macro' in v]
    out['decision_flips']={
      'behavior_at_Pfine':sum(v['fine']['pass_Pfine']!=v['macro']['pass_Pfine'] for v in pairs),
      'behavior_at_Pmacro':sum(v['fine']['pass_Pmacro']!=v['macro']['pass_Pmacro'] for v in pairs),
      'measurement_with_Ifine':sum(r['interface']=='fine' and r['pass_Pfine']!=r['pass_Pmacro'] for r in rows),
      'measurement_with_Imacro':sum(r['interface']=='macro' and r['pass_Pfine']!=r['pass_Pmacro'] for r in rows),
      'n_paired_interface':len(pairs)
    }
    matrix={}
    for I in ('fine','macro'):
      rr=[r for r in rows if r['interface']==I]
      matrix[I]={p:(sum(x[p] for x in rr)/len(rr) if rr else None) for p in ('P_fine','P_macro')}
    out['IxP_matrix']=matrix
    if all(matrix[i][p] is not None for i in matrix for p in matrix[i]):
      out['decomposition']={
       'behavior_at_Pfine':matrix['macro']['P_fine']-matrix['fine']['P_fine'],
       'behavior_at_Pmacro':matrix['macro']['P_macro']-matrix['fine']['P_macro'],
       'measurement_with_Ifine':matrix['fine']['P_macro']-matrix['fine']['P_fine'],
       'measurement_with_Imacro':matrix['macro']['P_macro']-matrix['macro']['P_fine'],
       'interaction':(matrix['macro']['P_macro']-matrix['macro']['P_fine'])-(matrix['fine']['P_macro']-matrix['fine']['P_fine'])
      }
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--models',nargs='*',default=MODELS); ap.add_argument('--tasks',type=int,default=8); ap.add_argument('--concurrency',type=int,default=2); ap.add_argument('--out',default='results')
    a=ap.parse_args(); tasks=build_tasks()[:a.tasks]; out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    manifest={'seed':SEED,'models':a.models,'tasks':tasks,'interfaces':{'fine':schema_text('fine'),'macro':schema_text('macro')},'scoring':{'P_fine':'mean exact positional primitive correctness over 4 canonical primitive events','P_macro':'mean all-correct score over fixed target pairs [1,2] and [3,4]','decision_threshold':0.5,'decision_threshold_rationale':'predeclared before inspecting outcomes; matches the documented DeepEval default threshold used elsewhere in the paper'},'endpoint':'all four register values equal target final state','frozen_before_inference':True}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    jobs=[(m,t,I) for m in a.models for t in tasks for I in ('fine','macro')]; rows=[]
    def one(job):
      m,t,I=job; print('START',m,t['task_id'],I,flush=True); r=run_episode(m,t,I); print('DONE',m,t['task_id'],I,r['endpoint_success'],r['P_fine'],r['P_macro'],flush=True); return r
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
      futs=[ex.submit(one,j) for j in jobs]
      for f in as_completed(futs):
        try: rows.append(f.result())
        except Exception as e: print('JOBFAIL',repr(e),flush=True)
    rows.sort(key=lambda r:(r['model'],r['task_id'],r['interface']))
    with (out/'trajectories.jsonl').open('w') as f:
      for r in rows: f.write(json.dumps(r)+'\n')
    summary=summarize(rows); (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print('SUMMARY_JSON='+json.dumps(summary,separators=(',',':')),flush=True)

if __name__=='__main__': main()
