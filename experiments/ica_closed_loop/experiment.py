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
PILOT_SEED=267
CONFIRM_SEED=310267

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

def build_tasks(n=8, cohort='pilot'):
    if cohort == 'pilot':
        if n > len(TEMPLATES):
            raise ValueError('pilot cohort contains exactly eight frozen tasks')
        rng=random.Random(PILOT_SEED)
        out=[instantiate(i,p,rng) for i,p in enumerate(TEMPLATES[:n])]
        for t in out: t['cohort']='pilot'
        return out
    if cohort == 'confirmatory':
        rng=random.Random(CONFIRM_SEED)
        out=[]
        for i in range(n):
            pair=TEMPLATES[i % len(TEMPLATES)]
            t=instantiate(8+i,pair,rng)
            t['cohort']='confirmatory'
            out.append(t)
        return out
    raise ValueError(cohort)

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
    # Transport/parser fix only: decode nested JSON from the first opening brace.
    # The previous regex stopped at the inner args brace and mislabeled valid calls INVALID.
    s=text.strip()
    start=s.find('{')
    if start >= 0:
        try:
            obj,_=json.JSONDecoder().raw_decode(s[start:])
            tool=str(obj.get('tool','')).upper(); args=obj.get('args',{})
            if tool and isinstance(args,dict):
                return tool,{str(k):v for k,v in args.items()}
        except Exception:
            pass
    m=re.search(r'CALL\\s+([A-Za-z_]+)\\s*(.*)',text,re.I)
    if not m: return 'INVALID',{}
    tool=m.group(1).upper(); rest=m.group(2); args={}
    for k,v in re.findall(r'(\\w+)\\s*=\\s*([^,\\s}]+)',rest):
        try: v=int(v)
        except: v=v.strip("\\\"'")
        args[k]=v
    return tool,args

def parser_self_test():
    assert parse_call('{"tool":"ADD","args":{"key":"amber","delta":3}}') == ('ADD',{'key':'amber','delta':3})
    assert parse_call('CALL COPY src=amber dst=jade') == ('COPY',{'src':'amber','dst':'jade'})

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

def call_model(model,messages,max_retries=8):
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
            err=repr(e); time.sleep(min(60,8*(attempt+1)))
    raise RuntimeError(err)

def run_episode(model,task,interface,repeat=0):
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
      'model':model,'task_id':task['task_id'],'cohort':task.get('cohort'),'repeat':repeat,'interface':interface,
      'initial':task['initial'],'goal':task['goal'],'instruction':task['instruction'],
      'target':[list(x) for x in target],'canonical':[list(x) for x in canonical],
      'y':y,'P_fine':p_fine,'P_macro':p_macro,'pass_Pfine':int(p_fine>=threshold),'pass_Pmacro':int(p_macro>=threshold),'endpoint_success':int(state==task['goal']),'exact_plan':int(all(y)),
      'final_state':state,'raw_calls':raw,'api_meta':api_meta
    }

def percentile_bootstrap(vals,B=10000,seed=310267):
    vals=list(vals)
    if not vals: return None
    rng=random.Random(seed); n=len(vals); boots=[]
    for _ in range(B):
        sample=[vals[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample)/n)
    boots.sort()
    return {'n_tasks':n,'mean':sum(vals)/n,
            'ci95':[boots[int(.025*B)],boots[min(B-1,int(.975*B))]]}

def signflip_p(vals,B=100000,seed=310268):
    vals=list(vals)
    if not vals: return None
    obs=abs(sum(vals)/len(vals)); rng=random.Random(seed)
    extreme=0
    for _ in range(B):
        stat=abs(sum((v if rng.random()<0.5 else -v) for v in vals)/len(vals))
        extreme += int(stat >= obs - 1e-12)
    return (extreme+1)/(B+1)

def task_cluster_interface_contrast(rows,field,model=None):
    tasks=sorted(set(r['task_id'] for r in rows))
    vals=[]
    for tid in tasks:
        tr=[r for r in rows if r['task_id']==tid and (model is None or r['model']==model)]
        models=sorted(set(r['model'] for r in tr))
        mdiffs=[]
        for m in models:
            fine=[r[field] for r in tr if r['model']==m and r['interface']=='fine']
            macro=[r[field] for r in tr if r['model']==m and r['interface']=='macro']
            if fine and macro:
                mdiffs.append(sum(macro)/len(macro)-sum(fine)/len(fine))
        if mdiffs: vals.append(sum(mdiffs)/len(mdiffs))
    out=percentile_bootstrap(vals)
    if out is not None:
        out['randomization_p']=signflip_p(vals)
        out['cluster_unit']='task; models and repeats retained within task'
    return out

def task_cluster_measurement_contrast(rows,interface):
    tasks=sorted(set(r['task_id'] for r in rows)); vals=[]
    for tid in tasks:
        tr=[r for r in rows if r['task_id']==tid and r['interface']==interface]
        if tr:
            vals.append(sum(r['P_macro']-r['P_fine'] for r in tr)/len(tr))
    out=percentile_bootstrap(vals)
    if out is not None:
        out['randomization_p']=signflip_p(vals)
        out['cluster_unit']='task; models and repeats retained within task'
    return out

def task_cluster_interaction(rows):
    tasks=sorted(set(r['task_id'] for r in rows)); vals=[]
    for tid in tasks:
        tr=[r for r in rows if r['task_id']==tid]
        md=[]
        for m in sorted(set(r['model'] for r in tr)):
            f=[r['P_macro']-r['P_fine'] for r in tr if r['model']==m and r['interface']=='fine']
            g=[r['P_macro']-r['P_fine'] for r in tr if r['model']==m and r['interface']=='macro']
            if f and g: md.append(sum(g)/len(g)-sum(f)/len(f))
        if md: vals.append(sum(md)/len(md))
    return percentile_bootstrap(vals)

