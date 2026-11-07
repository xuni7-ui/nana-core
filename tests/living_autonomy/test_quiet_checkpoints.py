"""No-change housekeeping is operational; original C/source work remains durable."""
import json
from nana_core.presence.contracts import SECOND,ScheduleSpec
from nana_core.contracts import CoreError
from .helpers import fresh,event


def test_builtin_review_and_empty_scan_do_not_invent_experiences_but_custom_schedule_is_durable(tmp_path):
    with fresh(tmp_path/'self.db',review_interval_us=SECOND) as runtime:
        before=len(runtime.store.all('events'))
        for n in range(10):runtime.clock.source.advance(SECOND);runtime.step()
        assert len(runtime.store.all('events'))==before+1 # actual scan-job creation
        assert not runtime.store.all('subject_events') and not runtime.store.all('runtime_queue')
        checks=json.loads(runtime.store.one('core_meta','runtime.routine_review')['value_json'])
        assert checks['checks']==10 and checks['pending'] is False and checks['authority'] is False
        custom=event(runtime,'custom-calendar',background=True)
        custom=custom.model_copy(update={'event_type':'TIME_EVENT','trigger':'TIME_TRIGGER'})
        runtime.scheduler.add(ScheduleSpec(dedupe_key='custom-maintenance',kind='PERIODIC',due_at_us=runtime.clock.utc_now_us(),interval_us=SECOND,event=custom))
        runtime.step()
        assert runtime.store.db.execute("SELECT 1 FROM runtime_queue WHERE source_key=?",(custom.input.source_key,)).fetchone() is None
        assert runtime.store.all('runtime_queue') and runtime.store.all('subject_events')
        assert not runtime.store.all('runtime_cognition_calls')


def test_pending_c_owned_check_survives_restart_without_new_input_or_model(tmp_path):
    path=tmp_path/'self.db'
    with fresh(path,review_interval_us=SECOND) as runtime:
        identity=runtime.identity_id;clock=runtime.clock.source
        clock.advance(SECOND);runtime.lease.heartbeat();runtime.scheduler.due()
        assert runtime.scheduler.routine_pending()
        count=len(runtime.store.all('subject_events'))
    with fresh(path,clock=clock,review_interval_us=SECOND) as runtime:
        assert runtime.identity_id==identity and runtime.scheduler.routine_pending()
        runtime.step()
        assert not runtime.scheduler.routine_pending()
        assert len(runtime.store.all('subject_events'))==count
        assert not runtime.store.all('runtime_cognition_calls')


def test_empty_scan_keeps_durable_cursor_and_growth_hook_without_periodic_journal(tmp_path):
    with fresh(tmp_path/'self.db') as runtime:
        maintenance=runtime.work.maintenance;maintenance.interval=SECOND
        maintenance.discover();before=len(runtime.store.all('events'))
        job=runtime.store.db.execute("SELECT * FROM jobs WHERE work_kind='SCAN'").fetchone()
        for n in range(10):
            runtime.clock.source.advance(SECOND);runtime.lease.heartbeat()
            result=maintenance.slice()
            assert result['read_count']==0 and result['operational_only']
        after=runtime.store.one('jobs',job['job_id'])
        assert (after['cursor'],after['revision'])==(job['cursor'],job['revision'])
        assert after['due_at_us']>runtime.clock.utc_now_us()
        assert len(runtime.store.all('events'))==before


def test_storage_profile_separates_file_lengths_allocated_blocks_and_json_bytes(tmp_path):
    from nana_core.life.durability import profile
    from pathlib import Path
    with fresh(tmp_path/'self.db') as runtime:
        with runtime.store.transaction('synthetic.profile_unicode',{'text':'公开合成片段🌙'}):pass
        view=profile(runtime.store)
        paths=[Path(str(runtime.store.path)+suffix) for suffix in ('','-wal','-shm','.privacy.json')]
        paths.append(runtime.store.privacy.path)
        allocations={(p.stat().st_dev,p.stat().st_ino):p.stat().st_blocks*512 for p in paths if p.exists()}
        assert view['allocated_family_bytes']==sum(allocations.values())
        assert view['file_length_measurement']=='STAT_ST_SIZE_NOT_ALLOCATED_BLOCKS'
        row=runtime.store.db.execute("SELECT length(CAST(data_json AS BLOB)) FROM events WHERE kind='synthetic.profile_unicode'").fetchone()
        found=next(r for r in view['event_kinds'] if r['kind']=='synthetic.profile_unicode')
        assert found['json_bytes']==row[0]
