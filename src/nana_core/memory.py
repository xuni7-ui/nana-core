"""Minimal source-backed claim assessment and pure scoped memory retrieval.

Source fact: a supplied statement exists. Belief: a reversible assessment of its
operator annotation. Neither raw legacy confidence nor this assessment is VERIFIED.
"""
import json
import re
from .contracts import CoreError
from .storage import canonical,digest


class MemoryView:
    def __init__(self,store):self.store=store
    def entries(self,dataset_ids):
        if not dataset_ids or any(not d.startswith('synthetic:') for d in dataset_ids):
            raise CoreError('EXPLICIT_SYNTHETIC_MEMORY_SCOPE_REQUIRED')
        entries=[]
        for memory in self.store.all('memory_items'):
            body=json.loads(memory['body_json']);iris=body.get('iris')
            if not iris or iris['origin']['dataset_id'] not in dataset_ids or memory['status']!='ACTIVE':continue
            refs=body['source_refs']
            # Missing/corrupt evidence cannot silently become supported memory.
            for ref in refs:self.store.artifact(ref['artifact_id'])
            entries.append({'memory_id':memory['memory_id'],'content':body['content'],'iris':iris,
                'epistemic_kind':body['epistemic_kind'],
                'source_refs':[{**{k:r[k] for k in ('event_id','artifact_id','coverage')},
                    'source_kind':self.store.event(r['event_id'])['kind']} for r in refs],'belief':body.get('belief')})
        return entries

    def assess_claims(self,dataset_ids):
        entries=self.entries(dataset_ids);groups={};changed=[];disputed_count=0
        for entry in entries:
            claim=entry['iris']['claim']
            if claim:
                key=digest([entry['iris']['origin']['dataset_id'],claim['subject'],claim['predicate'],claim['value']])
                groups.setdefault(key,[]).append(entry)
        for key,group in groups.items():
            direct=[e for e in group if e['epistemic_kind']=='USER_STATEMENT']
            times=[e['iris']['time']['underlying_event_time_us'] for e in direct]
            opposing=len({e['iris']['claim']['polarity'] for e in direct})>1
            unknown=any(t is None for t in times)
            newest=max((t for t in times if t is not None),default=None)
            latest=[e for e in direct if e['iris']['time']['underlying_event_time_us']==newest]
            unresolved=opposing and (unknown or len({e['iris']['claim']['polarity'] for e in latest})>1)
            disputed_count+=int(unresolved)
            for entry in group:
                polarity=entry['iris']['claim']['polarity']
                support=[e['memory_id'] for e in direct if e['iris']['claim']['polarity']==polarity]
                contradictions=[e['memory_id'] for e in direct if e['iris']['claim']['polarity']!=polarity]
                if entry['epistemic_kind']!='USER_STATEMENT':state='UNASSESSED'
                elif unresolved:state='DISPUTED'
                elif opposing and latest[0]['iris']['claim']['polarity']!=polarity:state='SUPERSEDED'
                else:state='CURRENT_USER_STATEMENT'
                belief={'claim_key':key,'claim':entry['iris']['claim'],'current_assessment':state,
                    'supporting_memory_ids':support,'contradicting_memory_ids':contradictions,
                    'evidence_refs':[ref for e in group for ref in e['source_refs']],
                    'why':'latest dated direct user statement' if not unresolved else 'unknown/tied chronology; preserve dispute',
                    'verified_fact':False,'policy_version':1}
                body=json.loads(self.store.one('memory_items',entry['memory_id'])['body_json'])
                if body.get('belief')!=belief:
                    body['belief']=belief;changed.append((entry['memory_id'],body))
        if changed:
            with self.store.transaction('memory.claims_assessed',{'policy_version':1,'claim_groups':list(groups)}) as tx:
                for key,body in changed:tx.update('memory_items',key,body_json=canonical(body))
        return {'claim_groups':len(groups),'changed':len(changed),'disputed_groups':disputed_count}

    def retrieve(self,query,*,identity_id,dataset_ids,max_chars=4000,limit=8):
        if identity_id!=self.store.identity['identity_id']:raise CoreError('MEMORY_IDENTITY_MISMATCH')
        if not 256<=max_chars<=8000 or not 1<=limit<=20:raise CoreError('MEMORY_CONTEXT_BOUND')
        entries=self.entries(dataset_ids);tokens=set(re.findall(r'\w+',query.casefold()))
        def relevance(e):return len(tokens&set(re.findall(r'\w+',e['content'].casefold())))
        selected=[e for e in entries if relevance(e)]
        selected.sort(key=lambda e:(e['belief'] is not None and e['belief']['current_assessment']=='CURRENT_USER_STATEMENT',
            relevance(e),e['iris']['time']['legacy_record_time_us'] or -1,e['memory_id']),reverse=True)
        # Keep source-backed contradiction partners adjacent, ahead of generic
        # matches. A bounded context must not prefer extra matches over the
        # evidence that qualifies its top current belief.
        indexed={e['memory_id']:e for e in entries};ordered=[];seen=set()
        for entry in selected:
            bundle=[entry]+[indexed[mid] for mid in (entry['belief'] or {}).get('contradicting_memory_ids',[]) if mid in indexed]
            for e in bundle:
                if e['memory_id'] not in seen:ordered.append(e);seen.add(e['memory_id'])
        selected=ordered
        output=[];dropped=[]
        for e in selected:
            item={'memory_id':e['memory_id'],'content':e['content'],'coverage':'FULL_SUPPLIED_CONTENT',
                'epistemic_kind':e['epistemic_kind'],'source_refs':e['source_refs'],'origin':e['iris']['origin'],
                'time':e['iris']['time'],'belief':e['belief'],'relation':e['iris']['relation']}
            if len(output)>=limit or len(canonical(output+[item]))>max_chars:dropped.append(e['memory_id'])
            else:output.append(item)
        return {'identity_id':identity_id,'items':output,'dropped_memory_ids':dropped,'context_chars':len(canonical(output)),
            'coverage':'SELECTED_CONTEXT','original_evidence_unchanged':True}