def task_cluster_model_margin(rows,interface,field,model_a,model_b):
    tasks=sorted(set(r['task_id'] for r in rows)); vals=[]
    for tid in tasks:
        a=[r[field] for r in rows if r['task_id']==tid and r['interface']==interface and r['model']==model_a]
        b=[r[field] for r in rows if r['task_id']==tid and r['interface']==interface and r['model']==model_b]
        if a and b: vals.append(sum(a)/len(a)-sum(b)/len(b))
    out=percentile_bootstrap(vals)
    if out is not None:
        out['randomization_p']=signflip_p(vals)
        out['contrast']=model_a+' minus '+model_b
    return out

def summ_group(rows):
    o={}
    for I in ('fine','macro'):
      rr=[r for r in rows if r['interface']==I]
      if rr:
        o[I]={k:sum(float(x[k]) for x in rr)/len(rr) for k in ('endpoint_success','exact_plan','P_fine','P_macro','pass_Pfine','pass_Pmacro')}
        o[I]['n']=len(rr)
    return o

def summarize(rows):
    out={'n_episodes':len(rows),'n_tasks':len(set(r['task_id'] for r in rows)),
         'models':{},'overall':{},'inference_unit':'task cluster'}
    models=sorted(set(r['model'] for r in rows))
    for model in models:
        mr=[r for r in rows if r['model']==model]; out['models'][model]=summ_group(mr)
    out['overall']=summ_group(rows)

    fields=['endpoint_success','exact_plan','P_fine','P_macro','pass_Pfine','pass_Pmacro']
    out['paired_macro_minus_fine_interface']={
        f:task_cluster_interface_contrast(rows,f) for f in fields
    }
    out['paired_macro_minus_fine_interface_by_model']={
        m:{f:task_cluster_interface_contrast(rows,f,m) for f in fields} for m in models
    }
    out['measurement_Pmacro_minus_Pfine']={
        I:task_cluster_measurement_contrast(rows,I) for I in ('fine','macro')
    }
    out['interaction']=task_cluster_interaction(rows)

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

    if len(models)==2:
        out['model_margins']={}
        for I in ('fine','macro'):
            for field in ('endpoint_success','P_fine','P_macro'):
                out['model_margins'][f'I_{I}_{field}']=task_cluster_model_margin(
                    rows,I,field,models[0],models[1])

    by={}
    for r in rows:
        by.setdefault((r['model'],r['task_id'],r.get('repeat',0)),{})[r['interface']]=r
    pairs=[v for v in by.values() if 'fine' in v and 'macro' in v]
    out['decision_flips']={
      'behavior_at_Pfine':sum(v['fine']['pass_Pfine']!=v['macro']['pass_Pfine'] for v in pairs),
      'behavior_at_Pmacro':sum(v['fine']['pass_Pmacro']!=v['macro']['pass_Pmacro'] for v in pairs),
      'measurement_with_Ifine':sum(r['interface']=='fine' and r['pass_Pfine']!=r['pass_Pmacro'] for r in rows),
      'measurement_with_Imacro':sum(r['interface']=='macro' and r['pass_Pfine']!=r['pass_Pmacro'] for r in rows),
      'n_paired_interface':len(pairs)
    }
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--models',nargs='*',default=MODELS)
    ap.add_argument('--tasks',type=int,default=8)
    ap.add_argument('--cohort',choices=['pilot','confirmatory'],default='pilot')
    ap.add_argument('--repeats',type=int,default=1)
    ap.add_argument('--concurrency',type=int,default=2)
    ap.add_argument('--out',default='results')
    a=ap.parse_args()
    tasks=build_tasks(a.tasks,a.cohort)
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    manifest={'pilot_seed':PILOT_SEED,'confirm_seed':CONFIRM_SEED,'cohort':a.cohort,
              'models':a.models,'repeats':a.repeats,'tasks':tasks,
              'interfaces':{'fine':schema_text('fine'),'macro':schema_text('macro')},
              'scoring':{'P_fine':'mean exact positional primitive correctness over 4 canonical primitive events',
                         'P_macro':'mean all-correct score over fixed target pairs [1,2] and [3,4]',
                         'decision_threshold':0.5,
                         'decision_threshold_rationale':'predeclared before inspecting confirmatory outcomes; matches the documented DeepEval default threshold used elsewhere in the paper'},
              'endpoint':'all four register values equal target final state',
              'frozen_before_inference':True,
              'primary_inference_unit':'task cluster; models and repeats retained together'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    jobs=[(m,t,I,rep) for m in a.models for t in tasks for I in ('fine','macro') for rep in range(a.repeats)]
    rows=[]
    def one(job):
      m,t,I,rep=job
      print('START',m,t['task_id'],I,rep,flush=True)
      r=run_episode(m,t,I,rep)
      print('DONE',m,t['task_id'],I,rep,r['endpoint_success'],r['P_fine'],r['P_macro'],flush=True)
      return r
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
      futs=[ex.submit(one,j) for j in jobs]
      for f in as_completed(futs):
        try: rows.append(f.result())
        except Exception as e: print('JOBFAIL',repr(e),flush=True)
    rows.sort(key=lambda r:(r['model'],r['task_id'],r.get('repeat',0),r['interface']))
    with (out/'trajectories.jsonl').open('w') as f:
      for r in rows: f.write(json.dumps(r)+'\n')
    summary=summarize(rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print('SUMMARY_JSON='+json.dumps(summary,separators=(',',':')),flush=True)

if __name__=='__main__': main()
