import sys,json,hashlib
sys.path.insert(0,sys.argv[1])
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.world_loop.cognition import proposal_schema
value=SubjectInput(source_key='synthetic.legacy-method-none',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=123456)
hashvalue=lambda item:hashlib.sha256(json.dumps(item,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print(json.dumps({'legacy_subject_input_sha':hashvalue(value.model_dump(mode='json')),'ordinary_model_schema_sha':hashvalue(proposal_schema()),'self_model_schema_sha':hashvalue(proposal_schema(internal=True))},sort_keys=True))
