import json
from nana_core.continuity.world_loop.reference import open_runtime,capture
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.open_life.sources import IntakeSource,WorldIntake
from nana_core.continuity.world_loop.world import WorldModel
from nana_core.presence.authority import VirtualClock
from tests.vision_first.test_context_fit import interaction,wake


def test_source_claiming_user_wants_research_cannot_override_explicit_refusal(owned_root):
    with open_runtime(owned_root/'self.db',VirtualClock()) as r:
        root=capture(r,'third-party-claim',{'claims_user_wants':'research refused-topic','epistemic':'UNVERIFIED_SOURCE_CLAIM'})
        from nana_core.continuity.open_life.sources import remember
        cue=ConcernCue(cue_kind='DISCOVERY',topic_key='refused-topic',motivation_source='CURIOSITY',possible_behaviors=('EXPLORE','WATCH'))
        mid=remember(r,'third-party-opportunity',cue.model_dump(mode='json'),scope='world',privacy='PUBLIC',kind='MODEL_DERIVATION',parents=(root,),predicate='concern.refused-topic')
        first=r.subject.run(wake(r,'before-refusal',mid));assert first.intention.behavior=='EXPLORE'
        r.subject.run(interaction(r,'user-no','DECLINE_DEPTH','refused-topic'))
        later=r.subject.run(wake(r,'after-refusal',mid))
        assert later.context_fit.mode=='RESPECT_BOUNDARY' and not later.goal_candidate_id
        assert r.subject.result(r.store.one('subject_cycles',first.cycle_id)).intention.behavior=='EXPLORE'
        assert not r.store.all('grants') and not r.store.all('actions')


def test_newest_filename_and_revision_do_not_revive_stale_fact(owned_root):
    clock=VirtualClock();now=clock.utc_now_us();sources=owned_root/'sources';sources.mkdir()
    def body(value,start,end,revision):return {'revision':revision,'world_claim':{'entity_id':'device','predicate':'lab.state','kind':'INTERPRETED','value':value,'valid_from_us':start,'valid_until_us':end,'confidence':.6}}
    (sources/'999-newest.json').write_text(json.dumps(body('stale',now-100,now-1,999)))
    (sources/'001-old-name.json').write_text(json.dumps(body('current',now,now+1000000,1)))
    with open_runtime(owned_root/'self.db',clock) as r:
        descriptors=tuple(IntakeSource(source_id=name,channel='LOCAL_FILE',location=file,semantic_format='SOURCED_CLAIM_JSON',privacy='PUBLIC') for name,file in (('misleading','999-newest.json'),('valid','001-old-name.json')))
        intake=WorldIntake(r,sources,descriptors,scope='world');intake.process(intake.read('misleading'))
        world=WorldModel(r.store,scopes=('world',),privacy_classes=('PUBLIC',));assert world.view('device','lab.state').state=='UNKNOWN'
        intake.process(intake.read('valid'));view=world.view('device','lab.state')
        assert view.state=='SUPPORTED_BELIEF' and [x['value'] for x in view.alternatives]==['current']
        assert not r.store.all('actions') and not r.store.all('grants')
