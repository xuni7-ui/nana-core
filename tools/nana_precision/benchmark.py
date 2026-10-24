"""Frozen independent transition evaluator and varied bounded task generator.

This measures ARCHITECTURE_PRECISION, not semantic intelligence or real effects.
The worker receives public operators/goals only, never this oracle/seed/answers.
Held-out instances are generated only after code freeze with a fresh seed.
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def tasks(seed, count):
    rng = random.Random(seed)
    for index in range(count):
        family = index % 6
        ops = []
        width = rng.randint(5, 8)
        depth = rng.randint(2, 3)
        desired = []
        prefix = 'f' + str(rng.randrange(10**9))
        if family in (0, 1):
            # Independent chains: state/order permutations, shared prerequisite.
            for branch in range(width):
                last = None
                for step in range(depth):
                    fact = f'{prefix}.{branch}.{step}'
                    ops.append({'operator_id': fact, 'requires': [last] if last else [], 'produces': [fact], 'cost': rng.randint(1, 3)})
                    last = fact
                desired.append(last)
            if family == 1:
                ops.append({'operator_id': prefix+'.shortcut', 'requires': [], 'produces': desired[:3], 'cost': 5})
        elif family == 2:
            # Distractors and alternative valid paths, not a single answer list.
            last = None
            for step in range(rng.randint(5, 8)):
                fact = f'{prefix}.path.{step}'
                ops.append({'operator_id': fact, 'requires': [last] if last else [], 'produces': [fact]})
                last = fact
            desired = [last]
            for step in range(20):
                ops.append({'operator_id': f'{prefix}.noise.{step}', 'requires': [], 'produces': [f'noise.{step}']})
        elif family == 3:
            # Facts alone do not encode which producer supplied required data.
            ops = [
                {'operator_id': prefix+'.cheap', 'requires': [], 'produces': ['ready']},
                {'operator_id': prefix+'.read', 'requires': [], 'produces': ['ready'], 'cost': 3},
                {'operator_id': prefix+'.write', 'requires': ['ready'], 'produces': ['done'], 'args': {'input_from': prefix+'.read'}},
            ]
            desired = ['done']
        elif family == 4:
            # Delete effects and misleading cheap irreversible branch.
            ops = [
                {'operator_id': prefix+'.trap', 'requires': ['token'], 'produces': ['dead'], 'consumes': ['token']},
                {'operator_id': prefix+'.route', 'requires': ['token'], 'produces': ['ready'], 'cost': 3},
                {'operator_id': prefix+'.finish', 'requires': ['ready'], 'produces': ['done'], 'consumes': ['token']},
            ]
            desired = ['done']
        else:
            ops = [{'operator_id': prefix+'.decoy', 'requires': [], 'produces': ['unrelated']}]
            desired = ['impossible']
        for op in ops:
            op.setdefault('cost', 1)
            op.setdefault('consumes', [])
            op.setdefault('capability', 'world.publish' if op.get('args') else 'world.observe')
            op.setdefault('resource', 'synthetic://precision/'+op['operator_id'])
            op.setdefault('args', {})
        rng.shuffle(ops)
        objective = {'objective_id': f'precision.case{index}', 'scope': 'precision', 'motivation_source': 'PROJECT_COMPLETION', 'task_domain': 'precision', 'initial': ['token'] if family == 4 else [], 'desired': desired, 'operators': ops, 'max_steps': 32}
        yield {'objective': objective, 'source_record_id': 'public-source-'+str(index), 'world_revision': hashlib.sha256(canonical(objective).encode()).hexdigest()}, family != 5, family


def verify(request, result, feasible):
    if result['state'] != 'PROPOSED':
        return {'correct': not feasible, 'verified_completion': False, 'invalid_proposal': False, 'false_success': False, 'duplicate_effects': 0}
    proposal = result['proposal']
    facts = set(request['objective']['initial'])
    table = {op['operator_id']: op for op in request['objective']['operators']}
    used = set()
    valid = (proposal['source_record_id'] == request['source_record_id'] and proposal['world_revision'] == request['world_revision'] and len(proposal['operator_ids']) <= request['objective']['max_steps'])
    duplicates = 0
    for oid in proposal['operator_ids']:
        if oid not in table:
            valid = False
            break
        op = table[oid]
        duplicates += oid in used
        valid &= oid not in used and set(op['requires']) <= facts
        valid &= not op['args'].get('input_from') or op['args']['input_from'] in used
        facts.difference_update(op['consumes'])
        facts.update(op['produces'])
        used.add(oid)
    valid &= set(request['objective']['desired']) <= facts
    return {'correct': bool(valid and feasible), 'verified_completion': bool(valid), 'invalid_proposal': not bool(valid), 'false_success': bool(not valid and result.get('validator_accepted')), 'duplicate_effects': duplicates}


def run(source, seed, count):
    rows = []
    for request, feasible, family in tasks(seed, count):
        raw = subprocess.run([sys.executable, str(Path(__file__).with_name('worker.py')), str(source)], input=canonical(request), text=True, capture_output=True, timeout=10, check=True)
        result = json.loads(raw.stdout)
        rows.append({'case_id': request['objective']['objective_id'], 'family': family, 'request_sha256': hashlib.sha256(canonical(request).encode()).hexdigest(), 'feasible': feasible, **verify(request, result, feasible), 'result': result})
    return {'scope': 'ARCHITECTURE_PRECISION_SYNTHETIC_SYMBOLIC', 'model_ablation': 'MODEL_ABLATION_NOT_RUN', 'real_model_calls': 0, 'seed': seed, 'count': count, 'correct': sum(r['correct'] for r in rows), 'verified_completions': sum(r['verified_completion'] for r in rows), 'feasible_count': sum(r['feasible'] for r in rows), 'invalid_proposals': sum(r['invalid_proposal'] for r in rows), 'false_success': sum(r['false_success'] for r in rows), 'duplicate_effects': sum(r['duplicate_effects'] for r in rows), 'source': str(source), 'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--count', type=int, default=24)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.seed, args.count)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}))
