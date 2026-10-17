"""Bounded H1 qualification with generated public bytes and the existing runtime.

Only environment inputs/opportunities are scripted. C owns every judgment and
adopted goal; the existing F/G/I services own planning/learning/local skills.
"""
import argparse,json,os,resource,time
from pathlib import Path
from ..clock import Clock
from ..contracts import CoreError
from ..storage import canonical,digest
from ..continuity.world_loop.reference import open_runtime,configure,context_policy,codec_providers,capture
from ..continuity.world_loop.semantic_harness import semantic_harness,semantic_proposer
from ..continuity.world_loop.semantics import MediaSemanticService
from ..continuity.world_loop.perception import PerceptionService,PublicMediaSource
from ..continuity.world_loop.samples import media_samples
from ..continuity.world_loop.world import SourcedClaim
from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..continuity.memory import MemoryService
from ..continuity.records import RecordService
from ..continuity.autonomy.governance import GovernanceController,ManagerConstraint
from ..continuity.autonomy.contracts import RealizationTarget
from ..continuity.subject import SubjectInput
from .authority import VirtualClock
from .contracts import SECOND,HOUR,RuntimeEvent,Cause


def offer_from_semantics(r,source,key,hints):
    """Synthetic workload interpretation candidate, not a direct Goal insert."""
    memory=MemoryService(r.store);text=canonical({'semantic_source':source,'opportunities':hints,'proposal_not_truth':True});now=r.clock.utc_now_us()
    eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.h1-workload',source_reference=key,source_kind='MODEL_DERIVATION'),text=text,privacy_class='PUBLIC',observed_time_us=now))
    mid=memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.PROSPECTIVE,epistemic_kind='INFERENCE',source_evidence_id=eid,text=text,derived_from=(source,)))
    r.work.world.observe(mid);return mid


def perceive(r,data,modality,key):
    now=r.clock.utc_now_us();mid,_=PerceptionService(r.store,codec_providers(),context_policy()).ingest(data,PublicMediaSource(source_id=key,modality=modality,origin='SYNTHETIC',event_time_us=now,observed_time_us=now),entity_id='observer',scope='world')
    s=MediaSemanticService(r.work.world.cognition);cid=s.prepare(key,mid,data);out=s.execute(cid)
    if out['state']!='PROPOSED':raise CoreError('H1_DEMO_SEMANTICS_FAILED')
    result=s.ground(cid,entity_id='device',predicate='media.'+modality.lower());return mid,cid,result


