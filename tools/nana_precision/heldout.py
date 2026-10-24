"""Independent finite-state oracle; new random graphs only after candidate freeze.

Worker sees the task, never oracle search state, solution, seed or evaluators.
This is unseen structural symbolic generalization, not LLM semantic reasoning.
"""
import argparse,collections,hashlib,json,random,subprocess,sys
from pathlib import Path
from .benchmark import verify,canonical


def generated(seed,count=18):
    rng=random.Random(seed)
    for case in range(count):
        size=rng.randint(9,14);prefix='h'+str(rng.getrandbits(40));ops=[]
        for i in range(size):
            requires=rng.sample(['permit',*(f's{j}' for j in range(i))],k=rng.randint(0,min(2,i+1)))
            consumes=['permit'] if rng.random()<.18 else []
            produces=[f's{i}']
            if i>1 and rng.random()<.3:produces.append('s'+str(rng.randrange(i)))
            args={}
            if i>0 and rng.random()<.22:args={'input_from':prefix+'.op'+str(rng.randrange(i))}
            ops.append({'operator_id':prefix+'.op'+str(i),'capability':'world.publish','resource':'synthetic://heldout/'+prefix+'/'+str(i),'args':args,'requires':requires,'produces':produces,'consumes':consumes,'cost':rng.randint(1,5)})
        rng.shuffle(ops)
        desired=rng.sample(['s'+str(i) for i in range(size//2,size)],rng.randint(1,3))
        if case%6==0:desired.append('missing')
        obj={'objective_id':'precision.heldout'+str(case),'scope':'precision','motivation_source':'PROJECT_COMPLETION','task_domain':'novel-transition-graph','desired':desired,'initial':['permit'],'operators':ops,'max_steps':32}
        yield {'objective':obj,'source_record_id':'heldout-public-'+str(case),'world_revision':hashlib.sha256(canonical(obj).encode()).hexdigest()}


def oracle(request):
    obj=request['objective'];goal=set(obj['desired']);start=(frozenset(obj['initial']),frozenset())
    queue=collections.deque((start,));seen={start}
    while queue:
        facts,used=queue.popleft()
        if goal<=facts:return True
        for op in obj['operators']:
            oid=op['operator_id'];binding=op['args'].get('input_from')
            if oid in used or not set(op['requires'])<=facts or (binding and binding not in used):continue
            state=(frozenset((facts-set(op['consumes']))|set(op['produces'])),used|{oid})
            if state not in seen:
                if len(seen)>200000:raise RuntimeError('ORACLE_BOUND_NOT_A_VERDICT')
                seen.add(state);queue.append(state)
    return False


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();rows=[]
    for request in generated(a.seed):
        feasible=oracle(request)
        raw=subprocess.run([sys.executable,str(Path(__file__).with_name('worker.py')),str(a.source)],input=canonical(request),text=True,capture_output=True,timeout=10,check=True)
        result=json.loads(raw.stdout)
        rows.append({'case_id':request['objective']['objective_id'],'request_sha256':hashlib.sha256(canonical(request).encode()).hexdigest(),'feasible':feasible,**verify(request,result,feasible),'result':result})
    output={'scope':'UNSEEN_RANDOM_TRANSITION_GRAPHS_NOT_MODEL_SEMANTICS','source':str(a.source),'seed':a.seed,'count':len(rows),'correct':sum(r['correct'] for r in rows),'feasible':sum(r['feasible'] for r in rows),'verified_completions':sum(r['verified_completion'] for r in rows),'invalid_proposals':sum(r['invalid_proposal'] for r in rows),'false_success':sum(r['false_success'] for r in rows),'oracle_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows}
    a.out.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({k:v for k,v in output.items() if k!='rows'}))


if __name__=='__main__':main()
