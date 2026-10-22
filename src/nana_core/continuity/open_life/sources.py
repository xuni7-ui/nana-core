"""Explicit owned source intake. No web discovery, ambient paths or credentials."""
import json,os,stat,urllib.request,urllib.parse
from pathlib import Path
from typing import Literal
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...storage import canonical,digest,uid
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..memory import MemoryService
from ..world_loop.world import WorldModel,SourcedClaim


def remember(runtime,key,body,*,scope,privacy,kind='DIRECT_OBSERVATION',parents=(),predicate=None):
    m=MemoryService(runtime.store);text=canonical(body)
    old=runtime.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference=?",('open-life:'+key,)).fetchone()
    eid=m.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT' if privacy=='PROJECT' else 'RECORDED_PUBLIC',source_namespace='recorded.project.material',source_reference='open-life:'+key,source_kind=kind),text=text,privacy_class=privacy,observed_time_us=old[0] if old else runtime.clock.utc_now_us()))
    prior=runtime.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(eid,)).fetchone()
    if prior:
        m.read(prior[0]);return prior[0] # tombstones fail closed, never recapture
    return m.add(MemoryCandidate(entity_id=runtime.config.entity_id,scope=scope,memory_type=MemoryType.EPISODIC,epistemic_kind='BELIEF' if kind=='MODEL_DERIVATION' else 'OBSERVATION',source_evidence_id=eid,text=text,derived_from=parents,predicate_key=predicate))


