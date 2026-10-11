import sqlite3
import hashlib
import pytest
from tools.nana_astrbot_shadow.iris_schema import SchemaInspector,SchemaPolicyError,TABLES,COLUMNS,INDEXES

# DDL is a minimal synthetic schema fixture matching locked adapter field/type
# metadata; no upstream executable source is vendored or called.
def fixture(path):
    with sqlite3.connect(path) as d:
        d.execute("CREATE TABLE memories (faiss_idx INTEGER PRIMARY KEY,memory_id TEXT UNIQUE NOT NULL,content TEXT NOT NULL,metadata TEXT NOT NULL DEFAULT '{}',group_id TEXT,user_id TEXT,timestamp TEXT,kg_processed INTEGER DEFAULT 0,persona_id TEXT NOT NULL DEFAULT 'default')")
        d.execute("INSERT INTO memories(memory_id,content) VALUES('synthetic-memory','synthetic-private-canary')")
        d.execute("CREATE TABLE nodes(id TEXT PRIMARY KEY,label TEXT NOT NULL,name TEXT NOT NULL,content TEXT,confidence REAL,access_count INTEGER,last_access_time TEXT,created_time TEXT,source_memory_id TEXT,group_id TEXT,properties TEXT)")
        d.execute("CREATE TABLE edges(source_id TEXT NOT NULL,target_id TEXT NOT NULL,relation_type TEXT NOT NULL,weight REAL,confidence REAL,access_count INTEGER,last_access_time TEXT,created_time TEXT,source_memory_id TEXT,properties TEXT,PRIMARY KEY(source_id,target_id,relation_type))")

@pytest.mark.parametrize('sql',["SELECT content FROM memories","SELECT * FROM memories","SELECT metadata FROM memories","SELECT sql FROM sqlite_master","SELECT dflt_value FROM pragma_table_info('memories')","PRAGMA wal_checkpoint","PRAGMA table_info(memories)","ATTACH DATABASE ':memory:' AS other","UPDATE memories SET content='x'","SELECT count(*) FROM memories","SELECT load_extension('x')"])
def test_only_exact_metadata_queries_allowed(tmp_path,sql):
    p=tmp_path/'iris.db';fixture(p)
    with SchemaInspector(p) as i:
        with pytest.raises(SchemaPolicyError,match='BLOCKED_SCHEMA_INSPECTION_POLICY'):i.query(sql)
        # Defense in depth: even bypassing Python query allowlist cannot select rows.
        with pytest.raises(sqlite3.DatabaseError):i._db.execute('SELECT content FROM memories').fetchall()

def test_metadata_only_compatibility_no_rows_or_default_values_and_zero_drift(tmp_path):
    p=tmp_path/'iris.db';fixture(p);before=hashlib.sha256(p.read_bytes()).hexdigest()
    with SchemaInspector(p) as i:
        report=i.inspect('l2');kg=i.inspect('kg')
        assert report['status']==kg['status']=='SCHEMA_COMPATIBLE'
        assert report['private_records_read']==report['writes']==0
        assert 'synthetic-private-canary' not in str(report) and 'dflt_value' not in str(report)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==before
    assert {x.name for x in tmp_path.iterdir()}=={'iris.db'}

def test_schema_drift_and_active_wal_fail_closed(tmp_path):
    p=tmp_path/'iris.db';fixture(p)
    with sqlite3.connect(p) as d:d.execute('ALTER TABLE memories ADD COLUMN unexpected TEXT')
    with SchemaInspector(p) as i:assert i.inspect('l2')['status']=='SCHEMA_DRIFT'
    (tmp_path/'iris.db-wal').write_bytes(b'synthetic journal marker')
    with pytest.raises(ValueError,match='FROZEN_SCHEMA'):SchemaInspector(p)
