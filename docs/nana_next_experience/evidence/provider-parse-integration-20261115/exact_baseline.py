import ast, json, subprocess, tempfile
from pathlib import Path
from tools.nana_next_experience.experiments import provider_config_cache as bench
import nana_core.continuity.provider_config as module
source=subprocess.check_output(['git','show','5d4457e5551aaf6fdbe5e34c4fa7045d1b7b1478:src/nana_core/continuity/provider_config.py'],text=True)
tree=ast.parse(source)
node=next(n for n in next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProviderConfigService').body if isinstance(n,ast.FunctionDef) and n.name=='_load')
namespace=dict(vars(module))
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])), '<exact-5d4457e-_load>', 'exec'),namespace)
bench.BaselineConfigService._load=namespace['_load']
with tempfile.TemporaryDirectory(prefix='nana-pr17-',dir='/tmp') as folder:
 home=Path(folder);home.chmod(0o700);raw=bench.document(8,32).model_dump_json().encode()
 p=home/'providers.json';p.write_bytes(raw);p.chmod(0o600)
 bench._validated_configuration.cache_clear()
 result=bench.comparison(lambda:bench.baseline_status(home),lambda:bench.provider_status(home))
 print(json.dumps({'baseline':'5d4457e5551aaf6fdbe5e34c4fa7045d1b7b1478','candidate':'30459c54564c3e246d92e1c8e97f2ec2df4b9409','input_bytes':len(raw),'providers':8,'models':32,'comparison':result,'network_calls':0,'model_calls':0,'actual_provider_tokens':None},indent=2))
