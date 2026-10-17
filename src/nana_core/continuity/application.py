"""In-process frontend contract over existing projections/transitions.

No HTTP server and no direct database mutation. The application constructs this
facade with controller handles; clients get only its session API. Python object
introspection/root modification are not a security sandbox claim.
"""
from typing import Literal
from pydantic import Field
from ..contracts import DTO,CoreError
from ..storage import canonical
from .context import ContextPolicy,self_frame
from .memory import MemoryService
from .relationships import relationship_view
from .relational.bootstrap import SubjectBootstrapService,primary_user_view
from .relational.projections import personality_tendencies,self_narrative,social_appetite
from .relational.contracts import RelationalAnchorSpec
from .surfaces import SurfaceIngress,ContinuityViews
from .extensions import SurfaceEnvelope
from .subject.contracts import SubjectInput

class FrontendPolicy(DTO):
    context: ContextPolicy
    entity_id: str
    commands: tuple[Literal['SEND_INPUT','PROPOSE_GOAL','FORGET','CONFIGURE_PRIMARY_USER','CHANGE_SETTING','CAPABILITY_REVIEW'],...]
    deletable_scopes: tuple[str,...] = ()

class FrontendProjection(DTO):
    kind: str
    derived: Literal[True] = True
    data_json: str
    execution_authority: Literal[False] = False

class CapabilityReviewProposal(DTO):
    """Future authority workflow only. This never becomes a Grant/Capability."""
    operation: Literal['REQUEST_APPROVAL','REQUEST_REVOCATION']
    capability_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{1,127}$')
    resource_reference: str = Field(pattern=r'^synthetic[.:_-][A-Za-z0-9._:-]{1,128}$')
    scope: str = Field(min_length=1,max_length=96)
    execution_authority: Literal[False] = False
    state: Literal['PROPOSAL_ONLY_NOT_AUTHORIZATION'] = 'PROPOSAL_ONLY_NOT_AUTHORIZATION'

class SubjectApplication:
    def __init__(self,store,subject_loop,operator,*,providers,bootstrap_authority=None,health=None,runtime_views=None,ingress=None):
        if subject_loop.store is not store:raise CoreError('FRONTEND_SUBJECT_STORE_MISMATCH')
        self._store,self._subject,self._operator=store,subject_loop,operator
        self._providers,self._bootstrap,self._health=providers,bootstrap_authority,health
        self._runtime_views,self._ingress=runtime_views,ingress
    def session(self,policy:FrontendPolicy):
        if not set(policy.deletable_scopes)<=set(policy.context.allowed_scopes):raise CoreError('FRONTEND_POLICY_INVALID')
        if not self._store.one('entities',policy.entity_id):raise CoreError('FRONTEND_ENTITY_UNBOUND')
        return FrontendSession(self,policy)