def shadow_compare(store,query,dataset_ids,important_keys):
    """Pure Iris-style lexical/legacy-confidence surrogate, not FAISS parity."""
    view=MemoryView(store);entries=view.entries(dataset_ids);tokens=set(re.findall(r'\w+',query.casefold()))
    matching=[e for e in entries if tokens&set(re.findall(r'\w+',e['content'].casefold()))]
    def old_confidence(e):
        score=e['iris']['legacy_confidence']
        return float(score) if isinstance(score,(int,float)) and not isinstance(score,bool) and 0<=score<=1 else 0.
    matching.sort(key=lambda e:(old_confidence(e),e['memory_id']),reverse=True)
    old=[]
    for e in matching:
        item={'memory_id':e['memory_id'],'content':e['content'],'coverage':'FULL_SUPPLIED_CONTENT',
            'epistemic_kind':e['epistemic_kind'],'source_refs':e['source_refs'],'origin':e['iris']['origin'],
            'time':e['iris']['time'],'belief':None,'relation':e['iris']['relation']}
        if len(old)<8 and len(canonical(old+[item]))<=8000:old.append(item)
    new=view.retrieve(query,identity_id=store.identity['identity_id'],dataset_ids=dataset_ids,max_chars=8000)
    old_keys={e['origin']['legacy_key'] for e in old};new_keys={e['origin']['legacy_key'] for e in new['items']}
    def metrics(items,keys,chars):
        return {'recall':len(set(important_keys)&keys)/len(important_keys) if important_keys else None,
            'provenance_completeness':sum(bool(e['source_refs']) for e in items)/len(items) if items else 1.,
            'temporal_relevance_known':sum((e.get('time') or e.get('iris',{}).get('time',{})).get('legacy_record_time_us') is not None for e in items),
            'contradictions_visible':sum(bool(e.get('belief') and e['belief']['contradicting_memory_ids']) for e in items),
            'unsupported_memory_rate':sum(e['memory_id'] not in {x['memory_id'] for x in entries} for e in items)/len(items) if items else 0.,
            'context_chars':chars,'dropped_important_keys':sorted(set(important_keys)-keys)}
    return {'scope':'pure synthetic comparison; old lexical/confidence surrogate, not actual Iris embedding retrieval',
        'identity_id':store.identity['identity_id'],'matched_bounds':{'max_chars':8000,'limit':8},'old':metrics(old,old_keys,len(canonical(old))),
        'core':metrics(new['items'],new_keys,new['context_chars']),'core_context':new,'production_runtime_parity':'NOT_RUN'}
