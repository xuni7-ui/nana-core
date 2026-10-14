"""Whole-subject causal acceptance, not a fixture asserting its own answer."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from nana_core.continuity.subject.simulation import run


def test_ten_day_counterfactual_and_sixty_day_life(tmp_path):
    report = run(tmp_path/'life', days=60)
    assert all(report['checks'].values()), report['checks']
    worlds = report['worlds']
    assert worlds['normal']['day6']['intention']['kind'] == 'EXPLORE'
    assert worlds['without_preference']['day6']['intention']['kind'] == 'NO_ACTION'
    assert not worlds['without_preference']['preferences_after_game']
    assert worlds['normal']['day9']['deliberation']['raw_proposal_json'] != worlds['without_lesson']['day9']['deliberation']['raw_proposal_json']
    assert worlds['normal']['experience_outcome'] == worlds['without_lesson']['experience_outcome'] == 'FAILURE'
    # Matched worlds share exact initial identity, memories, commitments and
    # project records by backup, not merely the same identity label in a prompt.
    assert len({v['before_restart']['identity']['identity_id'] for v in worlds.values()}) == 1
    assert worlds['normal']['trace'][:4] == worlds['without_preference']['trace'][:4] == worlds['without_lesson']['trace'][:4]
    assert report['soak']['max_pending'] <= 8 and report['soak']['max_hot_state_bytes'] < 16384
    assert report['real_model_calls'] == report['real_external_actions'] == 0


CHILD = r'''
import json,signal,sys
from pathlib import Path
from nana_core.clock import ManualClock
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import SubjectLoop,SubjectInput,PreferenceSignal
from nana_core.storage.sqlite_store import Transaction
path, marker, mode = sys.argv[1:]
clock=ManualClock()
with ContinuityStore(path,clock) as store:
 IdentityService(store,OperatorAuthority())
 MemoryService(store).entity('synthetic-person','PERSON')
 loop=SubjectLoop(store,scopes=('life',))
 event=SubjectInput(source_key='synthetic.kill.experience',kind='PLAY',origin='ENVIRONMENT',
  entity_id='synthetic-person',scope='life',text='A fictional new route was useful',
  observed_at_us=clock.utc_now_us(),occurred_at_us=clock.utc_now_us(),
  preference_signal=PreferenceSignal(topic='exploration',direction='SUPPORT',interpretation='New direct occurrence'))
 if mode == 'during':
  original=Transaction.put
  def put(tx,table,row):
   original(tx,table,row)
   if table=='assertion_signals':
    Path(marker).write_text('transaction_open')
    while True: signal.pause()
  Transaction.put=put
 result=loop.run(event)
 if mode=='after':
  Path(marker).write_text('committed')
  while True: signal.pause()
 print(json.dumps({'identity':store.identity['identity_id'],'revision':loop.revision,
  'cycles':len(store.all('subject_cycles')),'signals':len(store.all('assertion_signals')),
  'replayed':result.replayed,'action_counts':[len(store.all(t)) for t in ('actions','attempts','grants','budgets')],
  'integrity':store.db.execute('PRAGMA integrity_check').fetchone()[0]}))
'''


@pytest.mark.parametrize('cut', ('during','after'))
def test_actual_sigkill_subject_transaction_no_duplicate(tmp_path, cut):
    path, marker = tmp_path/'self.db', tmp_path/'ready'
    process = subprocess.Popen([sys.executable,'-c',CHILD,str(path),str(marker),cut], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        limit=time.monotonic()+15
        while not marker.exists() and process.poll() is None and time.monotonic()<limit:
            time.sleep(.01)
        assert marker.exists(), process.communicate(timeout=2)
        os.kill(process.pid,signal.SIGKILL)
        process.communicate(timeout=10)
        assert process.returncode == -signal.SIGKILL
    finally:
        if process.poll() is None:
            process.kill();process.communicate(timeout=10)
    reopened=subprocess.run([sys.executable,'-c',CHILD,str(path),str(marker),'recover'],capture_output=True,text=True,check=True,timeout=15)
    result=json.loads(reopened.stdout)
    assert result['revision']==result['cycles']==result['signals']==1
    assert result['replayed'] == (cut=='after')
    assert result['integrity']=='ok' and not any(result['action_counts'])
    again=subprocess.run([sys.executable,'-c',CHILD,str(path),str(marker),'recover'],capture_output=True,text=True,check=True,timeout=15)
    assert json.loads(again.stdout)['replayed']
