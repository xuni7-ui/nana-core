"""Reviewed offline learning/procedure extension; no Python/plugin installation."""
import json
from ..actions import OperatorAuthority
from ..contracts import CoreError
from ..storage import canonical,digest
from .learning import ExperienceService
from .records import RecordService
from .agency_contracts import OfflineProgram

class OfflineLearningPolicy:
    def __init__(self,tasks=('reading_card',)):
        if not tasks or not set(tasks)<={'reading_card','interaction.shared_discovery','disposition.review'}:raise CoreError('FINITE_LEARNING_POLICY_REQUIRED')
        self.tasks=frozenset(tasks)
    def apply(self,runtime,experience_id):
        experience=ExperienceService(runtime.store,runtime.authority).get(experience_id)
        if experience.task_class not in self.tasks:return None
        try:return runtime.subject.reflect(experience_id,authority=runtime.authority,apply=True)
        except CoreError as exc:
            if exc.code=='NO_SUPPORTED_LESSON':return None
            raise

class OfflineSkillService:
    """Need=verified failure; procedure=bounded data; activation=trusted review."""
    def __init__(self,store,authority,program_policy):
        if store.schema_target<11 or not isinstance(authority,OperatorAuthority):raise CoreError('OFFLINE_SKILL_CONTROLLER_REQUIRED')
        self.store,self._authority,self.policy=store,authority,program_policy;self.records=RecordService(store)
    def propose(self,lesson_id,program:OfflineProgram):
        lesson=self.store.one('lessons',lesson_id)
        if not lesson or lesson['state']!='ACTIVE' or not lesson['test_event_id'] or not self.records.current_support(lesson['record_id']):raise CoreError('VERIFIED_LESSON_REQUIRED')
        row=self.records.read(lesson['record_id']);rule=row['payload']['rule']
        if row['scope']!=program.scope or rule.get('kind')!='ADD_READ_STEP' or lesson['tested_rule_hash']!=digest(rule):raise CoreError('OFFLINE_PROCEDURE_SCOPE_MISMATCH')
        key=digest([lesson_id,program.model_dump(mode='json')])
        old=self.store.db.execute("SELECT data_json FROM events WHERE source_namespace='living.skill-proposal' AND source_key=?",(key,)).fetchone()
        if old:return json.loads(old[0])['data']['record_id']
        data={'target_id':program.program_id}
        with self.store.transaction('living.skill_proposed',data,source_namespace='living.skill-proposal',source_key=key) as tx:
            rid=self.records.create(tx,kind='SKILL_PROPOSAL',scope=program.scope,payload={'state':'SANDBOX_TESTED_NOT_ENABLED','program':program.model_dump(mode='json'),'lesson_id':lesson_id,'trial_event_id':lesson['test_event_id'],'rule_digest':lesson['tested_rule_hash'],'executable_code':False,'real_installation':False},records=(lesson['record_id'],),target_id=program.program_id)
            data['record_id']=rid
        return rid
    def enable_offline(self,proposal_id,*,authority):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        row=self.records.read(proposal_id)
        if row['record_kind']!='SKILL_PROPOSAL' or not self.records.current_support(proposal_id):raise CoreError('SKILL_SOURCE_RETIRED')
        body=row['payload'];program=OfflineProgram.model_validate_json(canonical(body['program']))
        lesson=self.store.one('lessons',body['lesson_id'])
        if not lesson or lesson['state']!='ACTIVE' or lesson['tested_rule_hash']!=body['rule_digest']:raise CoreError('SKILL_TRIAL_STALE')
        self.policy.install_reviewed(program,proposal_id)
        old=self.store.db.execute("SELECT 1 FROM events WHERE source_namespace='living.skill-enabled' AND source_key=?",(proposal_id,)).fetchone()
        if not old:
            with self.store.transaction('living.skill_enabled',{'record_id':proposal_id,'program_id':program.program_id,'mode':'OFFLINE_PROCEDURE_ONLY'},source_namespace='living.skill-enabled',source_key=proposal_id):pass
        return program.program_id
