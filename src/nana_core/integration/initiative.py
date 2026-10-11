"""Host initiative gate reuses Initiative; never constructs a live Runtime."""
from ..initiative import Initiative
from ..contracts import CoreError

class _ShadowAuthorization:
    def _grant_for(self,*args,**kw):raise CoreError('SHADOW_BLOCKED')

class InitiativeHostGate:
    def __init__(self,store):self._initiative=Initiative(store,_ShadowAuthorization())
    def propose_and_evaluate(self,candidate):
        key=self._initiative.propose(candidate)
        return key,self._initiative.evaluate(key)
    def activate(self,*args,**kwargs):raise CoreError('SHADOW_BLOCKED')
