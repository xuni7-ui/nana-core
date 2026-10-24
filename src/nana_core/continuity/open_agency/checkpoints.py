"""Reobserve completed hierarchical work through the original Kernel, not a cache."""
import json
from ...contracts import CoreError
from ...storage import digest


def checked_prefix(service, work, old_plan, objective):
    if not objective.task_groups:
        return (), (), (), ()
    current={op.operator_id:op for op in objective.operators}
    groups=[g for g in objective.task_groups if all(oid in current for oid in g.members)]
    outputs={o['operator_id']:o for o in service._current_outputs(work)}
    eligible=set()
    for group in groups:
        if (any(current[oid].capability=='world.publish' and current[oid].expected_digest for oid in group.members)
                and all(oid in outputs and outputs[oid]['quality'] for oid in group.members)):
            eligible.update(group.members)
    # A checkpoint is a contiguous verified prefix of entire completed groups.
    # No arbitrary skipping, partial group, or out-of-order state assertion.
    selected=[]
    prior=old_plan.get('checkpoint',{}).get('completed_operator_ids',())
    old_table={op['operator_id']:op for op in old_plan['objective']['operators']}
    sequence=[*(old_table[oid] for oid in prior),*old_plan['steps'][:work['cursor']]]
    for op in sequence:
        if op['operator_id'] not in eligible:break
        selected.append(op)
    kept={op['operator_id'] for op in selected}
    # Truncation must not leave only part of an AND group.
    for group in groups:
        if kept.intersection(group.members) and not set(group.members)<=kept:
            kept.difference_update(group.members)
    selected=[op for op in selected if op['operator_id'] in kept]
    facts=set(objective.initial);reused=[];checks=[];parents=[]
    for old in selected:
        oid=old['operator_id'];op=current[oid]
        if any(old.get(key)!=op.model_dump(mode='json').get(key) for key in ('capability','resource','requires','produces','consumes','expected_digest')):
            raise CoreError('CHECKPOINT_DESCRIPTION_CHANGED')
        output=outputs[oid];memory=service.records.memory.read(output['memory_id'])
        action=service.store.one('actions',output['action_id'])
        if not action or action['state']!='SUCCEEDED' or memory['scope']!=objective.scope or memory['privacy_class'] not in service.subject.privacy_classes:
            raise CoreError('CHECKPOINT_SUPPORT_UNAVAILABLE')
        if op.capability in {'world.publish','world.contact'}:
            # Social sends and unverified task-quality outcomes cannot be reused.
            if op.capability=='world.contact' or not op.expected_digest:
                raise CoreError('CHECKPOINT_EFFECT_REVIEW_REQUIRED')
            check=service.realization.kernel.reobserve(action['action_id'],service._authority)
            if check['verdict']!='MATCH' or digest((check['result'] or {}).get('data'))!=op.expected_digest:
                raise CoreError('CHECKPOINT_CURRENT_EFFECT_UNCERTAIN')
            checks.append({'operator_id':oid,**{key:check[key] for key in ('action_id','record_id','event_id','verdict')}})
            parents.append(check['record_id'])
        facts.difference_update(op.consumes);facts.update(op.produces)
        reused.append(output)
    return tuple(op['operator_id'] for op in selected),tuple(sorted(facts)),tuple(reused),tuple(checks)
