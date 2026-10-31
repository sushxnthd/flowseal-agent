#!/usr/bin/env python3
import json, random, statistics, sys
from pathlib import Path

path=Path(sys.argv[1])
out=Path(sys.argv[2])
rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
models=sorted(set(r['model'] for r in rows))
q=[m for m in models if 'Qwen' in m][0]
l=[m for m in models if 'llama' in m.lower()][0]
tasks=sorted(set(r['task_id'] for r in rows))
by={(r['task_id'],r['model'],r['interface']):r for r in rows}
missing=[(t,m,I) for t in tasks for m in (q,l) for I in ('fine','macro') if (t,m,I) not in by]
if missing or len(tasks)!=32:
    raise SystemExit(f'incomplete combined dataset: {len(tasks)} tasks, {len(missing)} missing cells')

def ci(vals,B=10000,seed=310267):
    rng=random.Random(seed); n=len(vals)
    boots=[]
    for _ in range(B):
        sample=[vals[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample)/n)
    boots.sort()
    return {'mean':sum(vals)/n,'lo':boots[int(.025*B)],'hi':boots[min(B-1,int(.975*B))],'n_tasks':n}

def task_effect(fn):
    return ci([fn(t) for t in tasks])

def across_models(t,fn):
    return statistics.mean(fn(by[(t,m,'fine')],by[(t,m,'macro')]) for m in (q,l))

res={}
res['behavior_endpoint']=task_effect(lambda t: across_models(t,lambda f,m:m['endpoint_success']-f['endpoint_success']))
res['behavior_Pfine']=task_effect(lambda t: across_models(t,lambda f,m:m['P_fine']-f['P_fine']))
res['behavior_Pmacro']=task_effect(lambda t: across_models(t,lambda f,m:m['P_macro']-f['P_macro']))
res['measurement_Ifine']=task_effect(lambda t: statistics.mean(by[(t,m,'fine')]['P_macro']-by[(t,m,'fine')]['P_fine'] for m in (q,l)))
res['measurement_Imacro']=task_effect(lambda t: statistics.mean(by[(t,m,'macro')]['P_macro']-by[(t,m,'macro')]['P_fine'] for m in (q,l)))
res['interaction']=task_effect(lambda t: statistics.mean((by[(t,m,'macro')]['P_macro']-by[(t,m,'macro')]['P_fine'])-(by[(t,m,'fine')]['P_macro']-by[(t,m,'fine')]['P_fine']) for m in (q,l)))

for I in ('fine','macro'):
    for P in ('P_fine','P_macro'):
        res[f'margin_{I}_{P}']=task_effect(lambda t,I=I,P=P: by[(t,q,I)][P]-by[(t,l,I)][P])
    res[f'margin_{I}_endpoint']=task_effect(lambda t,I=I: by[(t,q,I)]['endpoint_success']-by[(t,l,I)]['endpoint_success'])

flip_pf=flip_pm=meas_if=meas_im=0
for t in tasks:
    for m in (q,l):
        f=by[(t,m,'fine')]; ma=by[(t,m,'macro')]
        flip_pf += int(f['pass_Pfine'] != ma['pass_Pfine'])
        flip_pm += int(f['pass_Pmacro'] != ma['pass_Pmacro'])
        meas_if += int(f['pass_Pfine'] != f['pass_Pmacro'])
        meas_im += int(ma['pass_Pfine'] != ma['pass_Pmacro'])
res['decision_flips']={
  'behavior_Pfine':flip_pf,
  'behavior_Pmacro':flip_pm,
  'measurement_Ifine':meas_if,
  'measurement_Imacro':meas_im,
  'n_model_task_pairs':64
}
res['n_episodes']=len(rows)
res['n_tasks']=len(tasks)
res['models']=[q,l]
out.write_text(json.dumps(res,indent=2))
print(json.dumps(res,indent=2))
