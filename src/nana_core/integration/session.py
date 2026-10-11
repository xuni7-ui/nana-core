"""Bounded host embedding; no persistent second runtime or privileged repair."""
import json
from ..contracts import CoreError
from ..storage import canonical,digest
from .shadow import ShadowBridge

class HostShadowSession:
    def __init__(self,bridge,*,allowed_conversations,expires_at_us,max_events=1):
        if not isinstance(bridge,ShadowBridge) or type(max_events)!=int or not 1<=max_events<=100:raise CoreError('SHADOW_SESSION_BOUND_REQUIRED')
        if not allowed_conversations:raise CoreError('SHADOW_CONVERSATION_ALLOWLIST_REQUIRED')
        self.bridge=bridge;self.allowed=frozenset(allowed_conversations);self.expires_at_us=expires_at_us;self.max_events=max_events
        self.key='cloud.shadow_session:'+digest([bridge.context.model_dump(),sorted(self.allowed),expires_at_us])
    def observe(self,event,decision):
        s=self.bridge.store
        if (event.platform,event.conversation_id) not in self.allowed:raise CoreError('SHADOW_EVENT_OUT_OF_SCOPE')
        if type(self.expires_at_us)!=int or s.clock.utc_now_us()>=self.expires_at_us:raise CoreError('SHADOW_WINDOW_EXPIRED')
        state=s.one('core_meta',self.key);state=json.loads(state['value_json']) if state else {'event_keys':[]}
        ek=digest([event.host_instance,event.platform,event.conversation_id,event.event_id,event.revision])
        if ek not in state['event_keys'] and len(state['event_keys'])>=self.max_events:raise CoreError('SHADOW_EVENT_LIMIT')
        # Reserve before ingest. Crash can consume a slot, not allow extra private
        # events. Exact redelivery remains permitted and Bridge is idempotent.
        if ek not in state['event_keys']:
            state['event_keys'].append(ek)
            with s.transaction('cloud.shadow_event_reserved',{'event_key':ek}) as tx:
                tx.put('core_meta',{'key':self.key,'value_json':canonical(state)})
        return self.bridge.observe(event,decision)

def shadow_health(store):
    return {'mode':'SHADOW','identity_id':store.identity['identity_id'],'identity_revision':store.identity['revision'],
        'external_execute':False,'production_budget_enabled':False,
        'store_quick_check':store.db.execute('PRAGMA quick_check').fetchone()[0],
        'action_count':len(store.all('actions')),'active_goals':sum(g['state'] in {'PROPOSED','ACTIVE','BLOCKED'} for g in store.all('goals'))}