def semantic_world(directory,*,variant=0,hours=48):
    if not 24<=hours<=96:raise CoreError('H1_DURATION_BOUND')
    root=Path(directory);path=root/'subject'/'self.db'
    if path.exists():raise CoreError('FRESH_DEMO_REQUIRED')
    clock=VirtualClock();start=clock.utc_now_us();checks={};trajectory=[];media={};source_ids=[]
    realm='synthetic://h1/captions' if not variant else 'synthetic://h1/notes'
    resources=tuple(realm+x for x in ('','/compute','/report'))+('synthetic://h1/optional','synthetic://skill/data','synthetic://skill/analysis')
    with semantic_harness() as (t,metrics),open_runtime(path,clock) as r:
        identity=r.identity_id;port=configure(r,root,t,resources)
        samples=media_samples(5 if variant else 0)
        for mod,data in samples.items():
            mid,cid,res=perceive(r,data,mod,mod.lower());media[mod]=res;source_ids.append(mid)
        semantic=media['IMAGE']['semantic_memory_ids'][0];label=json.loads(MemoryService(r.store).read(semantic)['text'])['semantic']['label']
        data=label.upper() if variant else label.replace(' ','\t');expected=label if variant else label.split()
        port.seed_observation(realm,data);port.seed_observation('synthetic://h1/optional',{'label':label})
        offer_from_semantics(r,semantic,'caption-work',[{'topic':'normalize','resource':realm,'method':'CASEFOLD' if variant else 'SPLIT_SPACE','expected':expected,'domain':'style' if variant else 'language','value':'HIGH','motive':'CREATIVE_INTEREST' if variant else 'COMPETENCE','possible_behaviors':['CREATE']},{'topic':'optional','resource':'synthetic://h1/optional','motive':'REST' if variant else 'CURIOSITY','value':'HIGH'}])
        controller=GovernanceController(r.store,r.authority)
        controller.install(ManagerConstraint(constraint_id='h1-window',revision=1,issuer=r.authority.principal,source_reference='synthetic.h1-governance',identity_id=identity,scope='world',targets=(RealizationTarget(capability='world.observe',resource='synthetic://h1/optional',resource_class='ORDINARY',operation='READ'),),effective_from_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+48*HOUR,reason_code='SYNTHETIC_WINDOW'),r.authority)
        for tick in range(hours*4):
            if tick==4:
                offer_from_semantics(r,semantic,'capability-need',[{'topic':'caption-normalizer','skill_task':'TEXT_CLEAN' if not variant else 'TOKEN_ANALYSIS','value':'HIGH','motive':'CAPABILITY_GAP'}])
            if tick==8:
                def alternate(req):
                    out=semantic_proposer(req)
                    if req.cognitive_role=='MEDIA':out=out.model_copy(update={'media':out.media.model_copy(update={'observations':(out.media.observations[0].model_copy(update={'label':'contradictory field'}),)})})
                    return out
                with semantic_harness(proposer=alternate) as (other,_):
                    from ..continuity.world_loop.cognition import CognitionSession
                    service=MediaSemanticService(CognitionSession(r,other,context_policy()))
                    cid=service.prepare('contradiction',source_ids[0],samples['IMAGE']);service.execute(cid);bad=service.ground(cid,entity_id='device',predicate='media.image')
                checks['semantic_conflict']=r.work.world.world.view('device','media.image.0').state=='CONFLICT'
            if tick==12:
                # Independent known generated target + actual pixel comparison;
                # never relabel the provider's own answer as verification.
                from PIL import Image
                import io
                expected_rgb=(170,80,160) if variant else (20,80,160)
                with Image.open(io.BytesIO(samples['IMAGE'])) as im:assert im.convert('RGB').getextrema()==tuple((v,v) for v in expected_rgb)
                verified_label='red-dominant field' if variant else 'blue-dominant field'
                original=SourcedClaim(entity_id='device',predicate='media.image.0',value={'kind':'ATTRIBUTE','label':verified_label,'span':[0.,0.],'region':None},kind='VERIFIED_RESULT',valid_from_us=start,corrects=bad['belief_ids'][0],confidence=1.,related_resources=(realm,))
                direct=capture(r,'independent-decoded-color-check',{'world_claim':original.model_dump(mode='json'),'independent_oracle':'GENERATED_TARGET_EXACT_PIXEL_COMPARISON'},kind='SYSTEM_VERIFICATION');r.work.world.observe(direct)
                checks['direct_correction']=r.work.world.world.view('device','media.image.0').state=='SUPPORTED_BELIEF'
            if tick==16:
                from ..continuity.world_loop.cognition import CognitionBudget
                service=MediaSemanticService(r.work.world.cognition);metrics['delay']=.2
                cid=service.prepare('timeout',source_ids[1],samples['AUDIO'],budget=CognitionBudget(timeout_ms=50));checks['timeout_unknown']=service.execute(cid)['state']=='UNKNOWN';metrics['delay']=0
            if tick==20:
                actions=len(r.store.all('actions'));controller.revoke('h1-window',expected_revision=1,authority=r.authority);checks['revoke_not_execution']=len(r.store.all('actions'))==actions
            if tick in (6,35):
                inp=SubjectInput(source_key='synthetic.h1.user.'+str(tick),kind='INTERACTION',origin='USER',entity_id='observer',scope='world',observed_at_us=clock.utc_now_us(),privacy_class='PUBLIC',text='Public fictional check-in')
                r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=identity),),due_at_us=clock.utc_now_us(),priority=3))
            for _ in range(30):
                clock.advance(SECOND);out=r.step()
                if out and out.get('cycle'):
                    c=out['cycle'];trajectory.append({'hour':tick/4,'cycle_id':c.cycle_id,'stance':c.judgment.stance,'behavior':c.intention.behavior,'intention':c.intention.kind})
                if out is None:break
            clock.advance(15*60*SECOND);r.lease.heartbeat(force=True)
        goals=r.store.all('goals');records=RecordService(r.store)
        def ancestry(rid):
            seen=set();pending=list(records.support(rid))
            while pending:
                mid=pending.pop()
                if mid in seen:continue
                seen.add(mid)
                if len(seen)>1024:raise CoreError('DEMO_LINEAGE_BOUND')
                pending.extend(row[0] for row in r.store.db.execute("SELECT parent_id FROM memory_dependencies WHERE memory_id=? AND parent_kind='MEMORY'",(mid,)))
            return seen
        semantic_in_goal=any(semantic in ancestry(json.loads(g['body_json'])['record_id']) for g in goals)
        checks.update({'semantic_support_reaches_adopted_goal':semantic_in_goal,'subject_can_no_action':any(t['intention']=='NO_ACTION' for t in trajectory),'C_owns_goals':all(g['goal_key'].startswith('open:') for g in goals),'skill_reuses_existing_lifecycle':bool(r.work.world.skills.active()),'learning_reuses_existing_lifecycle':bool(r.store.all('lessons')) if not variant else 'NOT_APPLICABLE_NO_FAILURE','F_replanned_after_checked_learning':any(g['version']>4 and g['state']=='COMPLETED' for g in goals) if not variant else 'NOT_APPLICABLE_NO_FAILURE','multiple_concerns':len(r.store.all('open_concerns'))>=2,'bounded_hot_state':len(r.store.all('open_concerns'))<=16 and len(r.subject.pending('world'))<=8})
        counts={'goals':len(goals),'completed_goals':sum(g['state']=='COMPLETED' for g in goals),'actions':len(r.store.all('actions')),'verified_actions':sum(a['state']=='SUCCEEDED' for a in r.store.all('actions')),'experiences':len(r.store.all('experiences')),'lessons':len(r.store.all('lessons')),'cycles':len(r.store.all('subject_cycles')),'http_calls':metrics['calls']}
        beliefs=[v.model_dump(mode='json') for v in r.work.world.world.snapshot()]
        blocks=[records.read(row['record_id'])['payload'] for row in r.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='CONSTRAINT_OUTCOME' AND lifecycle='ACTIVE'")]
        checks['manager_keeps_stage_provenance']=any(b['result']=='BLOCK' for b in blocks) if not variant else 'NOT_APPLICABLE_REST'
        MemoryService(r.store,r.authority).forget(source_ids[-1],r.authority)
        checks['source_delete_world_unknown']=r.work.world.world.view('device','media.video.0').state=='UNKNOWN'
        for mid in media['VIDEO']['semantic_memory_ids']:
            try:MemoryService(r.store).read(mid);checks['source_delete_world_unknown']=False
            except CoreError:pass
        # Export only the post-erasure projection, never the deleted summary.
        beliefs=[v.model_dump(mode='json') for v in r.work.world.world.snapshot()]
        checksum={'identity_id':identity,'goal_ids':[g['goal_id'] for g in goals]}
    with open_runtime(path,clock) as r:
        checks['restart_same_subject']=r.identity_id==identity and [g['goal_id'] for g in r.store.all('goals')]==checksum['goal_ids']
        checks['restart_no_handles']=r.work.world is None and r.work.agency is None
        checks['fk_clean']=not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
    return {'status':'OFFLINE_SYNTHETIC_SEMANTIC_HARNESS','variant':variant,'virtual_hours':round((clock.utc_now_us()-start)/HOUR,4),'checks':checks,'counts':counts,'media':media,'beliefs':beliefs,'trajectory':trajectory[-128:],'live_semantic_provider':'NOT_RUN','real_model_calls':0,'real_external_actions':0}


def semantic_wall(directory,seconds=300):
    if not 1<=seconds<=1800:raise CoreError('WALL_BOUND')
    root=Path(directory);path=root/'subject'/'self.db'
    if path.exists():raise CoreError('FRESH_DEMO_REQUIRED')
    started=time.monotonic();fds=len(os.listdir('/proc/self/fd'))
    with semantic_harness() as (t,state),open_runtime(path,Clock(),wall=True) as r:
        configure(r,root,t,('synthetic://public',),grant=False,planner=False);identity=r.identity_id
        media=[]
        for mod,data in media_samples().items():
            mid,cid,result=perceive(r,data,mod,'wall-'+mod.lower());media.append(result);r.work.world.observe(result['semantic_memory_ids'][0])
        r.run(seconds)
    with open_runtime(path,Clock(),wall=True) as r:
        health=r.health();counts={'beliefs':len(r.store.all('world_beliefs')),'cycles':len(r.store.all('subject_cycles')),'actions':len(r.store.all('actions'))}
        stable=r.identity_id==identity
    return {'actual_wall_seconds':round(time.monotonic()-started,3),'configured_runtime_seconds':seconds,'identity_stable':stable,'queue_depth':health.queue_depth,'fd_before':fds,'fd_after':len(os.listdir('/proc/self/fd')),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'http_calls':state['calls'],'counts':counts,'interpretations':{k:sum(len(m['semantic_memory_ids']) for m in media if m['predicate']=='media.'+k.lower()) for k in ('IMAGE','AUDIO','VIDEO')},'live_semantic_provider':'NOT_RUN','real_external_actions':0,'scope':'actual bounded Runtime.run with semantic sources; no Runtime/Scheduler/provider-worker changes'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--output',required=True);parser.add_argument('--variant',type=int,choices=(0,1),default=0);parser.add_argument('--hours',type=int,default=48);parser.add_argument('--wall-seconds',type=int);args=parser.parse_args()
    result=semantic_wall(args.directory,args.wall_seconds) if args.wall_seconds else semantic_world(args.directory,variant=args.variant,hours=args.hours)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':args.output,'checks':result.get('checks'),'counts':result.get('counts'),'actual_wall_seconds':result.get('actual_wall_seconds')}))
if __name__=='__main__':main()
