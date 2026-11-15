"""The original resumable scan upgrades old literal-note derived coverage."""
import json
from collections import Counter
import pytest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.memory import MemoryService,NOTE_END_PREFIX,NOTE_GRAM_COMPLETE
from tools.nana_next_experience.memory_diverse_compare import add
from .conftest import initialize


@pytest.mark.parametrize('weekly',[False,True])
@pytest.mark.parametrize('missing_grams',[False,True])
def test_original_bounded_scan_repairs_missing_end_keys_with_old_complete_grams(tmp_path,weekly,missing_grams):
    home=tmp_path/'home';initialize(home,active=0);clock=VirtualClock();repaired=[];term_writes=[]
    def configure(app):
        service=app.runtime.work.maintenance;service.batch=2;service.interval=SECOND;service.privacy_classes=('PUBLIC','PROJECT');service.discover()
        app.runtime.store.db.set_trace_callback(lambda sql:term_writes.append(1) if sql.startswith('INSERT OR IGNORE INTO memory_terms') else None)
        return service
    def run_until(app,predicate):
        for _ in range(160):
            if predicate():return
            before={mid for mid in good if has_end(app.runtime.store,mid)}
            clock.advance(SECOND);app.runtime.lease.heartbeat();activity=app.runtime.work.maintenance.slice()
            fresh={mid for mid in good if has_end(app.runtime.store,mid)}-before;repaired.extend(fresh)
            assert len(fresh)<=2
            if activity:assert activity['read_count']<=2
        assert predicate(),'old complete-gram notes were skipped instead of receiving bounded End coverage'
    def has_end(store,mid):
        return bool(store.db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?',(mid,NOTE_END_PREFIX+'归途')).fetchone())
    with LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;memory=MemoryService(r.store)
        # Align the public fixture prefix to the two-row source slice, so the
        # first repaired slice contains exactly two notes, even when Core has
        # already retained its own source metadata. Do not alter the scan cursor.
        if r.store.db.execute('SELECT coalesce(max(rowid),0) FROM memories').fetchone()[0]%2:
            add(memory,'maintenance-prelude','SYNTHETIC ordinary prelude',entity=r.config.entity_id,scope=r.config.scopes[0],note=False,predicate='maintenance.prelude')
        good=[add(memory,'old-end-'+str(i),'SYNTHETIC note '+str(i)+' 归途',entity=r.config.entity_id,scope=r.config.scopes[0]) for i in range(6)]
        memory.entity('another-owner','PERSON')
        excluded=[add(memory,'old-end-private','SYNTHETIC private 归途',entity=r.config.entity_id,scope=r.config.scopes[0],privacy='PERSONAL'),
            add(memory,'old-end-entity','SYNTHETIC different owner 归途',entity='another-owner',scope=r.config.scopes[0]),
            add(memory,'old-end-scope','SYNTHETIC different scope 归途',entity=r.config.entity_id,scope='another-scope')]
        headers={mid:dict(r.store.one('memories',mid)) for mid in (*good,*excluded)};identity=r.identity_id
        service=configure(app)
        if weekly:
            run_until(app,lambda:r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='SCAN'").fetchone()[0]>=max(r.store.db.execute('SELECT rowid FROM memories WHERE memory_id=?',(mid,)).fetchone()[0] for mid in good))
        for mid in (*good,*excluded):
            assert r.store.db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?',(mid,NOTE_GRAM_COMPLETE)).fetchone()
            r.store.db.execute('DELETE FROM memory_terms WHERE memory_id=? AND term=?',(mid,NOTE_END_PREFIX+'归途'))
        if missing_grams:
            for mid in good:r.store.db.execute('DELETE FROM memory_terms WHERE memory_id=? AND term=?',(mid,NOTE_GRAM_COMPLETE))
        term_writes.clear()
        if not weekly:
            run_until(app,lambda:len(repaired)>=2)
            assert len(repaired)==2 and set(repaired)<=set(good)
        cursor=r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='SCAN'").fetchone()[0]
    if weekly:clock.advance(7*86400*SECOND)
    with LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;service=configure(app)
        assert r.identity_id==identity and r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='SCAN'").fetchone()[0]==cursor
        run_until(app,lambda:all(has_end(r.store,mid) for mid in good))
        assert Counter(repaired)==Counter({mid:1 for mid in good})
        assert len(term_writes)>6 if missing_grams else len(term_writes)==6
        assert all(not has_end(r.store,mid) for mid in excluded)
        assert all(dict(r.store.one('memories',mid))==header for mid,header in headers.items())
        assert not r.store.all('cognitive_requests') and not r.store.all('runtime_cognition_calls') and not r.store.all('actions')
        result=MemoryService(r.store).literal_notes(entity_ids=(r.config.entity_id,),scopes=r.config.scopes,privacy_classes=('PROJECT',),terms=('归途',))
        assert {row['memory_id'] for row in result}==set(good[-4:])
        print(json.dumps({'mode':'weekly' if weekly else 'incremental','repaired':len(repaired),'legacy_grams_missing':missing_grams,'term_write_statements':len(term_writes),'max_source_rows_per_slice':2,'excluded_untouched':len(excluded),'extra_model_calls':0}))


def test_normal_runtime_yields_to_foreground_before_repairing_legacy_end_key(tmp_path):
    from nana_core.presence.contracts import RuntimeEvent,Cause
    from nana_core.continuity.subject import SubjectInput
    home=tmp_path/'home';initialize(home,active=0);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        r=app.runtime;service=r.work.maintenance;service.interval=SECOND;service.discover()
        mid=add(MemoryService(r.store),'normal-runtime-old-end','SYNTHETIC old note 归途',entity=r.config.entity_id,scope=r.config.scopes[0])
        tail=NOTE_END_PREFIX+'归途';r.store.db.execute('DELETE FROM memory_terms WHERE memory_id=? AND term=?',(mid,tail))
        def covered():return bool(r.store.db.execute('SELECT 1 FROM memory_terms WHERE memory_id=? AND term=?',(mid,tail)).fetchone())
        cursor=r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='SCAN'").fetchone()[0]
        clock.advance(2*SECOND);r.lease.heartbeat()
        incoming=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.cache-upgrade-user-priority',kind='INTERACTION',origin='USER',
            entity_id=r.config.entity_id,scope=r.config.scopes[0],privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,))
        r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=incoming,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=clock.utc_now_us(),priority=3))
        first=r.step();assert first['cycle'].intention.self_generated is False
        assert not covered() and r.store.db.execute("SELECT cursor FROM jobs WHERE work_kind='SCAN'").fetchone()[0]==cursor
        for _ in range(120):
            if covered():break
            clock.advance(SECOND);r.lease.heartbeat();r.step()
        assert covered()
        assert not r.store.all('cognitive_requests') and not r.store.all('runtime_cognition_calls') and not r.store.all('actions')
