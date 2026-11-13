"""Manual owned-HTTP comparison; never a real-provider or installation claim."""
import argparse,json
from pathlib import Path
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.autonomy.private_intent import candidates
from tests.first_life_integration.test_private_intent import _private_d_fixture
from tests.person_self.test_provider_subject_runtime import proposer,bind


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('legacy-slot','bound'),required=True)
    parser.add_argument('--root',required=True);parser.add_argument('--report',required=True)
    args=parser.parse_args();root=Path(args.root).absolute();report_path=Path(args.report).absolute()
    if root.exists() or root.is_symlink() or root.resolve()!=root or root.parent not in {Path('/dev/shm'),Path('/tmp')}:
        raise SystemExit('fresh direct /tmp or /dev/shm root required')
    if report_path.exists() or report_path.is_symlink() or report_path.resolve()!=report_path or report_path.parent not in {Path('/dev/shm'),Path('/tmp')}:
        raise SystemExit('fresh direct /tmp or /dev/shm report required')
    root.mkdir(mode=0o700);clock=VirtualClock();runtime,rid,plan=_private_d_fixture(root,clock)
    with provider_harness(proposer=proposer) as (transport,state),runtime as r:
        if args.mode=='legacy-slot':
            # Isolated baseline only: the old host has no provider binding. Its
            # existing port injection retains the fixture reservation as well.
            policy=ContextPolicy(policy_id='provider-normal-d',allowed_scopes=('own-scope',),readable_privacy=('PROJECT',))
            session=CognitionSession(r,transport,policy,max_calls_per_day=r.config.max_calls_per_day)
            r.cognition.port=lambda call:session.subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=32768))
        else:bind(r,transport)
        clock.advance(3*SECOND);r.refresh_attention()
        for _ in range(4):r.step()
        assert state['calls']==1
        private=candidates(r.store,'own-scope',('PROJECT',))
        assert any('negative space' in value.content_summary for _,value in private)
        report={'mode':args.mode,'provider_calls':state['calls'],'provider_ledger_rows':len(r.store.all('cognitive_requests')),
            'fixture_ledger_rows':len(r.store.all('runtime_cognition_calls')),'same_c_question_formed':True,
            'actions':len(r.store.all('actions')),'grants':len(r.store.all('grants')),'real_model_calls':0,
            'runtime_config':r.config.model_dump(mode='json'),
            'source_module':__import__('nana_core.presence.runtime',fromlist=['NanaRuntime']).__file__,
            'limit':'Legacy slot injection is an isolated diagnostic, not a supported production integration. Fresh equivalent DEV stores; no binary migration/installation or real-model quality/cost comparison.'}
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ('mode','provider_calls','provider_ledger_rows','fixture_ledger_rows','same_c_question_formed')}))


if __name__=='__main__':main()
