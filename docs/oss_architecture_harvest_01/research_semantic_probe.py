# Research only: offline fixed public snapshots; not Nana implementation.
import ast,json,re,subprocess,sys,tempfile,asyncio,logging
from pathlib import Path
from datetime import datetime,timezone
root=Path(sys.argv[1]).resolve();results=[]
for repo,expected in {'getzep/graphiti': 'd50741d1bf463cbe3859eb73914cbff1b66839e6', 'yuri-os/YuriOS': 'cd4d1f16ae095f0f694dbbe7b1aac8e33db25367'}.items():
 p=root/repo.replace('/','__')
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip()==expected, 'RESEARCH_SOURCE_SHA_MISMATCH'
 assert subprocess.run(['git','diff','--quiet','HEAD','--'],cwd=p).returncode==0, 'RESEARCH_SOURCE_DIRTY'

def load(repo,file,names,scope):
 tree=ast.parse((root/repo.replace('/','__')/file).read_text())
 nodes=[]
 for n in tree.body:
  key=n.name if isinstance(n,(ast.FunctionDef,ast.ClassDef)) else n.targets[0].id if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) else None
  if key in names:nodes.append(n)
 assert len(nodes)==len(names)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),scope)
def check(name,ok):
 assert ok,name
 results.append({'check':name,'result':'PASS'})
g={'re':re,'datetime':datetime,'timezone':timezone}
load('getzep/graphiti','graphiti_core/utils/datetime_utils.py',{'ensure_utc'},g)
load('getzep/graphiti','graphiti_core/utils/maintenance/temporal_edge_utils.py',{'_FUTURE_ASSERTION_RE','_DEADLINE_RE','_ONGOING_STATE_END_RE','normalize_future_temporal_bounds'},g)
f=g['normalize_future_temporal_bounds'];ref=datetime(2026,1,1,tzinfo=timezone.utc);future=datetime(2026,1,2,tzinfo=timezone.utc)
check('Graphiti: future plan assertion starts at reference time',f('I will go to Tokyo tomorrow',ref,future,None)==(ref,None))
check('Graphiti: soft deadline is not fact invalidation',f('We will finish by tomorrow',ref,future,future)==(ref,None))
check('Graphiti: ongoing unavailability retains end',f('We will be unavailable until tomorrow',ref,None,future)==(ref,future))
check('Graphiti: completed event date stays distinct',f('We visited Tokyo',ref,future,None)==(future,None))
check('Graphiti: naive UTC is assumed, not rejected',g['ensure_utc'](datetime(2026,1,1))==ref)
y={'dataclass':__import__('dataclasses').dataclass,'field':__import__('dataclasses').field,'dt_of':lambda ts:datetime.fromtimestamp(ts,timezone.utc),'Clock':object}
load('yuri-os/YuriOS','yurios/mind/policy.py',{'InterruptDecision','quiet_hour','score_interrupt'},y)
y.update(QUIET_FROM=22,QUIET_UNTIL=9)
class Clock:
 def __init__(self,h):self.h=h
 def now(self):return datetime(2026,1,1,self.h,tzinfo=timezone.utc).timestamp()
def interrupt(h,cap=0,decided=False):return y['score_interrupt'](clock=Clock(h),relevance=1,time_sensitivity=1,last_contact_out=None,interrupts_today=cap,max_interrupts_per_day=2,threshold=.5,decided=decided)
check('YuriOS: quiet hours veto decided interruption',interrupt(23,decided=True).outcome=='SILENT')
check('YuriOS: daily cap veto decided interruption',interrupt(12,cap=2,decided=True).outcome=='SILENT')
check('YuriOS: decided open-window line is suggestion',interrupt(12,decided=True).outcome=='SUGGEST')
check('YuriOS: low worthiness remains silent',y['score_interrupt'](clock=Clock(12),relevance=0,time_sensitivity=0,last_contact_out=Clock(12).now(),interrupts_today=0,max_interrupts_per_day=2,threshold=.9).outcome=='SILENT')
with tempfile.TemporaryDirectory(prefix='nana-oss-gap-') as d:
 p=Path(d)/'external-effect.txt'
 code="import pathlib,sys,os;p=pathlib.Path(sys.argv[1]);p.write_text(p.read_text()+'effect\\n' if p.exists() else 'effect\\n');os._exit(23)"
 for _ in range(2):
  r=subprocess.run([sys.executable,'-c',code,str(p)],capture_output=True)
  assert r.returncode==23
 check('Abstract effect-before-checkpoint crash/retry duplicates effect (not a framework test)',len(p.read_text().splitlines())==2)
# Confirm a pinned-source mismatch between DREAM's comment and failure bookkeeping.
dg={'asyncio':asyncio,'Clock':object,'MindVault':object,'UtilityCall':object,'InferenceBusy':type('InferenceBusy',(Exception,),{}),'log':logging.getLogger('research.expected_failure')}
dg['log'].disabled=True
dg.update(day_of=lambda ts:datetime.fromtimestamp(ts,timezone.utc).date().isoformat(),utc_iso_of=lambda ts:datetime.fromtimestamp(ts,timezone.utc).isoformat())
def read_json(p,default):return json.loads(p.read_text()) if p.exists() else default
def write_json(p,obj):p.write_text(json.dumps(obj))
dg.update(read_json=read_json,write_json=write_json)
dg['datetime']=__import__('datetime')
load('yuri-os/YuriOS','yurios/mind/journal.py',{'canonical_day','is_canonical_day'},dg)
load('yuri-os/YuriOS','yurios/mind/dream.py',{'_BOOKKEEPING','keep_fact','ConsolidationReport','DreamConsolidator'},dg)
with tempfile.TemporaryDirectory(prefix='nana-oss-dream-') as d:
 v=Path(d);(v/'memory/episodic').mkdir(parents=True);(v/'state').mkdir();(v/'memory/episodic/2026-01-01.md').write_text('synthetic day')
 class Vault:
  vault=v
  def mark_dirty(self):pass
 class FakeClock:
  def now(self):return datetime(2026,1,3,tzinfo=timezone.utc).timestamp()
 async def failing_utility(messages):raise RuntimeError('synthetic provider unavailable')
 dream=dg['DreamConsolidator'](Vault(),object(),FakeClock(),utility=failing_utility)
 rep=asyncio.run(dream.consolidate())
 check('YuriOS pinned DREAM: generic utility failure returns no facts but marks day processed',rep.days_processed==['2026-01-01'] and dream.backlog()==[])
report={'scope':'11 isolated semantic/abstract checks, including observed upstream failure-bookkeeping behavior; NOT upstream full suites; NOT Nana qualification','passed':len(results),'failed':0,'real_models':0,'production':0,'checks':results,'dependencies':'stdlib only; selected reviewed AST nodes, no upstream package imports','framework_services_started':0}
(root/'semantic_probes.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
