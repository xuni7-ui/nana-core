# Test-only driver: actual interpreter and actual pinned library, never mocked versions.
import importlib.util,os,pathlib,runpy,sys
binding=pathlib.Path(os.environ.get('NANA_TEST_BINDING','/old/runtime/_sqlite3.cpython-312-x86_64-linux-gnu.so'))
import sqlite3
for name in list(sys.modules):
 if name=='_sqlite3' or name=='sqlite3' or name.startswith('sqlite3.'):del sys.modules[name]
spec=importlib.util.spec_from_file_location('_sqlite3',binding);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);sys.modules['_sqlite3']=m
sys.dont_write_bytecode=True
argv=sys.argv[1:]
if '-I' not in argv:sys.path[:0]=[p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p]
sys.path.insert(0,'/devdeps');sys.executable='/lab/python-private'
while argv and argv[0] in ('-I','-B','-S'):argv=argv[1:]
if argv[:1]==['-m']:
 sys.argv=argv[1:];sys.path.insert(0,os.getcwd());runpy.run_module(argv[1],run_name='__main__',alter_sys=True)
elif argv[:1]==['-c']:
 sys.argv=['-c',*argv[2:]];exec(argv[1],{'__name__':'__main__'})
else:
 sys.argv=argv;sys.path.insert(0,str(pathlib.Path(argv[0]).resolve().parent));runpy.run_path(argv[0],run_name='__main__')
