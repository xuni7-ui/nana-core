"""Generated fields checked against locked Iris 0.3.0; no private legacy records."""
import json
from .iris import IrisRecord,ClaimAnnotation


def fixtures():
    rows=[('l1','m1',{'role':'user','content':'Fictional reader likes paper gardens.','timestamp':'2026-09-01T00:00:00Z','token_count':8,'source':'synthetic-chat','metadata':{'message_id':'synthetic-m1'},'persona_id':'synthetic-nana'}),
          ('l1','m2',{'role':'user','content':'Fictional reader now dislikes paper gardens.','timestamp':'2026-09-02T00:00:00Z','token_count':9,'source':'synthetic-chat','metadata':{'message_id':'synthetic-m2'},'persona_id':'synthetic-nana'}),
          ('l2','summary',{'id':'synthetic-summary','content':'A model summarized a fictional paper garden preference.','metadata':{'source':'l1_summary','timestamp':'2026-09-01T00:00:00','confidence':.95,'group_id':'synthetic-chat'},'persona_id':'synthetic-nana'}),
          ('l2','inference',{'id':'synthetic-inference','content':'A model inferred an interest in paper gardens.','metadata':{'source':'tool','confidence':1.0},'persona_id':'synthetic-nana'}),
          ('l2_row','sql',{'faiss_idx':1,'memory_id':'synthetic-sql','content':'Synthetic SQL memory.','metadata':'{"source":"l1_summary","timestamp":"2026-09-01T00:00:00"}','timestamp':'2026-09-01T00:00:00','group_id':'synthetic-chat','user_id':None,'kg_processed':0,'persona_id':'synthetic-nana'}),
          ('kg_node','person',{'id':'synthetic-person','label':'Person','name':'Fictional Reader','content':'An invented person.','created_time':'2026-09-01T00:00:00Z','source_memory_id':'synthetic-summary','group_id':'synthetic-chat','properties':{}}),
          ('kg_node','garden',{'id':'synthetic-garden','label':'Preference','name':'Paper Garden','content':'An invented garden.','created_time':'2026-09-01T00:00:00Z','source_memory_id':'synthetic-summary','group_id':'synthetic-chat','properties':{}}),
          ('kg_edge','relation',{'source_id':'synthetic-person','target_id':'synthetic-garden','relation_type':'LIKES','weight':1.,'confidence':1.,'created_time':'2026-09-01T00:00:00Z','source_memory_id':'synthetic-summary','properties':{}}),
          ('user_profile','profile',{'user_id':'synthetic-reader','user_name':'Fictional Reader','version':1,'interests':['paper gardens'],'favorability':70.,'bot_relationship':'fictional companion','field_meta':{'interests':{'confidence':1.,'source':'llm','last_updated':'2026-09-01T00:00:00'}},'custom_fields':{}}),
          ('group_profile','group',{'group_id':'synthetic-chat','group_name':'Fictional Garden','version':1,'interests':['paper'],'field_meta':{}}),
          ('action_ledger','ledger',{'key':'synthetic-mode','state':'VERIFIED','updated_at':'2026-09-01 08:00:00+08:00','first_at':'2026-09-01 08:00:00+08:00','revision':1,'op':'synthetic','verify':'old human note; not Core verification','actor':'synthetic-operator','note':None}),
          ('decision_log','decision',{'t':'2026-09-01 08:00:00+08:00','t_utc':'2026-09-01T00:00:00Z','tier':'normal','reason':'synthetic','query':'paper garden','top_k':3,'hits':1,'route':'normal','soft_confirm':False}),
          ('conversation_flow','flow',{'ts':'2026-09-01T00:00:00Z','ts_cst':'2026-09-01 08:00:00+08:00','umo':'synthetic-chat','role':'assistant','sender_id':'synthetic-nana','sender_name':'Synthetic Nana','text':'An invented reply.'}),
          ('index_meta','index',{'version':1,'embedding_model':'synthetic-no-embedding','embedding_dimensions':4,'persona_id':'synthetic-nana','free_list':[]})]
    records=[]
    for kind,key,row in rows:
        annotation=ClaimAnnotation(subject='synthetic:reader',predicate='prefers',value='paper-gardens',polarity=key=='m1') if key in {'m1','m2'} else None
        records.append(IrisRecord(synthetic_only=True,dataset_id='synthetic:iris-schema-v030',kind=kind,legacy_key=key,
            raw_json=json.dumps(row,ensure_ascii=False),annotation=annotation))
    return tuple(records)
