"""Build a private CPython SQLite binding; no system Python/library replacement.

The host supplies an existing CPython3.12.14 executable. A separate Shadow process
loads this pinned binding and private wheels, leaving AstrBot's imports untouched.
"""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sysconfig
import tarfile
import zipfile
from .safety import digest, private_file

SOURCES = {
    'Python-3.12.14.tgz': ('https://www.python.org/ftp/python/3.12.14/Python-3.12.14.tgz', '6c6df908d2c3fd24e6d76869e92542abd0f33aec9dfc18df8875f89660286d43'),
    'sqlite-fixed.zip': ('https://www.sqlite.org/2026/sqlite-amalgamation-3510300.zip', 'acb1e6f5d832484bf6d32b681e858c38add8b2acdfd42ac5df24b8afb46552b4')}


def build_runtime(inputs, destination):
    inputs, dest = Path(inputs), Path(destination)
    if dest.exists():
        raise ValueError('RUNTIME_DESTINATION_MUST_BE_NEW')
    for name, (_, expected) in SOURCES.items():
        if digest((inputs/name).read_bytes()) != expected:
            raise ValueError('PINNED_SOURCE_HASH_MISMATCH')
    dest.mkdir(mode=0o700)
    work = dest/'build'; work.mkdir()
    with tarfile.open(inputs/'Python-3.12.14.tgz') as t:
        t.extractall(work, filter='data')
    with zipfile.ZipFile(inputs/'sqlite-fixed.zip') as z:
        z.extractall(work)
    cpy=work/'Python-3.12.14/Modules/_sqlite'; sql=work/'sqlite-amalgamation-3510300'
    inc=Path(sysconfig.get_paths()['include'])
    ext=dest/'_sqlite3.cpython-312-x86_64-linux-gnu.so'
    if platform.machine() != 'x86_64':
        raise ValueError('BUILD_ARCH_UNSUPPORTED')
    cmd=['gcc','-shared','-fPIC','-O2','-DPy_BUILD_CORE_MODULE','-DSQLITE_THREADSAFE=1','-DSQLITE_ENABLE_COLUMN_METADATA',
         '-ffile-prefix-map='+str(work)+'=/nana-shadow-build','-I'+str(inc),'-I'+str(cpy),'-I'+str(sql),
         *map(str,sorted(cpy.glob('*.c'))),str(sql/'sqlite3.c'),'-o',str(ext),'-lpthread','-ldl','-lm']
    subprocess.run(cmd, check=True)
    licenses=dest/'licenses'; licenses.mkdir()
    shutil.copyfile(work/'Python-3.12.14/LICENSE',licenses/'CPython-LICENSE.txt')
    (licenses/'SQLite-PUBLIC-DOMAIN.txt').write_text('SQLite is in the public domain. https://www.sqlite.org/copyright.html\nSource: '+SOURCES['sqlite-fixed.zip'][0]+'\n')
    deps=dest/'deps';deps.mkdir()
    wheels=[]
    for whl in sorted((inputs/'wheels').glob('*.whl')):
        if whl.name.split('-')[0] not in {'pydantic','pydantic_core','annotated_types','typing_extensions','typing_inspection'}:
            continue
        expected=json.loads((inputs/'wheel_sources.json').read_text())[whl.name]
        if digest(whl.read_bytes()) != expected['sha256']:
            raise ValueError('PINNED_WHEEL_HASH_MISMATCH')
        with zipfile.ZipFile(whl) as z:
            if any(Path(n).is_absolute() or '..' in Path(n).parts for n in z.namelist()):
                raise ValueError('WHEEL_PATH_REJECTED')
            z.extractall(deps)
        wheels.append({'filename':whl.name,**expected})
    shutil.rmtree(work)  # Own new build workspace only, never host/legacy files.
    files={str(p.relative_to(dest)):digest(p.read_bytes()) for p in dest.rglob('*') if p.is_file()}
    m={'kind':'isolated_dependency_runtime','existing_host_interpreter_required':'CPython 3.12.14',
       'bundled_python_executable':False,'sqlite':'3.51.3','pydantic':'2.13.5','architecture':'x86_64',
       'system':'Linux','minimum_glibc':'2.34','runtime_sha256':digest(files),'files':files,
       'sources':{k:{'url':v[0],'sha256':v[1]} for k,v in SOURCES.items()},'wheels':wheels,
       'licenses':['CPython PSF-2.0 and included historical licenses','SQLite public domain','Pydantic/dependencies: included wheel license files'],
       'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
       'flags':['shared','PIC','O2','Py_BUILD_CORE_MODULE','SQLITE_THREADSAFE=1','SQLITE_ENABLE_COLUMN_METADATA'],
       'system_library_or_global_env_changed':False,'bytes':sum(p.stat().st_size for p in dest.rglob('*') if p.is_file())}
    private_file(dest/'runtime_manifest.json',m)
    return m
