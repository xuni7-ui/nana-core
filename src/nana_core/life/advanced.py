"""Bounded, opt-in advanced attention at the original D opportunity safe point."""
from ..storage import digest
from ..contracts import CoreError
from ..continuity.records import RecordService
from ..continuity.open_life.opportunities import OpportunityQueue,LifeOpportunity
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.world_loop.world import WorldModel
from ..presence.contracts import DAY,SECOND
from ..continuity.open_life.sources import WorldIntake
from ..continuity.world_loop.world import SourcedClaim
import json


class AdvancedLife:
    def __init__(self,app,previous):
        self.app,self.previous=app,previous;self.queue=OpportunityQueue(app.runtime);self.next_at=0
        self.intake=WorldIntake(app.runtime,app.config.world_source_root or app.config.project_root,app.config.world_sources,scope=app.runtime.config.scopes[0])
        self.next_source_at=0;self.source_health={}
        from ..continuity.controlled_world.projects import ProjectPortfolio
        self.projects=ProjectPortfolio(app,app.config.controlled_projects) if app.config.controlled_projects else None
        from ..continuity.open_life.research_work import ResearchWork
        self.research_work=ResearchWork(app.runtime,self.queue,self.intake,record_outcomes=app.config.record_research_outcomes)

    def maintenance_slice(self):
        shared=self.app.shared.reconcile()
        if shared:return shared
        result=self.research_work.slice()
        if result and result.get('state') in {'ENOUGH_FOR_BOUNDED_BELIEF','CONTRADICTION'}:self.next_at=0
        return result

    def intake_slice(self):
        r=self.app.runtime;now=r.clock.utc_now_us()
        if now<self.next_source_at:return
        self.next_source_at=now+self.app.config.world_source_interval_seconds*SECOND
        for source in self.app.config.world_sources:
            try:
                mid=self.intake.read(source.source_id,observation_id=str(now//(self.app.config.world_source_interval_seconds*SECOND)))
                if source.semantic_format=='SOURCED_CLAIM_JSON':
                    self.intake.process(mid)
                else:
                    topic='source.'+digest(source.source_id)[:24]
                    self.queue.offer(LifeOpportunity(kind='WORLD_CHANGE',topic=topic,source_memory_ids=(mid,),cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CURIOSITY',topic_key=topic,possible_behaviors=('EXPLORE','WATCH','REST'),resource_class='ORDINARY'),expires_at_us=now+DAY))
                self.source_health[source.source_id]='SOURCE_READ_NOT_TRUTH_QUALIFICATION'
            except (CoreError,ValueError,KeyError) as exc:
                if isinstance(exc,CoreError) and exc.code in {'RUNTIME_LEASE_LOST','PRIVACY_ANCHOR_INVALID','PRIVACY_ANCHOR_UNAVAILABLE'}:raise
                self.source_health[source.source_id]=exc.code if isinstance(exc,CoreError) else 'SEMANTIC_FEED_INVALID'

    def collect(self):
        r=self.app.runtime;s=r.store;records=RecordService(s);now=r.clock.utc_now_us()
        candidates=[]
        # Fixed indexed horizons. No full-history replay or synthetic random wish.
        for row in s.db.execute('SELECT * FROM experiences ORDER BY created_at_us DESC LIMIT 8'):
            head=s.one('continuity_records',row['record_id'])
            if not head or head['lifecycle']!='ACTIVE' or head['privacy_class'] not in {'PUBLIC','PROJECT'} or head['scope'] not in r.config.scopes or not records.current_support(head['record_id']):continue
            topic='experience.'+digest(row['experience_id'])[:24]
            candidates.append(LifeOpportunity(kind='EXPERIENCE',topic=topic,reflection_experience_id=row['experience_id'],source_memory_ids=(row['result_memory_id'],row['verification_memory_id']),
                cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='EXPERIENCE_REVIEW',topic_key=topic,possible_behaviors=('REFLECT','WATCH','REST'),resource_class='ORDINARY',behavior_domain='PROJECT'),expires_at_us=row['created_at_us']+3*DAY))
        model=WorldModel(s,scopes=r.config.scopes,privacy_classes=('PUBLIC','PROJECT'))
        for belief in model.snapshot(limit=8):
            if not belief.support_records:continue
            sources=tuple(dict.fromkeys(mid for rid in belief.support_records for mid in records.support(rid)))
            if not 1<=len(sources)<=16:continue
            topic='world.'+digest([belief.entity_id,belief.predicate])[:24]
            candidates.append(LifeOpportunity(kind='WORLD_CHANGE',topic=topic,source_memory_ids=sources,
                cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CURIOSITY',topic_key=topic,possible_behaviors=('EXPLORE','WATCH','REST'),resource_class='ORDINARY',behavior_domain='CREATIVE'),expires_at_us=now+DAY))
        if self.projects:self.projects.offer(self.queue)
        for c in candidates[:16]:
            try:self.queue.offer(c)
            except CoreError as exc:
                if exc.code=='LIFE_QUEUE_BACKPRESSURE':break
                raise
        return len(candidates)

    def opportunity(self):
        r=self.app.runtime;now=r.clock.utc_now_us()
        if r.work.paused:return None
        self.intake_slice()
        if now>=self.next_at:
            self.next_at=now+min(60,self.app.config.world_source_interval_seconds)*SECOND;self.collect()
        # First settle a previous original judgment. Existing goal steps retain
        # priority in LivingWork; this service is reached only at its idle point.
        activity=self.queue.opportunity()
        return activity if activity else self.previous.opportunity() if self.previous else None

    def view(self):
        from ..continuity.open_life.projections import advanced_view
        r=self.app.runtime
        return {**advanced_view(r.store,scope=r.config.scopes[0],privacy=r.config.privacy_classes),'opportunities':self.queue.view(),'world_source_health':dict(self.source_health),'controlled_projects':self.projects.view() if self.projects else []}
