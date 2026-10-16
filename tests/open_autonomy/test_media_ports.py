from nana_core.continuity.providers import ProviderRegistry,ProviderDescriptor
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.open_agency.exploration import ContentItem,ContentFeed,ExplorationService,FixtureContentUnderstandingPort
from nana_core.continuity.open_agency.contracts import Objective,Operator
from .helpers import *
from .test_learning import language_learning

def register_video():
    reg=ProviderRegistry();reg.register(ProviderDescriptor(provider_id='fixture.media',model_id='fixture.video',model_version='1',operations=('VIDEO_UNDERSTAND',),input_modalities=('TEXT','VIDEO'),output_modalities=('TEXT',),context_limit=16384,output_limit=4096,locality='LOCAL_FIXTURE',permitted_privacy=('PUBLIC','PERSONAL')),FixtureContentUnderstandingPort());return reg

def test_actual_world_port_media_session_and_c_interest_create_learning(tmp_path):
    with fresh(tmp_path/'s'/'self.db') as r:
        browse=Objective(objective_id='explore.feed',scope='lab',motivation_source='CURIOSITY',task_domain='media',desired=('seen',),operators=(Operator(operator_id='feed',capability='world.observe',resource='synthetic://content/feed',produces=('seen',),args={}),))
        port=configure(r,tmp_path/'w'/'world.fixture.json',(browse,));spec=language_learning();r.work.configure_open_learning((spec,))
        r.work.exploration=ExplorationService(r.store,register_video(),ContextPolicy(policy_id='fixture',allowed_scopes=('lab',),readable_privacy=('PUBLIC','PERSONAL')), 'fixture.video',(spec.learning_key,))
        feed=ContentFeed(items=(ContentItem(content_id='clip-one',media_type='VIDEO',topic='language',learning_key=spec.learning_key,source_reference='synthetic.clip.one',occurred_at_us=r.clock.utc_now_us(),privacy_class='PUBLIC'),))
        port.seed_observation('synthetic://content/feed',feed.model_dump(mode='json'))
        mid=cue(r,browse);send(r,'browse',(mid,));r.drain(40)
        assert r.store.all('goals')[0]['state']=='COMPLETED'
        assert r.work.open_learning.strategy('language','lab')[1]=='UNICODE_WORDS'
        assert r.store.db.execute("SELECT count(*) FROM continuity_records WHERE record_kind='WORLD_OBSERVATION'").fetchone()[0]==1
        assert not r.store.all('runtime_cognition_calls')
        assert r.store.db.execute("SELECT count(*) FROM memories WHERE epistemic_kind='INFERENCE' AND predicate_key='concern.language'").fetchone()[0]==1
