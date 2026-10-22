"""Common descriptive Hand/embodied contracts. Descriptors never grant access.

The finite simulator compiles app-local gestures into the existing owned FORM
command protocol. Its output is a proposal for world.publish, never dispatched
here. No global input, real desktop/mobile APIs, shell or account login.
"""
from typing import Literal
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...storage import digest

class HandDescriptor(DTO):
    hand_id:str
    family:Literal['FILES','HTTP_API','BROWSER','APP_IPC','CONTROLLED_PROCESS','DESKTOP','MOBILE','GAME']
    qualification:Literal['OWNED_DEV','SIMULATOR','CONTRACT_ONLY']
    operations:tuple[str,...]=Field(min_length=1,max_length=12)
    permission_class:Literal['KERNEL_GRANT_REQUIRED']='KERNEL_GRANT_REQUIRED'
    privacy_classes:tuple[Literal['PUBLIC','PROJECT'],...]=('PROJECT',)
    reversibility:Literal['REVERSIBLE','PARTIAL','NOT_ESTABLISHED']
    cost_class:Literal['LOCAL_BOUNDED','EXPLICIT_EXTERNAL_BUDGET']
    preconditions:tuple[str,...]
    effect_receipt:Literal['CORRELATED_APPLICATION_RECEIPT']='CORRELATED_APPLICATION_RECEIPT'
    verify_method:str
    unknown_semantics:Literal['VERIFY_NO_BLIND_RETRY']='VERIFY_NO_BLIND_RETRY'
    execution_authority:Literal[False]=False


def hand_catalog():
    out=[]
    for family,qual,ops in (
        ('FILES','OWNED_DEV',('MOVE_DECLARED',)),('APP_IPC','OWNED_DEV',('READ','FORM','DOCUMENT','CONTENT')),
        ('BROWSER','OWNED_DEV',('OPEN','READ','NAVIGATE','FORM','SUBMIT')),
        ('HTTP_API','OWNED_DEV',('OWNED_LOOPBACK_READ','OWNED_FORM_SUBMIT')),
        ('CONTROLLED_PROCESS','CONTRACT_ONLY',('BOUNDED_PROCESS',)),
        ('DESKTOP','SIMULATOR',('OBSERVE_SCREEN','FOCUS_APP','CLICK','TYPE','SCROLL','BACK','HOME','LAUNCH','READ_RESULT','VERIFY_STATE')),
        ('MOBILE','SIMULATOR',('OBSERVE_SCREEN','FOCUS_APP','TAP','TYPE','SCROLL','BACK','HOME','LAUNCH','READ_RESULT','VERIFY_STATE')),
        ('GAME','SIMULATOR',('OBSERVE_SCREEN','CLICK','READ_RESULT','VERIFY_STATE'))):
        out.append(HandDescriptor(hand_id=family.lower(),family=family,qualification=qual,operations=ops,
            reversibility='PARTIAL' if qual!='CONTRACT_ONLY' else 'NOT_ESTABLISHED',cost_class='LOCAL_BOUNDED',
            preconditions=('EXPLICIT_OWNED_TARGET','CURRENT_REVISION','MANAGER_PASS','KERNEL_GRANT','BUDGET'),verify_method='ORIGINAL_READ_ONLY_IPC_AND_PERSISTED_STATE'))
    return tuple(out)

class EmbodiedGesture(DTO):
    operation:Literal['FOCUS_APP','CLICK','TAP','TYPE','SCROLL','BACK','HOME','LAUNCH','READ_RESULT','VERIFY_STATE']
    target:str|None=Field(default=None,max_length=32)
    text:str|None=Field(default=None,max_length=128)

class EmbodiedProposal(DTO):
    target_task_id:str
    source_revision:int=Field(ge=1)
    observation_digest:str=Field(pattern=r'^[a-f0-9]{64}$')
    gestures:tuple[EmbodiedGesture,...]=Field(min_length=1,max_length=32)
    execution_authority:Literal[False]=False


def compile_simulated_form(observation,proposal):
    """A finite owned device-screen simulator, not real device qualification."""
    task=observation['task'];state=observation['state']
    if task['kind']!='FORM' or proposal.target_task_id!=task['task_id'] or proposal.source_revision!=state['revision'] or proposal.observation_digest!=digest(observation):raise CoreError('EMBODIED_STALE_OBSERVATION')
    focused=False;field=None;commands=[];submitted=False
    for gesture in proposal.gestures:
        op=gesture.operation
        if submitted and op not in {'READ_RESULT','VERIFY_STATE'}:raise CoreError('EMBODIED_POST_SUBMIT_MUTATION')
        if op in {'LAUNCH','FOCUS_APP'}:
            if gesture.target!=task['task_id']:raise CoreError('EMBODIED_TARGET_DENIED')
            focused=True
        elif op in {'HOME','BACK'}:focused=False;field=None
        elif op=='SCROLL':
            if not focused:raise CoreError('EMBODIED_FOCUS_REQUIRED')
        elif op in {'CLICK','TAP'}:
            if not focused:raise CoreError('EMBODIED_FOCUS_REQUIRED')
            if gesture.target=='submit':commands.append({'op':'SUBMIT'});submitted=True
            elif gesture.target in task['fields']:field=gesture.target
            else:raise CoreError('EMBODIED_TARGET_DENIED')
        elif op=='TYPE':
            if not focused or field is None or gesture.text is None:raise CoreError('EMBODIED_FOCUS_REQUIRED')
            commands.append({'op':'SET_FIELD','field':field,'value':gesture.text})
        elif op in {'READ_RESULT','VERIFY_STATE'}:
            if not submitted:raise CoreError('EMBODIED_NO_RESULT')
    if not submitted or not 1<=len(commands)<=9:raise CoreError('EMBODIED_FINITE_FORM_REQUIRED')
    return {'task_id':task['task_id'],'revision':state['revision'],'commands':commands}
