import importlib.util,os,pathlib,runpy,sys
r=pathlib.Path('/tmp/nana-bootstrap-build')
a=sys.argv[1:];old=a[:1]==['--engine-old'];fixed=a[:1]==['--engine-fixed']
if old or fixed:a=a[1:]
if old or fixed:
 spec=importlib.util.spec_from_file_location('_sqlite3',(r/'engine-old'/'_sqlite3.cpython-312-x86_64-linux-gnu.so' if old else pathlib.Path('/workspace/nana-core/.nana-experiment/shadow-bootstrap/nana-shadow-bootstrap-3aba4eb4253c/runtime/_sqlite3.cpython-312-x86_64-linux-gnu.so')));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);sys.modules['_sqlite3']=m
sys.dont_write_bytecode=True
if '-I' not in a:sys.path[:0]=[p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p]
sys.path.insert(0,str(r/'deps'));sys.executable=str(r/('compat-python-old' if old else 'compat-python-fixed' if fixed else 'compat-python'))
while a and a[0] in ('-I','-B'):a=a[1:]
if a[:1]==['-m']:
 sys.argv=a[1:];sys.path.insert(0,os.getcwd());runpy.run_module(a[1],run_name='__main__',alter_sys=True)
elif a[:1]==['-c']:
 sys.argv=['-c',*a[2:]];exec(a[1],{'__name__':'__main__'})
else:
 sys.argv=a;sys.path.insert(0,str(pathlib.Path(a[0]).resolve().parent));runpy.run_path(a[0],run_name='__main__')
