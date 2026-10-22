import pytest
from nana_core.storage import digest
from nana_core.contracts import CoreError
from nana_core.continuity.open_life.capabilities import *

def test_simulator_gestures_compile_only_not_authority():
    observation={'task':{'task_id':'form','kind':'FORM','fields':['name']},'state':{'revision':1,'values':{'name':''}}}
    gestures=tuple(EmbodiedGesture(**g) for g in [
        {'operation':'LAUNCH','target':'form'},{'operation':'CLICK','target':'name'},
        {'operation':'TYPE','text':'PROJECT TEST'},{'operation':'TAP','target':'submit'},
        {'operation':'READ_RESULT'},{'operation':'VERIFY_STATE'}])
    proposal=EmbodiedProposal(target_task_id='form',source_revision=1,observation_digest=digest(observation),gestures=gestures)
    commands=compile_simulated_form(observation,proposal)
    assert commands['commands']==[{'op':'SET_FIELD','field':'name','value':'PROJECT TEST'},{'op':'SUBMIT'}]
    assert proposal.execution_authority is False
    with pytest.raises(CoreError):compile_simulated_form(observation,proposal.model_copy(update={'source_revision':2}))
    with pytest.raises(CoreError):compile_simulated_form(observation,proposal.model_copy(update={'gestures':(EmbodiedGesture(operation='CLICK',target='name'),)}))
    assert {d.family for d in hand_catalog()}=={'FILES','HTTP_API','BROWSER','APP_IPC','CONTROLLED_PROCESS','DESKTOP','MOBILE','GAME'}
