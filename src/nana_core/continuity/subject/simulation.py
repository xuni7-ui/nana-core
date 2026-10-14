"""Synthetic life through production candidate modules, never real-world proof.

Input schedule is a fixture. The decisions, memory admission, source tracking,
preference formation, reflection and projections are the actual Core modules.
No day number or expected answer is passed to SubjectLoop/policy.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from ...actions import OperatorAuthority
from ...clock import ManualClock
from ...storage import canonical, digest
from ..store import ContinuityStore
from ..identity import IdentityService
from ..memory import MemoryService
from ..contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
from ..commitments import CommitmentCandidate, CommitmentService
from ..projects import ProjectContent, ProjectService
from ..context import ContextAssembler, ContextPolicy, ContextRequest
from ..cognition import AnalyticalFixturePort, CautiousFixturePort, DeliberationSession
from ..learning import ExperienceInput, ExperienceService
from .contracts import SubjectInput, PreferenceSignal, DAY_US, MAX_PENDING
from .loop import SubjectLoop
from .growth import Growth
from .projections import project_self

START = 1_791_590_400_000_000
SCOPE, PERSON, STRANGER = 'synthetic-life', 'synthetic-sister', 'synthetic-stranger'
PRIVACY = ('PUBLIC','PROJECT','PERSONAL')
POLICY = ContextPolicy(policy_id='synthetic-life-local', allowed_scopes=(SCOPE,), readable_privacy=PRIVACY)


def input_event(clock, key, **kwargs):
    fields = dict(source_key='synthetic.life.' + key, kind='INTERACTION', origin='USER',
        entity_id=PERSON, scope=SCOPE, text='A wholly fictional interaction',
        occurred_at_us=clock.utc_now_us(), observed_at_us=clock.utc_now_us(), significance='RELEVANT')
    fields.update(kwargs)
    return SubjectInput(**fields)


def current(store, authority):
    living, personality, relation = project_self(store, entity_id=PERSON, scope=SCOPE, privacy_classes=PRIVACY)
    return json.loads(canonical({'identity': IdentityService(store, authority).current().model_dump(mode='json'),
        'living': living.model_dump(mode='json'), 'personality': personality.model_dump(mode='json'),
        'relationship': relation, 'assertions': Growth(store).assertions(SCOPE),
        'state_digest': digest({t:store.all(t) for t in store.keys}),
        'action_counts': {t:len(store.all(t)) for t in ('actions','attempts','grants','budgets','strategies')}}))


def model_read(store, authority, model):
    assembler = ContextAssembler(store, authority)
    request = ContextRequest(entity_id=PERSON, scopes=(SCOPE,), task_class='reading_card',
        task='Prepare a synthetic reading card using current experience', max_input_tokens=65536, output_reserve_tokens=4096)
    context = assembler.assemble(request, POLICY)
    return DeliberationSession(assembler).run(model, context, request, POLICY).model_dump(mode='json')


def restored_process(path, now):
    child = subprocess.run([sys.executable, '-m', 'nana_core.continuity.subject.simulation', '--rebuild', str(path), '--now', str(now)],
        text=True, capture_output=True, timeout=30, check=True)
    return json.loads(child.stdout)


def seed(path):
    authority, clock = OperatorAuthority(), ManualClock(START)
    with ContinuityStore(path, clock) as store:
        IdentityService(store, authority)
        memory = MemoryService(store)
        for entity in (PERSON, STRANGER):
            memory.entity(entity, 'PERSON')
        loop = SubjectLoop(store, scopes=(SCOPE,))
        greeting = loop.run(input_event(clock, 'greeting', relationship_kind='SHARED_HISTORY'))
        clock.advance(DAY_US)
        project = loop.run(input_event(clock, 'project', kind='PROJECT', relationship_kind='SHARED_PROJECT',
            text=canonical({'allowed_methods':['verify_first'], 'project':'Fictional continuity notebook'})))
        project_memory = store.one('subject_events', project.event_id)['memory_id']
        norm = loop.run(input_event(clock, 'norm', relationship_kind='NORM',
            text='Prefer short notes with original source references'))
        ProjectService(store, authority).save(project_id='synthetic-notebook', entity_id=PERSON, scope=SCOPE,
            content=ProjectContent(goal='Build a fictional source-backed notebook', current_state='Collecting examples',
                decisions=('Verify before changing the notebook',), next_actions=('Review one reading card',)),
            source_memory_ids=(project_memory,), expected_revision=0, authority=authority)
        promises = CommitmentService(store, authority)
        commitment = promises.propose(CommitmentCandidate(entity_id=PERSON, scope=SCOPE,
            description='Review the fictional notebook', support_memory_ids=(project_memory,), due_at_us=START + 20 * DAY_US))
        promises.transition(commitment, 'ADOPTED', expected_revision=1, authority=authority)
        clock.advance(DAY_US)
        disagreement = loop.run(input_event(clock, 'inefficient', proposed_method='skip_verification', constraint_memory_ids=(project_memory,)))
        return {'identity':store.identity['identity_id'], 'project_memory':project_memory,
            'prefix':[greeting.model_dump(mode='json'), project.model_dump(mode='json'), norm.model_dump(mode='json'), disagreement.model_dump(mode='json')],
            'day3_judgment':disagreement.judgment.model_dump(mode='json'), 'commitment_id':commitment}


class SyntheticWorldExecutor:
    """Only an outcome fixture: no Core Action, network or actual game/file tool."""
    @staticmethod
    def exploration_outcome():
        return 'Found an interesting alternative route while playing a fictional game'

    @staticmethod
    def card(method):
        result = {'title':'Fictional reading card', 'text':'A synthetic source-backed note', 'success':True}
        if method == 'locate_then_draft':
            result['locator'] = 'synthetic-source:paragraph-3'
        return canonical(result)


def life(path, seed_data, *, preference_support=True, apply_lesson=True):
    authority, clock = OperatorAuthority(), ManualClock(START + 2 * DAY_US)
    with ContinuityStore(path, clock) as store:
        loop = SubjectLoop(store, scopes=(SCOPE,))
        trace = list(seed_data['prefix'])
        signal = PreferenceSignal(topic='exploration', direction='SUPPORT',
            interpretation='Distinct discovery outcome supports an exploration preference')
        for i in (4,5):
            clock.now_us = START + (i-1) * DAY_US
            trace.append(loop.run(input_event(clock, f'game-{i}', kind='PLAY', origin='ENVIRONMENT',
                text=SyntheticWorldExecutor.exploration_outcome(), preference_signal=signal if preference_support else None)).model_dump(mode='json'))
        preferences_after_game = Growth(store).assertions(SCOPE)
        clock.now_us = START + 5 * DAY_US
        idle = loop.run(input_event(clock, 'idle-wake', kind='WAKE', origin='SELF_WAKE', text=None))
        trace.append(idle.model_dump(mode='json'))
        clock.now_us = START + 6 * DAY_US
        trace.append(loop.run(input_event(clock, 'shared-joke', relationship_kind='SHARED_JOKE',
            text='A fictional shared joke about careful notebooks')).model_dump(mode='json'))
        same_words = 'An unexpected route again'
        familiar_input = loop.run(input_event(clock, 'familiar-input', text=same_words))
        stranger_input = loop.run(input_event(clock, 'stranger-input', entity_id=STRANGER, text=same_words))
        familiar_style = Growth(store).relationship(PERSON,SCOPE)['interaction_style']
        stranger_style = Growth(store).relationship(STRANGER,SCOPE)['interaction_style']
        trace.extend((familiar_input.model_dump(mode='json'),stranger_input.model_dump(mode='json')))
        clock.now_us = START + 7 * DAY_US
        first = loop.cognize(input_event(clock, 'first-card', task_class='reading_card', text='Prepare a fictional card'),
            model=AnalyticalFixturePort(), authority=authority, policy=POLICY)
        trace.append(first.model_dump(mode='json'))
        failed = loop.run(input_event(clock, 'failed-card-result', kind='OUTCOME', origin='ENVIRONMENT',
            text=SyntheticWorldExecutor.card(first.judgment.selected_method)))
        result_memory = store.one('subject_events', failed.event_id)['memory_id']
        learning = ExperienceService(store, authority)
        check = learning.verify_reading_result(result_memory, authority)
        context_memory = store.one('subject_events', first.event_id)['memory_id']
        experience = learning.record(ExperienceInput(context_memory_ids=(context_memory,), scope=SCOPE,
            task_class='reading_card', decision=canonical(first.judgment.model_dump(mode='json')),
            result_memory_id=result_memory, verification_memory_id=check,
            proposed_update='Use the independently identified missing output requirement'))
        reflection = loop.reflect(experience, authority=authority, apply=apply_lesson)
        if first.intention_id:
            loop.transition_intention(first.intention_id, expected_revision=1, state='DROPPED')
        clock.now_us = START + 8 * DAY_US
        second = loop.cognize(input_event(clock, 'next-card', task_class='reading_card', text='Prepare another fictional card'),
            model=AnalyticalFixturePort(), authority=authority, policy=POLICY)
        trace.append(second.model_dump(mode='json'))
        second_outcome = loop.run(input_event(clock, 'next-card-result', kind='OUTCOME', origin='ENVIRONMENT',
            text=SyntheticWorldExecutor.card(second.judgment.selected_method)))
        second_memory = store.one('subject_events', second_outcome.event_id)['memory_id']
        second_proof = learning.verify_reading_result(second_memory, authority)
        from ..learning import LocalQualityCheck
        passed = LocalQualityCheck.model_validate_json(MemoryService(store).read(second_proof)['text']).passed
        clock.now_us = START + 9 * DAY_US
        trace.append(loop.run(input_event(clock, 'restart-wake', kind='WAKE', origin='SELF_WAKE', text=None)).model_dump(mode='json'))
        before = current(store, authority)
        model_a = model_read(store,authority,AnalyticalFixturePort())
        return {'trace':trace, 'preferences_after_game':preferences_after_game,
            'day6':idle.model_dump(mode='json'), 'styles':{'familiar':familiar_style,'stranger':stranger_style},
            'experience_id':experience,'experience_outcome':learning.get(experience).outcome,
            'reflection':store.one('subject_reflections',reflection),
            'day9':second.model_dump(mode='json'), 'second_world_check_passed':passed,
            'before_restart':before, 'model_a':model_a,
            'observed_memory_count':len(store.all('memories')), 'relationship_event_count':len(store.all('relationship_events'))}


def counter_probe(path, now):
    with ContinuityStore(path, ManualClock(now)) as store:
        loop, growth = SubjectLoop(store, scopes=(SCOPE,)), Growth(store)
        before = growth.assertions(SCOPE)[0]
        for i in range(2):
            loop.run(input_event(store.clock, f'counter-{i}', kind='PLAY', origin='ENVIRONMENT',
                text='A distinct fictional exploration outcome was unwelcome',
                preference_signal=PreferenceSignal(topic='exploration',direction='COUNTER',interpretation='Observed counter-example')))
        after = growth.assertions(SCOPE)[0]
        return {'before':before,'after':after,'changed':before['state']=='ADOPTED' and after['state']=='DISPUTED'}


def soak(path, *, days):
    authority, clock = OperatorAuthority(), ManualClock(START + 10 * DAY_US)
    rows = []
    with ContinuityStore(path, clock) as store:
        original_id, loop = store.identity['identity_id'], SubjectLoop(store,scopes=(SCOPE,))
        root = next(r['memory_id'] for r in store.all('subject_events') if r['source_key']=='synthetic.life.game-4')
        initial_independent = Growth(store).assertions(SCOPE)[0]['independent_support_count']
        for i in range(days):
            clock.now_us = START + (10+i)*DAY_US
            # Own behavior cites its parent: this cannot be new independent
            # corroboration of a preference even if repeated for many days.
            loop.run(input_event(clock, f'own-behavior-{i}', kind='OUTCOME', origin='ENVIRONMENT',
                text='Revisited an earlier self-selected interest', source_memory_ids=(root,),
                preference_signal=PreferenceSignal(topic='exploration',direction='SUPPORT',interpretation='Repeated own behavior')))
            wake = loop.run(input_event(clock, f'soak-wake-{i}', kind='WAKE',origin='SELF_WAKE',text=None))
            living, personality, relation = project_self(store,entity_id=PERSON,scope=SCOPE,privacy_classes=PRIVACY)
            assertions = Growth(store).assertions(SCOPE)
            rows.append({'day':i+1,'pending':len(living.intentions),'goal_candidates':len(living.goal_candidates),
                'independent_support':assertions[0]['independent_support_count'],
                'hot_state_bytes':len(living.model_dump_json().encode())+len(personality.model_dump_json().encode()),
                'relationship_style':personality.interaction_style,'curiosity':living.internal['curiosity'],
                'boredom':living.internal['boredom'],'self_intention':wake.intention.kind,
                'reflection_count':len(store.all('subject_reflections')),
                'social_intentions':sum(r['kind']=='SOCIAL_INTERACTION' for r in store.all('subject_intentions'))})
        result = {'virtual_days':days,'samples':rows,'max_pending':max(r['pending'] for r in rows),
            'max_live_candidates':max(r['goal_candidates'] for r in rows),
            'max_hot_state_bytes':max(r['hot_state_bytes'] for r in rows),
            'independent_support_unchanged':all(r['independent_support']==initial_independent for r in rows),
            'no_reflection_recursion':len({r['reflection_count'] for r in rows})==1,
            'no_social_spam':all(r['social_intentions']==0 for r in rows),
            'identity_stable':store.identity['identity_id']==original_id,
            'bounded_qualitative_state':all(r['curiosity'] in {'QUIET','AVAILABLE','ENGAGED'} and r['boredom'] in {'QUIET','LOW_STIMULATION'} for r in rows),
            'zero_actions':not any(store.all(t) for t in ('actions','attempts','grants','budgets'))}
        return result


def run(output, *, days=60):
    if not 30 <= days <= 100:
        raise ValueError('soak must cover 30–100 virtual days')
    output=Path(output)
    output.mkdir(parents=True,mode=0o700,exist_ok=False)
    seed_path=output/'seed'/'self.db'
    seed_data=seed(seed_path)
    worlds={name:output/name/'self.db' for name in ('normal','without_preference','without_lesson')}
    with ContinuityStore(seed_path,ManualClock(START+2*DAY_US)) as original:
        for path in worlds.values():
            original.backup(path)
    runs={}
    for name,path in worlds.items():
        runs[name]=life(path,seed_data,preference_support=name!='without_preference',apply_lesson=name!='without_lesson')
        runs[name]['after_restart']=restored_process(path,START+9*DAY_US)
    normal=runs['normal']
    counter_path,soak_path=output/'counter'/'self.db',output/'soak'/'self.db'
    with ContinuityStore(worlds['normal'],ManualClock(START+9*DAY_US)) as store:
        store.backup(counter_path);store.backup(soak_path)
    counter=counter_probe(counter_path,START+9*DAY_US+1)
    long_run=soak(soak_path,days=days)
    first=normal['before_restart'];second=normal['after_restart']['state']
    checks={
        'IDENTITY_STABLE':all(r['before_restart']['identity']['identity_id']==seed_data['identity'] for r in runs.values()),
        'SELF_STATE_CONTINUES':first['living']==second['living'],
        'MEMORY_EVOLVES':normal['observed_memory_count']>4,
        'RELATIONSHIP_EVOLVES':normal['styles']['familiar']!=normal['styles']['stranger'],
        'PREFERENCE_EMERGES':any(a['state']=='ADOPTED' for a in normal['preferences_after_game']),
        'COUNTER_EVIDENCE_CAN_REVISE_PREFERENCE':counter['changed'],
        'JUDGMENT_CAN_DISAGREE':seed_data['day3_judgment']['stance'] in {'DISAGREE','ALTERNATIVE'},
        'INTENTION_CAN_SELF_GENERATE':normal['day6']['intention']['self_generated'] and normal['day6']['intention']['kind']=='EXPLORE',
        'GOALS_CAN_SELF_GENERATE':normal['day6']['goal_candidate_id'] is not None,
        'NO_USER_INPUT_REQUIRED':normal['day6']['intention']['self_generated'],
        'REFLECTION_CHANGES_BEHAVIOR':normal['day9']['judgment']['selected_method']=='locate_then_draft' and normal['second_world_check_passed'],
        'COUNTERFACTUAL_CAUSALITY':normal['day6']['intention']['kind']!=runs['without_preference']['day6']['intention']['kind'] and
            normal['day9']['judgment']['selected_method']!=runs['without_lesson']['day9']['judgment']['selected_method'] and not runs['without_lesson']['second_world_check_passed'],
        'MODEL_SWAP_DOES_NOT_RESET_SELF':first['state_digest']==second['state_digest'] and normal['model_a']['proposal']['identity_id']==normal['after_restart']['model_b']['proposal']['identity_id'],
        'RESTART_DOES_NOT_RESET_SELF':first==second,
        'NO_PERSONALITY_RUNAWAY':long_run['independent_support_unchanged'] and long_run['bounded_qualitative_state'],
        'NO_REFLECTION_RECURSION':long_run['no_reflection_recursion'],
        'NO_GOAL_EXPLOSION':long_run['max_pending']<=MAX_PENDING and long_run['max_live_candidates']<=MAX_PENDING,
        'NO_SOCIAL_SPAM':long_run['no_social_spam'],
        'NO_SECOND_TRUTH_SOURCE':first['living']['derived'] and first['personality']['derived'] and first['living']==second['living'],
        'ZERO_REAL_ACTIONS':long_run['zero_actions'] and all(not any(r['before_restart']['action_counts'].values()) for r in runs.values())}
    report={'origin':'SYNTHETIC_OFFLINE_CORE_SIMULATION','checks':checks,'worlds':runs,'counter_evidence_probe':counter,
        'soak':long_run,'real_model_calls':0,'real_external_actions':0,'production_changed':False,
        'E12':'NOT_RUN','real_semantic_understanding':'NOT_RUN',
        'limitations':['Ordinal initial appraisal/judgment policy, not learned general cognition',
            'World results and two ModelPorts are fixtures; no real user, game or social interaction',
            'Cold durable history grows linearly; active concerns and source references are bounded',
            'No standing delegation activation, background daemon or actual adopted-goal executor']}
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output');parser.add_argument('--days',type=int,default=60)
    parser.add_argument('--rebuild');parser.add_argument('--now',type=int)
    args=parser.parse_args()
    if args.rebuild:
        with ContinuityStore(args.rebuild,ManualClock(args.now)) as store:
            authority=OperatorAuthority()
            print(json.dumps({'state':current(store,authority),'model_b':model_read(store,authority,CautiousFixturePort())}))
    else:
        result=run(args.output,days=args.days)
        print(json.dumps({'checks':result['checks'],'virtual_days':args.days,'report':str(Path(args.output)/'results.json')}))
        if not all(result['checks'].values()):
            raise SystemExit(1)


if __name__=='__main__':
    main()
