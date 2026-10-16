"""Surface adapters feed the existing SubjectLoop; tiers are reference views.

No transport, new event bus or payload cache. Metadata is dependency-bound to the
same deletable Subject record. Identity binding is checked before ingestion.
"""
import json
from typing import Literal
from pydantic import Field
from ..contracts import CoreError, DTO
from ..storage import digest
from .extensions import SurfaceEnvelope
from .context import ContextPolicy
from .records import RecordService
from .memory import MemoryService
from .revision import state_token
from .subject.contracts import SubjectInput


def source_key(envelope):
    return 'synthetic.surface.' + digest([envelope.platform, envelope.adapter,
        envelope.surface, envelope.source_event_key])

def surface_input(envelope,event,*,identity_id):
    envelope=SurfaceEnvelope.model_validate_json(envelope.model_dump_json())
    if envelope.subject_id!=identity_id:raise CoreError('SURFACE_SUBJECT_MISMATCH')
    event=event.model_copy(update={'surface':envelope,'source_key':source_key(envelope)})
    return SubjectInput.model_validate_json(event.model_dump_json())

class SurfaceIngress:
    def __init__(self, subject_loop):
        self._subject = subject_loop

    def submit(self, envelope: SurfaceEnvelope, event: SubjectInput):
        event=surface_input(envelope,event,identity_id=self._subject.store.identity['identity_id'])
        return self._subject.run(event)

class ContinuityTier(DTO):
    derived: Literal[True] = True
    tier: Literal['L0_LIVE','L1_RECENT','L2_DURABLE']
    subject_id: str
    entity_id: str
    as_of_us: int
    state_token: str
    source_event_ids: tuple[str, ...] = ()
    source_record_ids: tuple[str, ...] = ()
    source_memory_ids: tuple[str, ...] = ()
    commitment_ids: tuple[str, ...] = ()
    project_ids: tuple[str, ...] = ()
    intention_ids: tuple[str, ...] = ()
    goal_candidate_ids: tuple[str, ...] = ()
    latest_cycle_record_ids: tuple[str, ...] = ()
    surfaces: tuple[SurfaceEnvelope, ...] = ()
    recorded_at_us: tuple[int, ...] = ()
    coverage: Literal['BOUNDED_PROJECTION_NOT_FULL_HISTORY'] = 'BOUNDED_PROJECTION_NOT_FULL_HISTORY'

