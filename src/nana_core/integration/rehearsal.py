"""Synthetic cloud wiring rehearsal; no production runtime, model or network."""
import argparse
import json
import os
from pathlib import Path
from ..storage import Store,canonical
from ..migration.iris_fixtures import fixtures
from .contracts import HostEvent,RuntimeIntegrationContext
from .exporter import bundle
from .shadow import ShadowBridge,ShadowDecision,ProposedHostAction,reconcile,human_report

def run(directory):
    p=Path(directory);p.mkdir(parents=True,exist_ok=True)
    rows=[(r.kind,r.legacy_key,json.loads(r.raw_json)) for r in fixtures()]
    frozen=p/'frozen_synthetic_export.json'
    if frozen.exists():export=json.loads(frozen.read_text())
    else:
        export=bundle(rows,'synthetic:host-iris');frozen.write_text(canonical(export))
    event=HostEvent(host_instance='synthetic-host',platform='qq',channel='group',sender_id='synthetic-sister',event_id='message-1',
        conversation_id='synthetic-chat',content='Fictional research request',raw_content_reference='synthetic://host/message-1')
    with Store(p/'shadow.db') as s:
        identity=s.identity;ctx=RuntimeIntegrationContext(host_instance=event.host_instance,expected_identity_id=identity['identity_id'])
        b=ShadowBridge(s,ctx);source=b.capture_export(export)
        d=ShadowDecision(interpretation='Fictional research observation',evidence_event_ids=(source,),goal_purpose='Consider reading',
            planned_actions=(ProposedHostAction(capability='reading.source.read',resource='source://synthetic/paper',reason='Need source evidence'),),rationale='Await permission; never execute in shadow')
        result=b.observe(event,d);before=s.snapshot()
        reconciliation=reconcile(result['observation_event_id'],d,d,important_evidence=(source,))
        assert s.snapshot()==before
    with Store(p/'shadow.db') as s:
        b=ShadowBridge(s,ctx);assert s.identity==identity and b.observe(event,d)==result and b.capture_export(export)==source
        invariant={t:len(s.all(t)) for t in ('actions','attempts','budgets','grants','strategies','goals','plans')}
    assert all(n==0 for n in invariant.values())
    report={'status':'PASS','scope':'synthetic host event and hash-only Iris export; fixture decision; not cloud integration',
        'pid':os.getpid(),'same_identity':True,'duplicate_after_restart':True,'export_record_count':14,'zero_execution_tables':invariant,
        'production_calls':0,'real_model_calls':0,'external_messages':0,'E12':'NOT_RUN','reconciliation':reconciliation}
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('directory');a=p.parse_args();r=run(a.directory);print(canonical(r))
if __name__=='__main__':main()
