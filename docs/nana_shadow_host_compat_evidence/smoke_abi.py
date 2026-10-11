"""Actual-binding developer probe; no version monkeypatches or external calls."""
import gc,hashlib,json,pathlib,platform,sqlite3,subprocess,sys,sysconfig,tempfile
import _sqlite3,pydantic
# Warm up the class/module caches before checking for retained connection refs.
for _ in range(5):
 c=sqlite3.connect(':memory:');c.close();del c
gc.collect();before=sys.getrefcount(sqlite3.Connection)
for _ in range(200):
 c=sqlite3.connect(':memory:');c.execute('SELECT json_valid(?)',('{}',)).fetchone();c.close();del c
gc.collect();after=sys.getrefcount(sqlite3.Connection);assert after==before,(before,after)
with tempfile.TemporaryDirectory() as td:
 db=sqlite3.connect(pathlib.Path(td)/'probe.db');assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
 db.execute('PRAGMA synchronous=FULL');db.execute('CREATE TABLE example(k TEXT PRIMARY KEY,v TEXT)');db.execute('INSERT INTO example VALUES(?,?)',('synthetic','value'));db.commit()
 backup=sqlite3.connect(pathlib.Path(td)/'backup.db');db.backup(backup);assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok';backup.close();db.close()
assert pydantic.__version__=='2.13.5' and sqlite3.sqlite_version=='3.51.3'
print(json.dumps({'python':platform.python_version(),'SOABI':sysconfig.get_config_var('SOABI'),'EXT_SUFFIX':sysconfig.get_config_var('EXT_SUFFIX'),'architecture':platform.machine(),'glibc':platform.libc_ver(),'sqlite':sqlite3.sqlite_version,'pydantic':pydantic.__version__,'binding':_sqlite3.__file__,'binding_sha256':hashlib.sha256(pathlib.Path(_sqlite3.__file__).read_bytes()).hexdigest(),'connection_class_refcount_before':before,'connection_class_refcount_after':after,'connections_created_closed':205,'WAL_and_backup':'PASS','interpretation':'bounded smoke and successful shutdown do not certify absence of every possible refcount defect'}))
