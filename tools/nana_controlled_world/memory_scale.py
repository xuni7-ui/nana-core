"""Finite recorded PROJECT event retrieval, not private/human history."""
import argparse,json,time,statistics
from pathlib import Path
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import DAY
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.context import ContextAssembler,ContextRequest,ContextPolicy
from nana_core.contracts import CoreError


def run(root,count=2000):
    root=Path(root)
    if root.exists():raise ValueError('FRESH_MEMORY_SCALE_ROOT_REQUIRED')
    root.mkdir(mode=0o700,parents=True);clock=VirtualClock();start=time.monotonic()
    with open_runtime(root/'self.db',clock) as r:
        s=r.store;m=MemoryService(s,r.authority);now=clock.utc_now_us()
        def put(key,text,importance=.1,significance=0.,event=None,predicate=None,correction=None,derived=()):
            eid=m.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',source_namespace='recorded.project.material',source_reference='scale:'+key,source_kind='DIRECT_OBSERVATION'),text=text,privacy_class='PROJECT',event_time_us=event or now,observed_time_us=now))
            return m.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,importance=importance,significance=significance,predicate_key=predicate,correction_of=correction,derived_from=derived))
        high=put('important-old','migration recovery important shared project',1.,1.,now-60*DAY)
        old=put('corrected','project release version old',predicate='project.version')
        corrected=put('correction','project release version corrected',.9,.8,predicate='project.version',correction=old)
        withdrawn=put('withdrawn','migration revoked invalid support',.99,.9)
        derivative=put('derivative','migration derived invalid support',.9,.9,derived=(withdrawn,));m.forget(withdrawn,r.authority)
        for i in range(count):put('noise-'+str(i),'trivial tick '+str(i)+' irrelevant noise')
        recent=put('recent-relevant','migration recovery recent relevant project',.8,.8)
        policy=ContextPolicy(policy_id='scale',allowed_scopes=('world',),readable_privacy=('PROJECT',),remote_privacy=())
        request=ContextRequest(entity_id='observer',scopes=('world',),task_class='migration-review',task='Review sourced migration and current project version',task_privacy_class='PROJECT',query_terms=('migration','recovery','version'),max_input_tokens=8192,output_reserve_tokens=512)
        assembler=ContextAssembler(s,r.authority);times=[]
        for _ in range(5):
            t=time.perf_counter();package=assembler.assemble(request,policy);times.append((time.perf_counter()-t)*1000)
        selected={mid for b in package.blocks for mid in b.source_memory_ids}
        assert {high,recent,corrected}<=selected,{'high':high in selected,'recent':recent in selected,'corrected':corrected in selected,'blocks':[(b.kind,len(b.data_json)) for b in package.blocks],'tokens':package.manifest.input_tokens,'omitted':package.manifest.omitted_total}
        assert not {old,withdrawn,derivative}&selected
        assert package.manifest.retrieval_candidate_count<=128 and package.manifest.input_tokens<=request.max_input_tokens-request.output_reserve_tokens
        before=list(selected);m.rebuild_index();rebuilt=assembler.assemble(request,policy)
        assert {high,recent,corrected}<={mid for b in rebuilt.blocks for mid in b.source_memory_ids}
        counts={t:s.db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('events','artifacts','memories','memory_terms','record_dependencies')}
        # Controlled corruption in this disposable test Store only. The original
        # hash boundary must reject it before it can enter a ContextPackage.
        target=s.one('memories',high)['payload_artifact_id'];s.db.execute('UPDATE artifacts SET payload=? WHERE artifact_id=?',(b'corrupted derived payload',target))
        corrupt_denied=False
        try:m.read(high)
        except CoreError as exc:corrupt_denied=exc.code=='EVIDENCE_CORRUPT'
        assert corrupt_denied
        assert not s.db.execute('PRAGMA foreign_key_check').fetchall()
        result={'scope':'FINITE_OWNED_PROJECT_EVENTS_NOT_HUMAN_HISTORY','noise_events':count,'old_high_salience_selected':True,'recent_relevant_selected':True,'corrected_only_selected':True,'withdrawn_and_descendants_excluded':True,'trivial_candidates_bounded':True,'index_rebuild_stable':True,'corruption_rejected':corrupt_denied,'retrieval_ms':times,'retrieval_median_ms':statistics.median(times),'context_input_byte_estimate':package.manifest.input_tokens,'candidate_count':package.manifest.retrieval_candidate_count,'total_visible':package.manifest.retrieval_total_visible,'counts':counts,'db_family_bytes':sum(p.stat().st_size for p in root.glob('self.db*') if p.is_file()),'wall_seconds':time.monotonic()-start,'modified_corruption_copy':'DISPOSABLE_NOT_PORTABLE_SOURCE','provider_calls':0}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--count',type=int,default=2000);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not 100<=a.count<=10000:p.error('bounded100..10000')
    a.output.write_text(json.dumps(run(a.root,a.count),indent=2)+'\n')
if __name__=='__main__':main()
