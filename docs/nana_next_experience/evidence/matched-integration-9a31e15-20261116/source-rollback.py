"""Fresh synthetic source -> original withdrawal -> stopped 9a/fee8/9a."""
import json,sys,subprocess
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp/n9a/src')
from nana_core.life.config import LifeConfig,write_config
from nana_core.continuity.project_work.service import material_for
from nana_core.life.application import LifeApplication
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.life.surfaces import SurfaceBinding
from nana_core.nanalink.contracts import Account
from nana_core.nanalink.bilibili_dynamic import normalize_dynamic
from nana_core.nanalink.private_source import PrivateDynamicBridge
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
root=Path('/tmp/r9a');root.mkdir(mode=0o700);home=root/'home';bundle=Path('/tmp/n9a')
material=lambda name:material_for(bundle,'src/nana_core/continuity/'+name)
binding=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',
 mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,personal_retention_consent_ref='consent.fixture')
channel=BilibiliChannelBinding(channel_id='bili',binding_id=binding.binding_id,account_id=42,target_id=43,sender_id=43,
 cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
write_config(home,LifeConfig(project_root=str(bundle),materials=(material('recurrence.py'),),practice=material('identity.py'),
 heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),max_autonomous_materials=0,
 surface_bindings=(binding,),bilibili_channels=(channel,)))
class Own:
 descriptor='synthetic-reader-compatibility'
 def propose(self,request):
  value=json.loads(AnalyticalFixturePort().propose(request));value['private_tendency']={
   'topic':'reader-continuity','tendency':'SYNTHETIC own continuing curiosity, independent of the platform source.'}
  return json.dumps(value)
with LifeApplication(home) as app:
 app.pause();r=app.runtime
 event=normalize_dynamic(Account(platform='bilibili',adapter_id='bilibili.account',account_id='42'),
  {'id_str':'123','modules':{'module_author':{'mid':43,'pub_ts':1},'module_dynamic':{'desc':{'text':'SYNTHETIC retained source'}}}},
  now_us=r.clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK')
 source=PrivateDynamicBridge(app,'bili').receive(event)['memory_id']
 r.subject.cognize(SubjectInput(source_key='synthetic.reader-own',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
  scope='project-work',privacy_class='PROJECT',topic='reader-continuity',observed_at_us=r.clock.utc_now_us()),model=Own(),authority=r.authority,policy=app.policy)
 app.forget(source)
 (root/'seed.json').write_text(json.dumps({'identity':r.identity_id,'source':source}))
results=[]
for name,slot in [('before','/tmp/n9a'),('old','/tmp/nfee8'),('return','/tmp/n9a')]:
 done=subprocess.run([slot+'/.venv/bin/python','-I','/workspace/nana-9a-stopped-reader.py','--bundle',slot,'--home',str(home)],capture_output=True,text=True)
 Path('/workspace/nana-9a-source-reader-'+name+'.txt').write_text(done.stdout+done.stderr)
 assert done.returncode==0,done.stderr
 results.append(json.loads(done.stdout))
assert results[0]==results[1]==results[2]
report={'source':'9a31e15ff490559fda95c89f5cf379f67d8c0f8e','old_reader':'fee8f422a667ec42f2dd608472d3617ad2b14e89',
 'same_identity_lineage_private_revision_and_content_digest':True,'source_withdrawn_before_old_reader':True,
 'withdrawn_source_rejected_all_three':True,'counts_unchanged_during_binary_return':results[0]['counts'],
 'real_model_calls':0,'real_platform_calls':0,'production_changed':False,'scope':'STOPPED_SYNTHETIC_DEV_NOT_266_OR_PRODUCTION'}
Path('/workspace/nana-9a-source-rollback.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
