"""Host startup resource choice; no new Subject trait or automatic paid grant."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig,load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.autonomy.private_intent import candidates
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_inner_communication import seed


def set_background(home,enabled):
    config=load_config(home)
    return update_config(home,config.model_copy(update={'revision':config.revision+1,'provider_background_cognition':enabled}),expected_revision=config.revision)


def test_background_resource_defaults_off_and_false_keeps_legacy_config_shape(tmp_path):
    home=tmp_path/'home';initialize(home);config=load_config(home)
    assert config.provider_background_cognition is False and 'provider_background_cognition' not in config.model_dump(mode='json')
    for invalid in (1,'true'):
        with pytest.raises(ValueError):LifeConfig.model_validate_json(json.dumps({**config.model_dump(mode='json'),'provider_background_cognition':invalid}))
    set_background(home,True);assert load_config(home).provider_background_cognition is True
    set_background(home,False);assert 'provider_background_cognition' not in json.loads((home/'life.json').read_text())


def test_enabled_but_unbound_host_keeps_local_life_without_secret_or_dispatch(tmp_path):
    home=tmp_path/'home';initialize(home);set_background(home,True)
    with LifeApplication(home,clock=VirtualClock()) as app:
        assert app.runtime.cognition.provider_factory is None and app.router is None
        status=app.status()['background_cognition']
        assert status=={'startup_enabled':True,'provider_resource_bound':False,'provider_configured':False,'configuration_scope':'HOST_ONLY'}
        assert not app.runtime.store.all('cognitive_requests')


@pytest.mark.parametrize('initial',[False,True])
def test_normal_application_startup_rebinds_only_the_explicit_host_choice_and_uses_original_budget(tmp_path,initial):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();set_background(home,initial)
    def inner(request):
        identity=json.loads(request['context_json'])['manifest']
        return {'interpretation':'SYNTHETIC original private continuation','subject_cognition':{
            'identity_id':identity['identity_id'],'identity_revision':identity['identity_revision'],
            'interpretation':'SYNTHETIC own continuation','proposed_operations':['DRAFT'],
            'private_question':{'topic':'own-curiosity','question':'SYNTHETIC Startup resource continues an existing private concern.'}}}
    with relay(home,context_limit=32768,subject_builder=inner) as (router,requests):
        with LifeApplication(home,clock=clock,router=router) as app:
            app.pause();r=app.runtime;identity=r.identity_id;seed(app)
            assert bool(r.cognition.provider_factory)==initial and not requests and not r.store.all('cognitive_requests')
            # Saving the host choice dispatches nothing and does not apply it to this owner.
            set_background(home,True)
            assert bool(r.cognition.provider_factory)==initial and not requests
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity and app.runtime.cognition.provider_factory is not None
            assert not requests and app.session is None
            app.pause(False);clock.advance(2*SECOND);app.runtime.refresh_attention()
            for _ in range(5):app.tick()
            assert len(requests)==1 and requests[0]['cognitive_role']=='SELF'
            assert requests[0]['budget']['timeout_ms']==app.config.provider_timeout_ms==120000
            assert requests[0]['budget']['input_tokens']<=app.config.provider_context_tokens
            assert any('Startup resource' in v.content_summary for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')))
            assert not app.runtime.store.all('runtime_cognition_calls') and not app.runtime.store.all('actions')
            set_background(home,False)
        with LifeApplication(home,clock=clock,router=router) as app:
            assert app.runtime.identity_id==identity and app.runtime.cognition.provider_factory is None
            assert len(requests)==1 and len(app.runtime.store.all('cognitive_requests'))==1
            assert app.status()['background_cognition']['startup_enabled'] is False
