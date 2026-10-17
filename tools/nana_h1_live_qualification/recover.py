"""Keyless local checks of accepted public relay replies; never provider calls."""
import argparse,json
from pathlib import Path
from PIL import Image
import io
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.cognition import CognitionSession
from nana_core.continuity.world_loop.semantics import MediaSemanticService,OpenAIMediaTransport
from nana_core.continuity.world_loop.semantic_contracts import SemanticDescriptor
from nana_core.continuity.world_loop.reference import open_runtime,context_policy,capture
from nana_core.continuity.world_loop.world import WorldModel,SourcedClaim
from nana_core.continuity.subject import SubjectInput
from nana_core.presence.authority import VirtualClock
from .fixtures import cases
from .run import local_payload_guards,ground_to_subject

class NoNetwork:
    def __init__(self):self.calls=0
    def open(self,*args,**kwargs):self.calls+=1;raise CoreError('KEYLESS_RECOVERY_NETWORK_DENIED')

def run(directory,evidence):
    rows=json.loads((evidence/'live_calls.json').read_text());accepted=[x for x in rows if x['state']=='PROPOSED'];assert accepted
    desc=SemanticDescriptor(provider_id='tiantoken.qualification',model_id='qwen3.8-flash',modalities=('IMAGE','VIDEO'),max_input_bytes=98304)
    t=OpenAIMediaTransport('https://api.tiantoken.com/v1/chat/completions','qwen3.8-flash',provider_id=desc.provider_id,descriptor=desc)
    network=NoNetwork();t.opener=network
    fixture={x['source_sha256']:x for x in cases(directory/'recovery-fixtures',contrast=True)}
    with open_runtime(directory/'subject/self.db',VirtualClock()) as r:
        s=MediaSemanticService(CognitionSession(r,t,context_policy()));identity=r.identity_id
        # Reconstruct accepted historical beliefs after a different interpreter
        # process, with no key and a transport that cannot perform network IO.
        ids=[]
        for row in accepted:
            cid=row['request_id'];assert s.execute(cid)['replayed']
            if r.store.one('memories',row['source_memory_id'])['lifecycle']=='DELETED':continue
            result=s.ground(cid,entity_id='device',predicate=row['grounding']['predicate'])
            assert result==row['grounding'];ids.extend(result['belief_ids'])
        prior=r.store.db.execute('SELECT * FROM subject_cycles ORDER BY rowid LIMIT 1').fetchone()
        if prior and r.store.one('continuity_records',prior['record_id'])['lifecycle']!='ACTIVE':
            subject={'cycle_id':prior['cycle_id'],'judgment':prior['judgment'],'attention':prior['attention'],'barrier':prior['barrier'],'subject_can_choose_no_action':prior['barrier']=='NO_ACTION','detail':'Derived input/intention body erased with source; opaque audit columns only, no resurrection.'}
        else:subject=ground_to_subject(r,accepted[0]['grounding']['semantic_memory_ids'][0])
        # Independently known rendered text plus measured foreground pixel bounds
        # refines an incomplete MODEL_BELIEF region, not an alleged wrong OCR.
        textrow=next(x for x in accepted if x['case_id']=='text');raw=fixture[textrow['source_sha256']]['bytes']
        im=Image.open(io.BytesIO(raw)).convert('RGB');points=[(x,y) for y in range(im.height) for x in range(im.width) if max(im.getpixel((x,y)))<128]
        assert points;bounds=[min(x for x,y in points)/im.width,min(y for x,y in points)/im.height,(max(x for x,y in points)+1)/im.width,(max(y for x,y in points)+1)/im.height]
        old=textrow['grounding']['belief_ids'][0];world=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',))
        claim=SourcedClaim(entity_id='device',predicate=textrow['grounding']['predicate']+'.0',kind='RAW_OBSERVATION',value={'kind':'TEXT_REGION','label':'ORBIT 27','span':[0.,0.],'region':bounds},confidence=1.,corrects=old,valid_from_us=r.clock.utc_now_us())
        existing=r.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_reference='independent.rendered.text.bounds'").fetchone()
        correction=existing[0] if existing else capture(r,'independent.rendered.text.bounds',{'world_claim':claim.model_dump(mode='json'),'method':'Known generator ORBIT 27; independently measured black foreground bounds','source_byte_digest':textrow['source_sha256']})
        world.ingest(correction);view=world.view('device',textrow['grounding']['predicate']+'.0');assert r.store.one('world_beliefs',old)['state']=='SUPERSEDED' and view.state in {'SUPPORTED_BELIEF','CONFLICT'}
        correction_proof={'method':'Independent deterministic generator/actual pixel bounds','region':bounds,'old_model_belief_id':old,'correction_memory_id':correction,'current_view':view.model_dump(mode='json'),'scope':'Refines missing precise region. No factual OCR error claimed. Original response provenance retained. Existing repeat replies placed different observation kinds at ordinal0; this caller binding leaves an explicit CONFLICT, not a forced truth winner. Future qualification calls use per-request predicates.'}
        first=accepted[0]
        if r.store.db.execute("SELECT 1 FROM cognitive_requests WHERE request_key='media:local-deleted'").fetchone():
            guards={k:r.store.db.execute('SELECT state FROM cognitive_requests WHERE request_key=?',('media:local-'+v,)).fetchone()[0] for k,v in [('correlation','correlation'),('model_identity','model_identity'),('authority_fields','authority'),('stale','stale'),('interrupted','interrupted'),('deleted','deleted')]}
            assert guards=={'correlation':'REJECTED','model_identity':'REJECTED','authority_fields':'REJECTED','stale':'STALE','interrupted':'UNKNOWN','deleted':'STALE'}
        else:guards=local_payload_guards(r,s,first['request_id'],first['source_memory_id'],fixture[first['source_sha256']]['bytes'])
        assert all(r.store.one('memories',m)['lifecycle']=='DELETED' for m in first['grounding']['semantic_memory_ids'])
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        cycles=len(r.store.all('subject_cycles'));eventrow=r.store.db.execute('SELECT e.source_key FROM subject_events e JOIN subject_cycles c ON e.subject_event_id=c.subject_event_id WHERE c.cycle_id=?',(subject['cycle_id'],)).fetchone()
        event=SubjectInput(source_key=eventrow[0],kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',source_memory_ids=(first['grounding']['semantic_memory_ids'][0],),observed_at_us=r.clock.utc_now_us())
        assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
    with open_runtime(directory/'subject/self.db',VirtualClock()) as r:
        ss=MediaSemanticService(CognitionSession(r,t,context_policy()));ss.session.recover()
        assert r.identity_id==identity
        for row in rows:
            assert ss.execute(row['request_id'])['replayed']
        try:r.subject.run(event);raise AssertionError('erased source event revived')
        except CoreError:pass
        assert len(r.store.all('subject_cycles'))==cycles
        try:ss.ground(accepted[0]['request_id'],entity_id='device',predicate=accepted[0]['grounding']['predicate']);raise AssertionError('deleted source revived')
        except CoreError:pass
        assert network.calls==0
        counts={'actions':len(r.store.all('actions')),'grants':len(r.store.all('grants')),'goals':len(r.store.all('goals')),'subject_cycles':len(r.store.all('subject_cycles')),'business_tables':r.store.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]}
    result={'status':'PASS','subject':subject,'guards':guards,'stronger_evidence':correction_proof,'separate_process_reopen':True,'same_identity':True,'no_duplicate_judgment':True,'no_duplicate_provider_call_on_restart':True,'deleted_source_not_revived':True,'counts':counts,'real_provider_calls_in_this_command':0,'calling_cut':'CONTROLLED_LOCAL_STATE, NOT_A_LIVE_CALL_INTERRUPTION','authority_attack':'LOCAL_MUTATION_OF_REAL_REPLY, not completed live visual injection'}
    (evidence/'local_recovery_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','counts':counts,'network_calls':network.calls}))

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();run(a.directory,a.evidence)
if __name__=='__main__':main()
