"""Independent cross-episode strategy evidence, counterexamples and revalidation."""
import json
from ...contracts import CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from ..learning import ExperienceService
from ..open_agency.learning import LearningCase,IndependentEvaluator

class EpisodeLearning:
    def __init__(self,store,authority,*,scopes,privacy_classes):
        self.store,self.authority,self.scopes,self.privacy=store,authority,tuple(scopes),tuple(privacy_classes)
        self.records=RecordService(store);self.experiences=ExperienceService(store,authority)
    def assess(self,lesson_id,source_memory_id,*,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        memory=self.records.memory.read(source_memory_id)
        if memory['scope'] not in self.scopes or memory['privacy_class'] not in self.privacy or memory['authority']!='DIRECT':raise CoreError('STRATEGY_EPISODE_SOURCE_REQUIRED')
        try:
            body=json.loads(memory['text'])['strategy_episode'];case=LearningCase.model_validate_json(canonical(body['case']));key=body['episode_key']
            if body['lesson_id']!=lesson_id or type(key)!=str or not 1<=len(key)<=96:raise ValueError()
        except (KeyError,TypeError,ValueError):raise CoreError('STRATEGY_EPISODE_INVALID') from None
        old=self.store.db.execute('SELECT * FROM strategy_assessments WHERE lesson_id=? AND episode_key=?',(lesson_id,key)).fetchone()
        if old:return old['assessment_id']
        lesson=self.store.one('lessons',lesson_id)
        if not lesson or lesson['state'] not in {'ACTIVE','SUSPENDED'}:raise CoreError('STRATEGY_REVIEW_UNAVAILABLE')
        head=self.records.read(lesson['record_id'])
        if head['scope']!=memory['scope'] or head['privacy_class'] not in self.privacy or not self.records.current_support(lesson['record_id']):raise CoreError('STRATEGY_SOURCE_RETIRED')
        rule=self.experiences._rule(lesson)
        if getattr(rule,'kind',None)!='METHOD_SELECTION':raise CoreError('METHOD_STRATEGY_REQUIRED')
        result=IndependentEvaluator().evaluate(rule.method,(case,));verdict='SUCCESS' if result['all_passed'] else 'COUNTEREXAMPLE'
        aid=uid()
        with self.store.transaction('world.strategy_episode_checked',{'assessment_id':aid,'verdict':verdict}) as tx:
            rid=self.records.create(tx,kind='STRATEGY_REVIEW',scope=memory['scope'],payload={'episode':body,'result':result,'method':rule.method,'attribution':'STRATEGY_OUTPUT_VS_INDEPENDENT_EXPECTATION','not_a_personality_change':True},memories=(source_memory_id,),records=(lesson['record_id'],),target_id=lesson_id)
            tx.put('strategy_assessments',{'assessment_id':aid,'lesson_id':lesson_id,'record_id':rid,'episode_key':key,'verdict':verdict,'context_digest':digest([case.context,case.data]),'created_at_us':self.store.clock.utc_now_us()})
            # A durable disproof and its strategy fence are one causal change.
            # A crash must never leave ACTIVE selection between two commits;
            # replay of an already assessed episode would otherwise skip it.
            if verdict=='COUNTEREXAMPLE' and lesson['state']=='ACTIVE':
                tx.update('lessons',lesson_id,state='SUSPENDED',revision=lesson['revision']+1)
        return aid
    def view(self,lesson_id):
        rows=self.store.db.execute('SELECT * FROM strategy_assessments WHERE lesson_id=? ORDER BY created_at_us DESC,rowid DESC LIMIT 64',(lesson_id,)).fetchall();seen=set();valid=[]
        for row in rows:
            head=self.store.one('continuity_records',row['record_id'])
            if head['scope'] not in self.scopes or head['privacy_class'] not in self.privacy or head['lifecycle']!='ACTIVE' or not self.records.current_support(row['record_id']) or row['context_digest'] in seen:continue
            seen.add(row['context_digest']);valid.append(row)
        success=sum(r['verdict']=='SUCCESS' for r in valid);counter=sum(r['verdict']=='COUNTEREXAMPLE' for r in valid)
        return {'lesson_id':lesson_id,'distinct_checked_contexts':len(valid),'supports':success,'counterexamples':counter,'support_fraction':success/(success+counter) if valid else None,'confidence_semantics':'DERIVED_SUPPORT_FRACTION_NOT_CALIBRATED','state':self.store.one('lessons',lesson_id)['state'],'record_ids':tuple(r['record_id'] for r in valid)}
    def revalidate(self,lesson_id,*,authority):
        if authority is not self.authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        lesson=self.store.one('lessons',lesson_id)
        if not lesson or lesson['state']!='SUSPENDED':raise CoreError('SUSPENDED_STRATEGY_REQUIRED')
        rows=self.store.db.execute('SELECT * FROM strategy_assessments WHERE lesson_id=? ORDER BY rowid DESC LIMIT 64',(lesson_id,)).fetchall();contexts=set();support=[]
        for row in rows:
            if not self.records.current_support(row['record_id']):continue
            head=self.records.read(row['record_id'])
            if head['scope'] not in self.scopes or head['privacy_class'] not in self.privacy:continue
            if row['verdict']=='COUNTEREXAMPLE':break
            if row['verdict']=='SUCCESS':contexts.add(row['context_digest']);support.append(row['record_id'])
        if len(contexts)<2:raise CoreError('INDEPENDENT_REVALIDATION_REQUIRED')
        rule=self.experiences._rule(lesson)
        for row in rows:
            if row['verdict']!='COUNTEREXAMPLE' or not self.records.current_support(row['record_id']):continue
            payload=self.records.read(row['record_id'])['payload']
            case=LearningCase.model_validate_json(canonical(payload['episode']['case']))
            if not IndependentEvaluator().evaluate(rule.method,(case,))['all_passed']:raise CoreError('UNRESOLVED_COUNTEREXAMPLE')
        self.experiences.test_lesson(lesson_id);self.experiences.activate(lesson_id,self.authority)
        with self.store.transaction('world.strategy_revalidated',{'lesson_id':lesson_id,'support_records':support}):pass
        return self.view(lesson_id)
    def competition(self,domain):
        results=[]
        for row in self.store.db.execute("SELECT lesson_id FROM lessons WHERE task_class=? AND state IN ('ACTIVE','SUSPENDED') ORDER BY rowid DESC LIMIT 16",(domain,)):
            result=self.view(row[0]);results.append(result)
        return tuple(sorted(results,key=lambda r:(r['state']=='ACTIVE',r['supports']-2*r['counterexamples']),reverse=True))
