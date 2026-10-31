#!/usr/bin/env python3
import argparse, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import experiment as base

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--start',type=int,required=True,help='0-based inclusive task offset')
    ap.add_argument('--count',type=int,default=8)
    ap.add_argument('--concurrency',type=int,default=4)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()

    all_tasks=base.build_tasks(base.N_TASKS)
    tasks=all_tasks[a.start:a.start+a.count]
    if len(tasks)!=a.count:
        raise SystemExit(f'expected {a.count} tasks, got {len(tasks)}')

    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    manifest={
      'study':'32-new-task confirmatory extension, sharded transport',
      'seed':base.SEED,
      'task_start':a.start,
      'task_count':a.count,
      'task_ids':[t['task_id'] for t in tasks],
      'models':base.MODELS,
      'tasks':tasks,
      'interfaces':{'fine':base.schema_text('fine'),'macro':base.schema_text('macro')},
      'scoring':{
        'P_fine':'mean exact positional primitive correctness over 4 canonical primitive events',
        'P_macro':'mean all-correct score over fixed target pairs [1,2] and [3,4]',
        'decision_threshold':0.5
      },
      'frozen_before_inference':True,
      'transport_only_sharding':True
    }
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))

    jobs=[(m,t,I) for m in base.MODELS for t in tasks for I in ('fine','macro')]
    rows=[]
    def one(job):
        m,t,I=job
        print('START',m,t['task_id'],I,flush=True)
        r=base.run_episode(m,t,I)
        print('DONE',m,t['task_id'],I,r['endpoint_success'],r['P_fine'],r['P_macro'],flush=True)
        return r

    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs=[ex.submit(one,j) for j in jobs]
        for f in as_completed(futs):
            rows.append(f.result())

    rows.sort(key=lambda r:(r['model'],r['task_id'],r['interface']))
    expected=len(base.MODELS)*len(tasks)*2
    if len(rows)!=expected:
        raise SystemExit(f'incomplete shard: {len(rows)}/{expected} episodes')
    with (out/'trajectories.jsonl').open('w') as fh:
        for r in rows: fh.write(json.dumps(r)+'\n')
    (out/'summary_shard.json').write_text(json.dumps(base.summarize(rows),indent=2))
    print('SHARD_COMPLETE',a.start,a.count,len(rows),flush=True)

if __name__=='__main__':
    main()
