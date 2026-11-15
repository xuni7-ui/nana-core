from pathlib import Path
import argparse,json,os,subprocess,sys,tempfile
from tests.person_self.conftest import initialize
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.life.surfaces import SurfaceBinding
from nana_core.life.bilibili_runtime import BilibiliChannelBinding
from nana_core.nanalink.private_source import PrivateDynamicBridge
from nana_core.nanalink.bilibili_dynamic import normalize_dynamic
from nana_core.nanalink.contracts import Account
parser=argparse.ArgumentParser(description='Synthetic post-withdrawal old-reader qualification')
parser.add_argument('--old-source',required=True,help='Explicit old Git archive containing src/nana_core')
args=parser.parse_args();old=Path(args.old_source).resolve()
assert (old/'src/nana_core/life/application.py').is_file()
with tempfile.TemporaryDirectory(prefix='nanalink-rollback-') as d:
 home=Path(d)/'home';initialize(home);cfg=load_config(home)
 b=SurfaceBinding(binding_id='bili.private',platform='bilibili.account',adapter='bilibili.account',surface='chat.direct',mode='PLATFORM_ADAPTER_NO_SEND',permitted_privacy=('PERSONAL',),allow_personal_retention=True,personal_retention_consent_ref='consent.fixture')
 c=BilibiliChannelBinding(channel_id='bili',binding_id=b.binding_id,account_id=42,target_id=43,sender_id=43,cookie_ref='test.cookie',csrf_ref='test.csrf',enabled=True,read_authorized=True,private_read_authorized=True)
 update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'surface_bindings':(b,),'bilibili_channels':(c,)}),expected_revision=cfg.revision)
 with LifeApplication(home) as app:
  app.pause();ident=app.runtime.identity_id
  row={'id_str':'123','modules':{'module_author':{'mid':43,'pub_ts':1},'module_dynamic':{'desc':{'text':'SYNTHETIC_ROLLBACK_PRIVATE'}}}}
  event=normalize_dynamic(Account(platform='bilibili',adapter_id='bilibili.account',account_id='42'),row,now_us=app.runtime.clock.utc_now_us(),origin='SYNTHETIC_LOOPBACK');bridge=PrivateDynamicBridge(app,'bili');mid=bridge.receive(event)['memory_id'];assert bridge.withdraw(event)
 script='''from nana_core.life.application import LifeApplication\nfrom nana_core.contracts import CoreError\nfrom nana_core.continuity.memory import MemoryService\nimport sys\nwith LifeApplication(sys.argv[1]) as app:\n app.pause();assert app.runtime.identity_id==sys.argv[2]\n try:MemoryService(app.runtime.store).read(sys.argv[3]);raise AssertionError('erased memory visible')\n except CoreError as e:assert e.code=='MEMORY_UNAVAILABLE'\n assert app.runtime.store.one('memories',sys.argv[3])['lifecycle']=='DELETED'\n print('OLD_READER_IDENTITY_MATCH_TOMBSTONE_HONOURED')\n'''
 env=os.environ.copy();env['PYTHONPATH']=str(old/'src');out=subprocess.run([sys.executable,'-c',script,str(home),ident,mid],cwd='/workspace/work',env=env,text=True,capture_output=True,timeout=30);print(json.dumps({'returncode':out.returncode,'stdout':out.stdout.strip(),'stderr_tail':out.stderr[-1500:]},ensure_ascii=False));assert out.returncode==0
