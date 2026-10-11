import hashlib,inspect,json,sys
sys.path.insert(0,'/workspace/nana-core/src')
import pydantic
from nana_core.contracts import DTO,Observation,GrantSpec
from nana_core import contracts
from nana_core.semantic import contracts as semantic
from nana_core.migration import legacy,iris
from nana_core.integration import contracts as host,shadow
mods=[contracts,semantic,legacy,iris,host,shadow]
schemas={m.__name__+'.'+n:c.model_json_schema() for m in mods for n,c in vars(m).items() if inspect.isclass(c) and issubclass(c,DTO) and c.__module__==m.__name__}
o=Observation(source_namespace='synthetic.contract',object_id='one',raw_text='Fictional probe')
assert Observation.model_validate_json(o.model_dump_json())==o
errors=[]
for extra in [{'object_id':4},{'execution_success':True}]:
 try:Observation.model_validate({**o.model_dump(),**extra})
 except pydantic.ValidationError as e:errors.append([x['type'] for x in e.errors()])
 else:raise AssertionError('strict/extra unexpectedly accepted')
try:o.object_id='changed'
except pydantic.ValidationError as e:errors.append([x['type'] for x in e.errors()])
else:raise AssertionError('frozen DTO changed')
body={'schemas':schemas,'serialized_observation':o.model_dump(mode='json'),'invalid_input_errors':errors}
print(json.dumps({'pydantic':pydantic.__version__,'DTO_schema_count':len(schemas),'contract_hash':hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'strict_errors':errors}))
