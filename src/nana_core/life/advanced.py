"""Bounded, opt-in advanced attention at the original D opportunity safe point."""
from ..storage import digest
from ..contracts import CoreError
from ..continuity.records import RecordService
from ..continuity.open_life.opportunities import OpportunityQueue,LifeOpportunity
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.world_loop.world import WorldModel
from ..presence.contracts import DAY,SECOND


class AdvancedLife:
    def __init__(self,app,previous):
        self.app,self.previous=app,previous;self.queue=OpportunityQueue(app.runtime);self.next_at=0

    def collect(self):
        r=self.app.runtime;s=r.store;records=RecordService(s);now=r.clock.utc_now_us()
        candidates=[]
        # Fixed indexed horizons. No full-history replay or synthetic random wish.
        for row in s.db.execute('SELECT * FROM experiences ORDER BY created_at_us DESC LIMIT 8'):
            head=s.one('continuity_records',row['record_id'])
            if not head or head['lifecycle']!='ACTIVE' or head['privacy_class'] not in {'PUBLIC','PROJECT'} or head['scope'] not in r.config.scopes or not records.current_support(head['record_id']):continue
            topic='experience.'+digest(row['experience_id'])[:24]
            candidates.append(LifeOpportunity(kind='EXPERIENCE',topic=topic,source_memory_ids=(row['result_memory_id'],row['verification_memory_id']),
                cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='EXPERIENCE_REVIEW',topic_key=topic,possible_behaviors=('REFLECT','WATCH','REST'),resource_class='ORDINARY',behavior_domain='PROJECT'),expires_at_us=row['created_at_us']+3*DAY))
        model=WorldModel(s,scopes=r.config.scopes,privacy_classes=('PUBLIC','PROJECT'))
        for belief in model.snapshot(limit=8):
            if not belief.support_records:continue
            sources=tuple(dict.fromkeys(mid for rid in belief.support_records for mid in records.support(rid)))
            if not 1<=len(sources)<=16:continue
            topic='world.'+digest([belief.entity_id,belief.predicate])[:24]
            candidates.append(LifeOpportunity(kind='WORLD_CHANGE',topic=topic,source_memory_ids=sources,
                cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CURIOSITY',topic_key=topic,possible_behaviors=('EXPLORE','WATCH','REST'),resource_class='ORDINARY',behavior_domain='CREATIVE'),expires_at_us=now+DAY))
        for c in candidates[:16]:
            try:self.queue.offer(c)
            except CoreError as exc:
                if exc.code=='LIFE_QUEUE_BACKPRESSURE':break
                raise
        return len(candidates)

    def opportunity(self):
        r=self.app.runtime;now=r.clock.utc_now_us()
        if r.work.paused:return None
        if now>=self.next_at:
            self.next_at=now+60*SECOND;self.collect()
        # First settle a previous original judgment. Existing goal steps retain
        # priority in LivingWork; this service is reached only at its idle point.
        activity=self.queue.opportunity()
        return activity if activity else self.previous.opportunity() if self.previous else None

    def view(self):
        from ..continuity.open_life.projections import advanced_view
        r=self.app.runtime
        return {**advanced_view(r.store,scope=r.config.scopes[0],privacy=r.config.privacy_classes),'opportunities':self.queue.view()}