class FrontendSession:
    def __init__(self,application,policy):
        self.__app,self.__policy=application,policy
        self.__settings={'presentation.detail':'BRIEF'}
    def _allowed(self,command):
        if command not in self.__policy.commands:raise CoreError('FRONTEND_COMMAND_DENIED')
    def _scope(self,scope):
        if scope not in self.__policy.context.allowed_scopes:raise CoreError('FRONTEND_SCOPE_DENIED')
    def _event(self,envelope,event):
        if not isinstance(envelope,SurfaceEnvelope) or not isinstance(event,SubjectInput):raise CoreError('FRONTEND_TYPED_INPUT_REQUIRED')
        self._scope(event.scope)
        if event.entity_id!=self.__policy.entity_id or event.privacy_class not in self.__policy.context.readable_privacy or event.origin!='USER':
            raise CoreError('FRONTEND_INPUT_POLICY_DENIED')
        if self.__app._ingress:return self.__app._ingress(envelope,event)
        return SurfaceIngress(self.__app._subject).submit(envelope,event)
    def send_input(self,envelope:SurfaceEnvelope,event:SubjectInput):
        self._allowed('SEND_INPUT');return self._event(envelope,event)
    def propose_goal(self,envelope:SurfaceEnvelope,event:SubjectInput):
        self._allowed('PROPOSE_GOAL')
        if event.kind!='PROJECT':raise CoreError('FRONTEND_GOAL_REQUEST_REQUIRED')
        # Request -> existing Subject judgment -> possibly GoalCandidate, never AdoptedGoal.
        return self._event(envelope,event)
    def forget(self,memory_id):
        self._allowed('FORGET');store=self.__app._store
        head=store.one('memories',memory_id)
        if not head or head['entity_id'] not in {self.__policy.entity_id,store.identity['identity_id']} or head['scope'] not in self.__policy.deletable_scopes or head['privacy_class'] not in self.__policy.context.readable_privacy:
            raise CoreError('FRONTEND_DELETE_DENIED')
        if head['lifecycle']=='DELETED':return {'state':'ALREADY_DELETED'}
        return MemoryService(store,self.__app._operator).forget(memory_id,self.__app._operator)
    def configure_primary_user(self,spec:RelationalAnchorSpec):
        self._allowed('CONFIGURE_PRIMARY_USER');self._scope(spec.scope)
        if spec.role_kind!='PRIMARY_USER':raise CoreError('EXPLICIT_PRIMARY_USER_REQUIRED')
        authority=self.__app._bootstrap
        if authority is None:raise CoreError('SUBJECT_BOOTSTRAP_AUTHORITY_REQUIRED')
        return SubjectBootstrapService(self.__app._store,authority).install(spec,authority)
    def change_setting(self,key,value):
        self._allowed('CHANGE_SETTING')
        if key!='presentation.detail' or value not in {'BRIEF','EXPANDED'}:raise CoreError('FRONTEND_SETTING_DENIED')
        self.__settings[key]=value;return dict(self.__settings)
    def request_capability_review(self,proposal:CapabilityReviewProposal):
        self._allowed('CAPABILITY_REVIEW');self._scope(proposal.scope)
        return CapabilityReviewProposal.model_validate_json(proposal.model_dump_json())
    def view(self,kind,*,scope=None,tier='L0_LIVE'):
        app,p=self.__app,self.__policy
        scopes=(scope,) if scope else p.context.allowed_scopes
        for s in scopes:self._scope(s)
        privacy=p.context.readable_privacy
        if kind in {'LIVING_RUNTIME','LIVING_JOURNAL','RESOURCE_STATE','OPEN_AUTONOMY','WORLD_LOOP'}:
            if not app._runtime_views:raise CoreError('RUNTIME_VIEW_UNAVAILABLE')
            data=app._runtime_views(kind,p.context,scopes=scopes,entity_id=p.entity_id)
        elif kind=='SELF':
            data=self_frame(app._store,app._operator,entity_id=p.entity_id,scopes=scopes,privacy_classes=privacy).model_dump(mode='json')
        elif kind=='CONTINUITY':
            return ContinuityViews(app._store,p.context).project(tier,entity_id=p.entity_id,scopes=scopes)
        elif kind=='RELATIONSHIP':
            data={'relationship':relationship_view(app._store,p.entity_id,scopes=scopes,privacy_classes=privacy).model_dump(mode='json'),'primary_user_entity_id':None}
            if len(scopes)==1 and app._store.schema_target>=10:
                primary=primary_user_view(app._store,scope=scopes[0],privacy_classes=privacy)
                data['primary_user_entity_id']=primary.spec.entity_id if primary else None
                data['anchor']=primary.model_dump(mode='json') if primary else None
        elif kind=='PERSONALITY':
            if len(scopes)!=1:raise CoreError('FRONTEND_EXACT_SCOPE_REQUIRED')
            data={k:v.model_dump(mode='json') for k,v in (
                ('tendencies',personality_tendencies(app._store,scope=scopes[0],privacy_classes=privacy,entity_id=p.entity_id)),
                ('narrative',self_narrative(app._store,scope=scopes[0],privacy_classes=privacy,entity_id=p.entity_id)),
                ('appetite',social_appetite(app._store,scope=scopes[0],privacy_classes=privacy)))}
        elif kind=='LIVING_SELF':
            if len(scopes)!=1:raise CoreError('FRONTEND_EXACT_SCOPE_REQUIRED')
            from .subject.projections import project_self
            living,personality,relationship=project_self(app._store,entity_id=p.entity_id,scope=scopes[0],privacy_classes=privacy)
            data=living.model_dump(mode='json')
        elif kind=='MEMORY_SUMMARY':
            service=MemoryService(app._store)
            data={'visible_count':service.query_count(entity_ids=(p.entity_id,app._store.identity['identity_id']),scopes=scopes,privacy_classes=privacy),
                'memory_ids':tuple(m['memory_id'] for m in service.query(entity_ids=(p.entity_id,app._store.identity['identity_id']),scopes=scopes,privacy_classes=privacy))}
        elif kind=='GOALS_COMMITMENTS_PROJECTS':
            view=ContinuityViews(app._store,p.context).project('L1_RECENT',entity_id=p.entity_id,scopes=scopes)
            data={'goal_candidate_ids':view.goal_candidate_ids,'commitment_ids':view.commitment_ids,'project_ids':view.project_ids,'intention_ids':view.intention_ids,'source_record_ids':view.source_record_ids}
        elif kind=='RUNTIME':
            data=app._health().model_dump(mode='json') if app._health else {'status':'NOT_RUNNING','derived':True}
        elif kind=='PROVIDERS':data={'descriptors':[d.model_dump(mode='json') for d in app._providers.descriptors()]}
        else:raise CoreError('FRONTEND_VIEW_UNKNOWN')
        return FrontendProjection(kind=kind,data_json=canonical(data))

    def assemble_context(self,request):
        from .context import ContextAssembler,ContextRequest
        if type(request) is not ContextRequest or request.entity_id!=self.__policy.entity_id:
            raise CoreError('FRONTEND_CONTEXT_REQUEST_DENIED')
        return ContextAssembler(self.__app._store,self.__app._operator).assemble(request,self.__policy.context)