class IntakeSource(DTO):
    source_id:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    channel:Literal['LOCAL_FILE','OWNED_HTTP','STRUCTURED_FEED','MEDIA_METADATA','TRANSCRIPT','IMAGE_DESCRIPTOR']
    location:str=Field(min_length=1,max_length=512)
    privacy:Literal['PUBLIC','PROJECT']='PROJECT'
    max_bytes:int=Field(default=8192,ge=1,le=32768)
    semantic_format:Literal['OPAQUE','SOURCED_CLAIM_JSON']='OPAQUE'
    @model_validator(mode='after')
    def safe_location(self):
        if self.channel=='OWNED_HTTP':
            u=urllib.parse.urlsplit(self.location)
            if u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.username or u.password or u.fragment or u.query or '%' in u.path or '..' in u.path.split('/'):raise ValueError('explicit owned loopback URL required')
        elif self.location.startswith('/') or '..' in Path(self.location).parts or '\\' in self.location or '?' in self.location or '#' in self.location:raise ValueError('owned relative file required')
        return self


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class WorldIntake:
    def __init__(self,runtime,root,sources,*,scope):
        self.runtime=runtime;self.root=Path(root).resolve();self.scope=scope
        if scope not in runtime.config.scopes or len(sources)>16:raise CoreError('INTAKE_SCOPE_DENIED')
        self.sources={s.source_id:IntakeSource.model_validate_json(s.model_dump_json()) for s in sources}
        if len(self.sources)!=len(sources):raise CoreError('DUPLICATE_INTAKE_SOURCE')
    def read(self,source_id,*,observation_id='initial'):
        if source_id not in self.sources:raise CoreError('INTAKE_SOURCE_NOT_CONFIGURED')
        s=self.sources[source_id]
        if s.privacy not in self.runtime.config.privacy_classes:raise CoreError('INTAKE_PRIVACY_DENIED')
        if not isinstance(observation_id,str) or not 1<=len(observation_id)<=64:raise CoreError('INTAKE_OBSERVATION_ID_REQUIRED')
        group=digest([source_id,s.location])
        attempt='owned-intake:'+digest([group,observation_id])
        if s.channel=='OWNED_HTTP':
            store=self.runtime.store
            old=store.db.execute('SELECT * FROM jobs WHERE occurrence_key=?',(attempt,)).fetchone()
            if old:
                state=json.loads(old['body_json'])
                if old['state']!='DONE':raise CoreError('INTAKE_UNKNOWN_NO_RETRY')
                MemoryService(self.runtime.store).read(state['memory_id']);return state['memory_id']
            if store.db.execute("SELECT 1 FROM jobs WHERE work_kind='WORLD_INTAKE' AND state IN ('RUNNING','UNKNOWN') AND json_extract(body_json,'$.source_group')=? LIMIT 1",(group,)).fetchone():raise CoreError('INTAKE_UNKNOWN_NO_RETRY')
            if store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='WORLD_INTAKE' AND state IN ('RUNNING','UNKNOWN')").fetchone()[0]>=16:raise CoreError('INTAKE_UNRESOLVED_BOUND')
            # A killed process after this reservation is ambiguous. The default
            # occurrence never repeats HTTP. New observations need a new ID.
            jid=uid();now=self.runtime.clock.utc_now_us()
            with store.transaction('life.intake_reserved',{'occurrence':digest(attempt)}) as tx:
                tx.put('jobs',{'job_id':jid,'occurrence_key':attempt,'due_at_us':now,'state':'RUNNING','body_json':canonical({'source_group':group}),'work_kind':'WORLD_INTAKE','record_id':None,'revision':1,'cursor':0,'owner_epoch':self.runtime.lease.epoch,'updated_at_us':now})
            # Explicit 127.0.0.1 only; never use a proxy/redirect/Authorization.
            op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            try:
                with op.open(s.location,timeout=1) as response:
                    if response.status!=200:raise CoreError('INTAKE_HTTP_UNAVAILABLE')
                    raw=response.read(s.max_bytes+1)
            except OSError:
                with store.transaction('life.intake_unknown',{'occurrence':digest(attempt)}) as tx:tx.update('jobs',jid,state='UNKNOWN',revision=2,owner_epoch=None)
                raise CoreError('INTAKE_HTTP_UNKNOWN_NO_RETRY') from None
        else:
            # Open every directory with NOFOLLOW, not just a resolve-before-open.
            fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                parts=Path(s.location).parts
                if not parts:raise CoreError('INTAKE_PATH_DENIED')
                for part in parts[:-1]:
                    nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
                file=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
                with os.fdopen(file,'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise CoreError('INTAKE_REGULAR_FILE_REQUIRED')
                    raw=stream.read(s.max_bytes+1)
            except OSError:raise CoreError('INTAKE_PATH_DENIED') from None
            finally:os.close(fd)
        if len(raw)>s.max_bytes:raise CoreError('INTAKE_BYTE_BOUND')
        try:text=raw.decode('utf-8')
        except UnicodeError:raise CoreError('INTAKE_TEXT_ENCODING') from None
        body={'source_id':s.source_id,'channel':s.channel,'source_digest':digest(raw),'content':text,'observation':'BYTES_FROM_EXPLICIT_OWNED_SOURCE_NOT_WORLD_TRUTH'}
        mid=remember(self.runtime,'intake:'+digest([s.source_id,body]),body,scope=self.scope,privacy=s.privacy)
        if s.channel=='OWNED_HTTP':
            with store.transaction('life.intake_completed',{'occurrence':digest(attempt)}) as tx:tx.update('jobs',jid,state='DONE',revision=2,owner_epoch=None,body_json=canonical({'source_group':group,'memory_id':mid}))
        return mid

    def interpret(self,memory_id,claim):
        # Caller is an explicit semantic adapter; output is always derivation,
        # never a raw observation, regardless of parser/model confidence.
        from ..records import RecordService
        records=RecordService(self.runtime.store);m=records.memory.read(memory_id)
        source=json.loads(m['text'])
        provenance=m['source_provenance']
        if source.get('source_id') not in self.sources or m['scope']!=self.scope or source.get('channel')!=self.sources[source['source_id']].channel or provenance['source_kind']!='DIRECT_OBSERVATION' or m['authority']!='DIRECT' or provenance['source_namespace']!='recorded.project.material' or provenance['source_reference']!='open-life:intake:'+digest([source['source_id'],source]):raise CoreError('INTAKE_CORRELATION_DENIED')
        c=SourcedClaim.model_validate_json(claim.model_dump_json())
        if c.kind not in {'INTERPRETED','INFERENCE','MODEL_BELIEF'} or c.corrects:raise CoreError('INTAKE_SEMANTIC_ESCALATION')
        mid=remember(self.runtime,'semantic:'+digest([memory_id,c.model_dump(mode='json')]),{'world_claim':c.model_dump(mode='json'),'source_digest':source['source_digest'],'derivation_type':'MODEL_DERIVATION'},scope=m['scope'],privacy=m['privacy_class'],kind='MODEL_DERIVATION',parents=(memory_id,))
        model=WorldModel(self.runtime.store,scopes=(self.scope,),privacy_classes=self.runtime.config.privacy_classes)
        return mid,model.ingest(mid)
