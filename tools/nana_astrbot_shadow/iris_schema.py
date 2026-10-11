"""Metadata-only frozen SQLite inspector, exact query gate plus authorizer.

No Iris import, KV/profile/L1 values, application SELECT, defaults, schema SQL,
index reconstruction, memory writing or model calls. Live WAL snapshots refused.
"""
import sqlite3
import time
from pathlib import Path
from tools.nana_host_shadow.safety import checked_path,digest

UPSTREAM='0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6'
# Field/type contract from locked L2 adapter.py:728-739, L3 adapter.py:75-103.
EXPECTED={
 'memories':{'faiss_idx':'INTEGER','memory_id':'TEXT','content':'TEXT','metadata':'TEXT','group_id':'TEXT','user_id':'TEXT','timestamp':'TEXT','kg_processed':'INTEGER','persona_id':'TEXT'},
 'nodes':{'id':'TEXT','label':'TEXT','name':'TEXT','content':'TEXT','confidence':'REAL','access_count':'INTEGER','last_access_time':'TEXT','created_time':'TEXT','source_memory_id':'TEXT','group_id':'TEXT','properties':'TEXT'},
 'edges':{'source_id':'TEXT','target_id':'TEXT','relation_type':'TEXT','weight':'REAL','confidence':'REAL','access_count':'INTEGER','last_access_time':'TEXT','created_time':'TEXT','source_memory_id':'TEXT','properties':'TEXT'}}
EXPECTED_PK={'memories':{'faiss_idx':1},'nodes':{'id':1},'edges':{'source_id':1,'target_id':2,'relation_type':3}}
EXPECTED_NOT_NULL={'memories':{'memory_id','content','metadata','persona_id'},'nodes':{'label','name'},'edges':{'source_id','target_id','relation_type'}}
MODULES={
 'L1':'iris_memory/l1_buffer/models.py', 'L2':'iris_memory/l2_memory/adapter.py',
 'L3_KG':'iris_memory/l3_kg/adapter.py','profile':'iris_memory/profile/storage.py'}
INDEX_NAMES={'sqlite_autoindex_memories_1','sqlite_autoindex_nodes_1','sqlite_autoindex_edges_1',
 'idx_memories_group_id','idx_memories_user_id','idx_memories_kg_processed','idx_memories_timestamp','idx_memories_persona_id',
 'idx_nodes_label_name','idx_nodes_group','idx_nodes_source_mem','idx_edges_source','idx_edges_target'}
TABLES="SELECT name FROM sqlite_schema WHERE type='table' AND name IN ('memories','nodes','edges') ORDER BY name"
COLUMNS='SELECT name,type,"notnull",pk FROM pragma_table_info(?)'
INDEXES='SELECT name,"unique",origin,partial FROM pragma_index_list(?)'
VERSION='PRAGMA user_version'

class SchemaPolicyError(ValueError):
    def __init__(self):super().__init__('BLOCKED_SCHEMA_INSPECTION_POLICY')

class SchemaInspector:
    def __init__(self,path):
        self.path=checked_path(path)
        if any(Path(str(self.path)+suffix).exists() for suffix in ('-wal','-journal','-shm')):
            raise ValueError('UNKNOWN_FROZEN_SCHEMA_SNAPSHOT_REQUIRED')
        self._db=sqlite3.connect(self.path.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            self._db.execute('PRAGMA query_only=ON')
            self._db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,256*1024)
            self._db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,8192)
            self._deadline=time.monotonic()+2
            self._db.set_progress_handler(lambda:int(time.monotonic()>self._deadline),1000)
            self._query_kind=None
            self._db.set_authorizer(self._authorize)
        except BaseException:self._db.close();raise
    def _authorize(self,action,table,column,database,trigger):
        if self._query_kind is None:return sqlite3.SQLITE_DENY
        if trigger is not None or database not in {None,'main'}:return sqlite3.SQLITE_DENY
        if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
        if action==sqlite3.SQLITE_READ:
            allowed={'sqlite_master':{'name','type'},'sqlite_schema':{'name','type'},
                     'pragma_table_info':{'name','type','notnull','pk'},'pragma_index_list':{'name','unique','origin','partial'}}
            return sqlite3.SQLITE_OK if table in allowed and column in allowed[table] else sqlite3.SQLITE_DENY
        if action==sqlite3.SQLITE_PRAGMA:
            if self._query_kind==VERSION and table=='user_version' and column is None:return sqlite3.SQLITE_OK
            if self._query_kind==COLUMNS and table=='table_info' and column in EXPECTED:return sqlite3.SQLITE_OK
            if self._query_kind==INDEXES and table=='index_list' and column in EXPECTED:return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    def query(self,sql,parameters=()):
        valid=(sql in {TABLES,VERSION} and parameters==()) or (sql in {COLUMNS,INDEXES} and type(parameters) is tuple and len(parameters)==1 and parameters[0] in EXPECTED)
        if not valid:raise SchemaPolicyError()
        self._query_kind=sql
        try:return self._db.execute(sql,parameters).fetchall()
        except sqlite3.DatabaseError:raise SchemaPolicyError() from None
        finally:self._query_kind=None
    def inspect(self,kind):
        if kind not in {'l2','kg'}:raise SchemaPolicyError()
        target={'memories'} if kind=='l2' else {'nodes','edges'}
        present={r[0] for r in self.query(TABLES)}
        result=[];drift=[]
        for name in sorted(target):
            if name not in present:drift.append(name+':missing');continue
            cols=self.query(COLUMNS,(name,));indexes=self.query(INDEXES,(name,))
            if {c[0]:c[1] for c in cols}!=EXPECTED[name]:drift.append(name+':columns_or_types')
            if {c[0]:c[3] for c in cols if c[3]}!=EXPECTED_PK[name]:drift.append(name+':primary_key')
            if {c[0] for c in cols if c[2]}!=EXPECTED_NOT_NULL[name]:drift.append(name+':not_null')
            safe_cols=[{'name':c[0] if c[0] in EXPECTED[name] else 'unknown:'+digest(c[0]),
                        'type':c[1] if c[1] in {'INTEGER','TEXT','REAL','BLOB',''} else 'unknown:'+digest(c[1]),
                        'not_null':bool(c[2]),'primary_key':c[3]} for c in cols]
            safe_indexes=[{'name':i[0] if i[0] in INDEX_NAMES else 'unknown:'+digest(i[0]),'unique':bool(i[1]),'origin':i[2],'partial':bool(i[3])} for i in indexes]
            result.append({'table':name,'columns':safe_cols,'indexes':safe_indexes})
        return {'status':'SCHEMA_DRIFT' if drift else 'SCHEMA_COMPATIBLE','scope':'selected frozen SQLite structure only; not native L1/profile or real host verification',
                'source_commit':UPSTREAM,'schema_hash':digest(result),'tables':result,'drift':drift,
                'user_version':self.query(VERSION)[0][0],'implementation_paths':MODULES,
                'private_records_read':0,'application_row_queries':0,'writes':0,'real_host_verified':False,
                'native_L1_profile_compatibility':'UNKNOWN'}
    def close(self):self._db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
