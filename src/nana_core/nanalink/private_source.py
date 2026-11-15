"""Admit a verified account observation into the existing owner and memory.

The host must explicitly bind source, account, personal reading AND retention.
This adapter neither grants platform access nor decides whether C reads it.
"""
import json
from ..contracts import CoreError
from ..storage import canonical, digest
from ..continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from ..continuity.memory import MemoryService
from .contracts import Account, Event


class PlatformObservationAuthority:
    def __init__(self, app, channel_id, event):
        self.app, self.channel_id, self.event = app, channel_id, event

    def permits(self, store, candidate):
        try:
            app, e = self.app, self.event
            if app.runtime.store is not store or type(e) is not Event or e.kind != 'dynamic.created' or e.privacy != 'PERSONAL':
                return False
            channel = next(c for c in app.config.bilibili_channels if c.channel_id == self.channel_id)
            binding = app.surfaces._binding(channel.binding_id)
            from ..life.config import load_config
            current=load_config(app.home)
            live_channel=next(c for c in current.bilibili_channels if c.channel_id==channel.channel_id)
            live_binding=next(b for b in current.surface_bindings if b.binding_id==binding.binding_id)
            if channel != live_channel or binding != live_binding:
                return False
            account = Account(platform='bilibili',adapter_id='bilibili.account',account_id=str(channel.account_id))
            if (e.account != account or not channel.enabled or not channel.read_authorized
                    or not channel.private_read_authorized or not binding.allow_personal_retention
                    or not binding.personal_retention_consent_ref or 'PERSONAL' not in binding.permitted_privacy
                    or binding.platform != 'bilibili.account' or binding.mode != 'PLATFORM_ADAPTER_NO_SEND'):
                return False
            if e.origin != 'SYNTHETIC_LOOPBACK':
                from ..life.platform_authority import require_platform_authority
                require_platform_authority(app,channel.activation,channel='bilibili',exclusive_writer=False,
                                           account_id=channel.account_id)
            return (candidate.retention_consent_ref == binding.personal_retention_consent_ref
                    and candidate.provenance.source_reference == 'dynamic:'+e.key
                    and candidate.text == observation_text(e,channel,binding)
                    and candidate.event_time_us == e.occurred_at_us)
        except (CoreError,ValueError,StopIteration,AttributeError,TypeError):
            return False


def observation_text(event,channel,binding):
    return canonical({'schema_version':1,'platform':'bilibili','account_key':event.account.key,
        'channel_id':channel.channel_id,'binding_id':binding.binding_id,'event_id':event.event_id,
        'author_id':event.sender_id,'conversation_id':event.conversation_id,'occurred_at_us':event.occurred_at_us,
        'origin':event.origin,'source_digest':event.raw_sha256,'source_reference':event.raw_reference,
        'segments':[s.model_dump(mode='json') for s in event.segments], 'observation_not_user_command':True})


class PrivateDynamicBridge:
    def __init__(self, app, channel_id):
        self.app,self.channel_id=app,channel_id

    def receive(self,event):
        from ..continuity.subject.contracts import SubjectInput
        from ..continuity.extensions import SurfaceEnvelope
        from ..continuity.surfaces import source_key
        from ..presence.contracts import RuntimeEvent, Cause
        app=self.app;runtime=app.runtime;store=runtime.store
        channel=next((c for c in app.config.bilibili_channels if c.channel_id==self.channel_id),None)
        if channel is None:
            raise CoreError('PLATFORM_OBSERVATION_NOT_AUTHORIZED')
        binding=app.surfaces._binding(channel.binding_id)
        authority=PlatformObservationAuthority(app,self.channel_id,event)
        ref='dynamic:'+event.key
        previous=store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace=? AND source_reference=?",
                                  ('recorded.platform.bilibili.dynamic',ref)).fetchone()
        now=runtime.clock.utc_now_us()
        data=observation_text(event,channel,binding)
        candidate=EvidenceInput(provenance=Provenance(domain='CONSENTED_PLATFORM',source_namespace='recorded.platform.bilibili.dynamic',
             source_reference=ref,source_kind='DIRECT_OBSERVATION'),retention_consent_ref=binding.personal_retention_consent_ref,
             text=data,privacy_class='PERSONAL',event_time_us=event.occurred_at_us,observed_time_us=previous[0] if previous else now)
        memory=MemoryService(store,authority=authority)
        eid=memory.capture(candidate)
        mid=memory.add(MemoryCandidate(entity_id=binding.entity_id,scope=binding.scope,memory_type=MemoryType.EPISODIC,
                         epistemic_kind='OBSERVATION',source_evidence_id=eid,text=data))
        surface=SurfaceEnvelope(domain='LOCAL_INTERACTION',subject_id=runtime.identity_id,platform='bilibili.account',
              surface=binding.surface,adapter=binding.adapter,entity_id=binding.entity_id,conversation_id=event.conversation_id,
              session_id=binding.binding_id,event_kind=event.kind,occurred_at_us=event.occurred_at_us,observed_at_us=now,
              correlation_id=event.event_id,privacy_class='PERSONAL',source_reference='local:nanalink:bili:'+event.key,
              source_event_key=event.key)
        key=source_key(surface)
        old=store.db.execute('SELECT queue_id FROM runtime_queue WHERE source_key=?',(key,)).fetchone()
        if old:
            return {'state':'ALREADY_ADMITTED_NO_REPLAY','memory_id':mid,'queue_id':old[0]}
        inp=SubjectInput(domain='SOURCED_LIFE',source_key=key,kind='WAKE',origin='SELF_WAKE',entity_id=binding.entity_id,
                scope=binding.scope,observed_at_us=now,occurred_at_us=event.occurred_at_us,privacy_class='PERSONAL',
                source_memory_ids=(mid,),surface=surface)
        queue=runtime.submit(RuntimeEvent(event_type='WORLD_EVENT',trigger='ENVIRONMENT_CHANGE',input=inp,
                             causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=now))
        return {'state':'SOURCE_QUEUED_NOT_JUDGED','memory_id':mid,'queue_id':queue}

    def withdraw(self, event):
        """Use the ORIGINAL deletion closure; stable source remains tombstoned."""
        ref='dynamic:'+event.key
        row=self.app.runtime.store.db.execute("SELECT m.memory_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_namespace=? AND e.source_reference=? AND m.lifecycle!='DELETED'",
             ('recorded.platform.bilibili.dynamic',ref)).fetchone()
        if row:
            self.app.forget(row[0])
            return True
        return False