class ContinuityViews:
    def __init__(self, store, policy: ContextPolicy):
        self._store, self._policy = store, policy

    def project(self, tier, *, entity_id, scopes, destination='LOCAL_FIXTURE', limit=32):
        if tier not in {'L0_LIVE','L1_RECENT','L2_DURABLE'} or type(limit) is not int or not 1 <= limit <= 128:
            raise CoreError('CONTINUITY_VIEW_REQUEST_INVALID')
        if destination not in {'LOCAL_FIXTURE','DEVELOPMENT_REMOTE'} or not scopes or not set(scopes) <= set(self._policy.allowed_scopes):
            raise CoreError('CONTINUITY_VIEW_SCOPE_DENIED')
        privacy=tuple(p for p in self._policy.readable_privacy if destination=='LOCAL_FIXTURE' or p in self._policy.remote_privacy)
        self._store.ensure_privacy_current()
        token=state_token(self._store)
        records=RecordService(self._store)
        def visible(rid):
            row=self._store.one('continuity_records',rid)
            return bool(row and row['scope'] in scopes and row['privacy_class'] in privacy
                and row['lifecycle']=='ACTIVE' and records.current_support(rid))
        events=[]; rids=[]; surfaces=[]; times=[]
        # Header filters precede payload parsing. Bounded query by entity/scopes.
        sql=('SELECT e.* FROM subject_events e JOIN continuity_records r ON r.record_id=e.record_id '
             f"WHERE e.entity_id=? AND e.scope IN ({','.join('?' for _ in scopes)}) "
             'ORDER BY e.ingested_at_us DESC,e.rowid DESC LIMIT ?')
        for raw in self._store.db.execute(sql,(entity_id,*scopes,limit)):
            row=dict(raw)
            if not visible(row['record_id']):continue
            events.append(row['subject_event_id']);rids.append(row['record_id'])
            payload=records.read(row['record_id'])['payload']
            env=payload.get('input',{}).get('surface')
            if env:
                surfaces.append(SurfaceEnvelope.model_validate_json(json.dumps(env)))
                times.append(row['ingested_at_us'])
        commitments=[];projects=[];intentions=[];goals=[];cycles=[]
        for table, key, states, out in (
            ('commitments','commitment_id',('ADOPTED','ACTIVE'),commitments),
            ('projects','project_id',('ACTIVE','PAUSED'),projects),
            ('subject_intentions','intention_id',('PENDING','DEFERRED'),intentions)):
            for row in self._store.db.execute(f"SELECT * FROM {table} WHERE scope IN ({','.join('?' for _ in scopes)}) ORDER BY rowid DESC LIMIT ?",(*scopes,limit)):
                if 'entity_id' in row.keys() and row['entity_id']!=entity_id:continue
                if table=='subject_intentions':
                    source=self._store.one('subject_events',row['subject_event_id'])
                    if not source or source['entity_id']!=entity_id or row['expires_at_us']<=self._store.clock.utc_now_us():continue
                if row['state'] in states and visible(row['record_id']):
                    out.append(row[key]);rids.append(row['record_id'])
        for row in self._store.db.execute(f"SELECT c.record_id FROM subject_cycles c JOIN subject_events e ON e.subject_event_id=c.subject_event_id WHERE e.entity_id=? AND e.scope IN ({','.join('?' for _ in scopes)}) ORDER BY c.revision DESC LIMIT ?",(entity_id,*scopes,limit)):
            if visible(row[0]):cycles.append(row[0])
        for row in self._store.db.execute(f"SELECT g.* FROM subject_goal_candidates g JOIN subject_intentions i ON i.intention_id=g.intention_id JOIN subject_events e ON e.subject_event_id=i.subject_event_id WHERE e.entity_id=? AND e.scope IN ({','.join('?' for _ in scopes)}) AND g.state IN ('PROPOSED','DEFERRED') AND i.expires_at_us>? ORDER BY g.rowid DESC LIMIT ?",(entity_id,*scopes,self._store.clock.utc_now_us(),limit)):
            if visible(row['record_id']):goals.append(row['candidate_id']);rids.append(row['record_id'])
        memories=()
        if tier!='L0_LIVE':
            memories=tuple(m['memory_id'] for m in MemoryService(self._store).query(
                entity_ids=(entity_id,self._store.identity['identity_id']),scopes=scopes,
                privacy_classes=privacy,limit=limit))
        if tier=='L2_DURABLE':
            # Narrative/assertion history is a view over existing, deletable records.
            for raw in self._store.db.execute(f"SELECT record_id FROM continuity_records WHERE scope IN ({','.join('?' for _ in scopes)}) AND record_kind IN ('REFLECTION','LESSON','ASSERTION','SUBJECT_BOOTSTRAP','EXPERIENCE') ORDER BY created_at_us DESC LIMIT ?",(*scopes,limit)):
                if visible(raw[0]):rids.append(raw[0])
        if token!=state_token(self._store):raise CoreError('CONTINUITY_VIEW_STALE')
        return ContinuityTier(tier=tier,subject_id=self._store.identity['identity_id'],entity_id=entity_id,
            as_of_us=self._store.clock.utc_now_us(),state_token=token,source_event_ids=tuple(events),
            source_record_ids=tuple(dict.fromkeys(rids)),source_memory_ids=memories,
            commitment_ids=tuple(commitments),project_ids=tuple(projects),intention_ids=tuple(intentions),
            goal_candidate_ids=tuple(goals),latest_cycle_record_ids=tuple(cycles),
            surfaces=tuple(surfaces),recorded_at_us=tuple(times))
