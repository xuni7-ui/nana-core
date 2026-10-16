# Research only: offline fixed public snapshots; not Nana implementation.
import importlib.util,socket,ssl,urllib.request,unittest,sys,io,json,time
from pathlib import Path
research_root=Path(sys.argv[1]).resolve()
root=research_root/'huodebing-alt__anima'
import subprocess
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='ba215ce72bcaedd147d5d08de6e54555a62952c1', 'RESEARCH_SOURCE_SHA_MISMATCH'
assert subprocess.run(['git','diff','--quiet','HEAD','--'],cwd=root).returncode==0, 'RESEARCH_SOURCE_DIRTY'

def deny(*a,**kw):raise AssertionError('RESEARCH_NO_NETWORK')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny;urllib.request.urlopen=deny
sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location('reviewed_anima_store_tests',root/'tests/test_store.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
log=io.StringIO();start=time.monotonic();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
(research_root/'anima_tests.txt').write_text(log.getvalue())
report={'suite':'huodebing-alt/anima tests/test_store.py','passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.monotonic()-start,4),'network_calls':0,'LLM_calls':0,'guard':'socket connect + urllib urlopen reject; reviewed temp-store suite only','python':sys.version.split()[0]}
(research_root/'anima_tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert result.wasSuccessful()