def poll_dynamics(workflow):
    """Owner-thread bounded source poll. Reserve before account or feed I/O."""
    from ..life.platform_runtime import reserve_inbound_read
    from .bilibili_dynamic import normalize_dynamic
    c=workflow.channel;app=workflow.app;store=workflow.store
    binding=app.surfaces._binding(c.binding_id)
    if (not c.enabled or not c.read_authorized or not c.private_read_authorized
            or not binding.allow_personal_retention or not binding.personal_retention_consent_ref):
        raise CoreError('PLATFORM_OBSERVATION_NOT_AUTHORIZED')
    workflow._authority()
    now=store.clock.utc_now_us();account=Account(platform='bilibili',adapter_id='bilibili.account',account_id=str(c.account_id))
    reservation=digest(['nanalink.dynamic',account.key,now//300000000])
    if store.db.execute("SELECT 1 FROM events WHERE source_namespace='platform.bilibili.ingress' AND source_key=?",(reservation,)).fetchone():
        return {'state':'ALREADY_POLLED_NO_RETRY','observations':0,'external_delivery':False}
    source='dynamic.'+c.channel_id
    count=store.db.execute("SELECT count(*) FROM events WHERE kind='platform.bilibili.ingress_reserved' AND recorded_at_us>=? AND json_extract(data_json,'$.data.channel_id')=?",(now-3600000000,source)).fetchone()[0]
    if count>=12:
        raise CoreError('BILIBILI_DYNAMIC_HOURLY_CEILING')
    reserve_inbound_read(workflow.realization.kernel,2,'bilibili',source,reservation)
    workflow.transport.calls=0;workflow.transport.account();rows=workflow.transport.dynamic_rows()
    bridge=PrivateDynamicBridge(app,c.channel_id);admitted=0;retired=0
    for row in rows:
        event=normalize_dynamic(account,row,now_us=now,origin=workflow.transport.realm)
        if event is None:
            continue
        try:
            bridge.receive(event);admitted+=1
        except CoreError as exc:
            if exc.code not in {'SOURCE_DELETED','MEMORY_UNAVAILABLE'}:
                raise
            retired+=1
    return {'state':'SOURCES_QUEUED_NOT_JUDGED','observations':admitted,'retired':retired,
            'coverage':'LATEST_PAGE_20_NO_HISTORY_GUARANTEE','external_delivery':False,'model_calls':0}


def reconcile_revoked_sources(app, config):
    """Withdraw original memory dependency closures when host consent is gone."""
    store=app.runtime.store
    channels={c.channel_id:c for c in config.bilibili_channels}
    bindings={b.binding_id:b for b in config.surface_bindings}
    removed=0
    def rows_in_pages():
        cursor=0
        while True:
            rows=store.db.execute("SELECT m.rowid AS source_row,m.memory_id,e.payload_artifact_id FROM memories m JOIN continuity_evidence e ON m.source_evidence_id=e.evidence_id WHERE e.source_namespace='recorded.platform.bilibili.dynamic' AND m.lifecycle!='DELETED' AND m.rowid>? ORDER BY m.rowid LIMIT 128",(cursor,)).fetchall()
            if not rows:
                return
            cursor=rows[-1]['source_row']
            yield from rows
    for row in rows_in_pages():
        current=store.one('memories',row['memory_id'])
        if not current or current['lifecycle']=='DELETED':
            continue
        payload=json.loads(store.artifact(row['payload_artifact_id']))
        observation=json.loads(payload['text']);channel=channels.get(observation['channel_id'])
        binding=bindings.get(observation['binding_id'])
        if channel is None or binding is None:
            invalid=True
        else:
            account=Account(platform='bilibili',adapter_id='bilibili.account',account_id=str(channel.account_id))
            invalid=(not channel.read_authorized or not channel.private_read_authorized
                 or channel.binding_id!=binding.binding_id or observation['account_key']!=account.key
                 or not binding.enabled or not binding.allow_personal_retention
                 or not binding.personal_retention_consent_ref
                 or payload.get('retention_consent_ref')!=binding.personal_retention_consent_ref
                 or binding.platform!='bilibili.account' or 'PERSONAL' not in binding.permitted_privacy)
        if invalid:
            app.forget(row['memory_id']);removed+=1
    return removed
