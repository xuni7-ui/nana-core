import json,pathlib,sqlite3,subprocess,sys,tempfile
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);db=sqlite3.connect(p/'source.db',isolation_level=None)
 db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.executescript(pathlib.Path('src/nana_core/storage/schema_v1.sql').read_text());db.execute('BEGIN IMMEDIATE');db.execute("INSERT INTO core_meta VALUES('probe','{}') ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json");db.execute('COMMIT')
 db.execute('BEGIN IMMEDIATE');db.execute("INSERT INTO core_meta VALUES('abort','{}')");db.execute('ROLLBACK');assert db.execute("SELECT count(*) FROM core_meta WHERE key='abort'").fetchone()[0]==0
 t=sqlite3.connect(p/'backup.db');db.backup(t);assert t.execute('PRAGMA integrity_check').fetchone()[0]=='ok';t.close();db.close()
 code="import sqlite3,sys,os,signal; db=sqlite3.connect(sys.argv[1]);db.execute('PRAGMA synchronous=FULL');db.execute(\"INSERT INTO core_meta VALUES('committed','{}')\");db.commit();os.kill(os.getpid(),signal.SIGKILL)"
 r=subprocess.run([sys.executable,'-c',code,str(p/'source.db')]);assert r.returncode==-9
 db=sqlite3.connect(p/'source.db');assert db.execute("SELECT count(*) FROM core_meta WHERE key='committed'").fetchone()[0]==1;assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok';db.close()
 print(json.dumps({'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'SQL_schema_and_JSON1':'PASS','UPSERT':'PASS','explicit_transaction_rollback':'PASS','backup_integrity':'PASS','real_SIGKILL':r.returncode,'WAL_committed_recovery':'PASS','upstream_WAL_reset_race':'NOT_REPRODUCED; passing these checks does not establish absence','Core_support_gate':'NOT_BYPASSED'}))
