import argparse,json,sys,hashlib,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--input',type=Path,default=Path('/dev/shm/nana-pts-native-281/source.ts'));a=p.parse_args();sys.dont_write_bytecode=True;sys.path.insert(0,str(a.source_root))
from nana_core.continuity.world_loop.perception import MediaDecoder
import nana_core.continuity.world_loop.perception as module
from nana_core.contracts import CoreError
source=a.input;data=source.read_bytes();calls=[];original=MediaDecoder._run
class Observed(MediaDecoder):
 def _run(self,args,**kw):
  raw=original(self,args,**kw);calls.append({'program':args[0],'output_bytes':len(raw)});return raw
started=time.perf_counter();cpu=time.process_time()
try:decoded=Observed().decode(data,'VIDEO');error=None
except CoreError as exc:decoded=None;error=exc.code
report={'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),'actual_decoder_source':module.__file__,'error':error,'decoded':decoded,'processes':calls,'elapsed_seconds':time.perf_counter()-started,'cpu_seconds':time.process_time()-cpu,'provider_calls':0,'temporary_public_bytes_only':True};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='decoded'}))
