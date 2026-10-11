"""One bounded operator-authorized public research card, never retry UNKNOWN."""
import json
from pathlib import Path
from ..actions import ActionKernel,OperatorAuthority
from ..clock import Clock
from ..contracts import CAPABILITIES,GrantSpec,Observation,VERIFY_CAPABILITY
from ..development.public_http import PublicHTTPTransport,WebSpec
from ..development.web_source import WebSourcePort
from ..development.web_lab import cite_completed_goal
from ..fake_world import FakeWorld
from ..migration.routing import CapabilityRouter
from ..planning import FixtureModel
from ..runtime import Runtime
from ..storage import Store


def run(output):
    root=Path(output);root.mkdir(parents=True,exist_ok=False)
    source='source://public/phase3/example';card='notebook://synthetic/phase3/public-card'
    clock,authority=Clock(),OperatorAuthority('phase3-public-read-operator')
    with Store(root/'core.db',clock) as store:
        world=FakeWorld(root/'world.db')
        try:
            transport=PublicHTTPTransport()
            port=WebSourcePort(store,{source:WebSpec(url='https://example.com/',timeout_seconds=5)},world,authority,transport)
            router=CapabilityRouter(store,{c:world if c=='reading.card.create' else port for c in CAPABILITIES},authority,resource_scope='development_public')
            router.select_owner('core_simulator',authority)
            kernel=ActionKernel(store,router.bind('core_simulator',authority),authority)
            kernel.set_budgets({'write_attempts':1,'external_requests':8,'cost_micro_units':8},authority)
            kernel.grant(GrantSpec(capabilities=tuple(sorted(CAPABILITIES|{VERIFY_CAPABILITY})),resources=(source,card),
                not_before_us=clock.utc_now_us(),expires_at_us=clock.utc_now_us()+60_000_000),authority)
            goal=Runtime(store,kernel,FixtureModel()).process(Observation(source_namespace='synthetic.phase3.public',
                object_id='one-public-research',raw_text='Read the approved public Example Domain page and preserve a sourced private card.',
                occurred_at='2026-10-11T00:00:00Z',source_id=source,card_resource=card))
            actions=store.all('actions');read=next(a for a in actions if a['capability']=='reading.source.read')
            result=json.loads(read['result_json']) if read['result_json'] else None
            return {'scope':'one actual public capability attempt; deterministic planning; fake notebook','URL':'https://example.com/',
                'last_stage':transport.last_stage,'safe_error':port.last_error,'http_attempts':transport.http_requests,
                'proxy_connection_attempts':transport.proxy_connections,'identity':store.identity,'goal_state':store.one('goals',goal)['state'],
                'read_state':read['state'],'action_id':read['action_id'],'attempts':store.all('attempts'),
                'receipt_event_id':next((a['receipt_event_id'] for a in store.all('attempts') if a['kind']=='EXECUTE'),None),
                'verification_event_id':json.loads(read['body_json']).get('verification_event_id'),
                'HTTP_status':result['status'] if result else None,'raw_content_hash':result['source_blob_sha256'] if result else None,
                'summary_hash':__import__('hashlib').sha256(result['text'][:240].encode()).hexdigest() if result else None,
                'cited_result':cite_completed_goal(store,goal),'public_gate':'PASS' if read['state']=='SUCCEEDED' and result['transport_evidence']['public_fetch'] else 'BLOCKED',
                'automatic_retries':0,'real_model_calls':0,'production_calls':0,'fees':0}
        finally:world.close()
