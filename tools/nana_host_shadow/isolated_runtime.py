"""Build a private CPython SQLite binding; no system Python/library replacement.

The host supplies an existing ABI-compatible CPython3.12 executable. A separate Shadow process
loads this pinned binding and private wheels, leaving AstrBot's imports untouched.
"""
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sysconfig
import tarfile
import zipfile
from .safety import digest, private_file
from .bootstrap_entry import SOABI, EXT_SUFFIX, VERIFIED_PYTHON_RELEASES, verify

SOURCES = {
    'Python-3.12.14.tgz': ('https://www.python.org/ftp/python/3.12.14/Python-3.12.14.tgz', '6c6df908d2c3fd24e6d76869e92542abd0f33aec9dfc18df8875f89660286d43'),
    'sqlite-fixed.zip': ('https://www.sqlite.org/2026/sqlite-amalgamation-3510300.zip', 'acb1e6f5d832484bf6d32b681e858c38add8b2acdfd42ac5df24b8afb46552b4')}

WHEEL_PINS = {'typing_inspection-0.4.4-py3-none-any.whl': '65b8397ba37ccbce054456aaccddfc91e6e3083c92824df348d96ca832f3f147', 'typing_extensions-4.16.0-py3-none-any.whl': '481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8', 'annotated_types-0.8.0-py3-none-any.whl': 'f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0', 'pydantic_core-2.46.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl': '0fc5be0abd4a407e200d844b404e33639a554e7bd0d448e7b9ae181be4789ac2', 'pydantic-2.13.5-py3-none-any.whl': '346a034f080da3755d8e9cb5e00e8b07de1d39e4f6e2c87d8ab7cafa0b269a73'}


def abi_metadata():
    return {'existing_host_interpreter_required': 'CPython3.12 normal ABI, Linux x86_64, glibc>=2.34',
            'extension_build_python': '3.12.14', 'extension_ABI_target': SOABI, 'EXT_SUFFIX': EXT_SUFFIX,
            'verified_python_releases': list(VERIFIED_PYTHON_RELEASES), 'other_3_12_patches': 'UNTESTED'}


def reuse_runtime(bundle, destination):
    """Reuse the already measured binaries unchanged; revise metadata only."""
    bundle, dest = Path(bundle), Path(destination)
    if dest.exists():
        raise ValueError('RUNTIME_DESTINATION_MUST_BE_NEW')
    outer = verify(bundle)
    m = json.loads((bundle/'runtime/runtime_manifest.json').read_text())
    if any(Path(name).is_absolute() or '..' in Path(name).parts for name in m['files']):
        raise ValueError('REUSED_RUNTIME_PATH_MISMATCH')
    actual = {str(p.relative_to(bundle/'runtime')) for p in (bundle/'runtime').rglob('*') if p.is_file()}
    if actual != set(m['files']) | {'runtime_manifest.json'}:
        raise ValueError('REUSED_RUNTIME_FILE_SET_MISMATCH')
    hashes = {name: digest((bundle/'runtime'/name).read_bytes()) for name in m['files']}
    pinned = '95c7215bc78d43cae809e99fcc65c1572cd611c87ae273afb80138b61c01e6ec'
    if hashes != m['files'] or digest(hashes) != pinned or outer['runtime_sha256'] != pinned:
        raise ValueError('REUSED_RUNTIME_HASH_MISMATCH')
    if m['sqlite'] != '3.51.3' or m['pydantic'] != '2.13.5':
        raise ValueError('REUSED_RUNTIME_VERSION_MISMATCH')
    shutil.copytree(bundle/'runtime', dest)
    m.update(abi_metadata(), reused_from_support_SHA=outer['support_source_SHA'])
    private_file(dest/'runtime_manifest.json', m, replace=True)
    return m


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
         *map(str,sorted(cpy.glob('*.c'))),str(sql/'sqlite3.c'),'-o',str(ext),'-Wl,-Bsymbolic','-lpthread','-ldl','-lm']
    subprocess.run(cmd, check=True)
    symbols=subprocess.check_output(['objdump','-T',str(ext)],text=True)
    glibc=max((tuple(map(int,v.split('.'))) for v in re.findall(r'GLIBC_(\d+\.\d+)',symbols)),default=(0,0))
    if glibc>(2,34):raise ValueError('BUILD_GLIBC_TARGET_EXCEEDED')
    licenses=dest/'licenses'; licenses.mkdir()
    shutil.copyfile(work/'Python-3.12.14/LICENSE',licenses/'CPython-LICENSE.txt')
    (licenses/'SQLite-PUBLIC-DOMAIN.txt').write_text('SQLite is in the public domain. https://www.sqlite.org/copyright.html\nSource: '+SOURCES['sqlite-fixed.zip'][0]+'\n')
    deps=dest/'deps';deps.mkdir()
    wheels=[]
    found={p.name for p in (inputs/'wheels').glob('*.whl') if p.name.split('-')[0] in {'pydantic','pydantic_core','annotated_types','typing_extensions','typing_inspection'}}
    if found != set(WHEEL_PINS):raise ValueError('PINNED_WHEEL_SET_MISMATCH')
    for whl in sorted((inputs/'wheels').glob('*.whl')):
        if whl.name.split('-')[0] not in {'pydantic','pydantic_core','annotated_types','typing_extensions','typing_inspection'}:
            continue
        expected=json.loads((inputs/'wheel_sources.json').read_text())[whl.name]
        if digest(whl.read_bytes()) != WHEEL_PINS[whl.name] or expected['sha256'] != WHEEL_PINS[whl.name]:
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
       'system':'Linux','minimum_glibc':'2.34','ELF_maximum_GLIBC_symbol':'.'.join(map(str,glibc)),
       'runtime_sha256':digest(files),'files':files,
       'sources':{k:{'url':v[0],'sha256':v[1]} for k,v in SOURCES.items()},'wheels':wheels,
       'licenses':['CPython PSF-2.0 and included historical licenses','SQLite public domain','Pydantic/dependencies: included wheel license files'],
       'compiler':subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],
       'flags':['shared','PIC','O2','Py_BUILD_CORE_MODULE','SQLITE_THREADSAFE=1','SQLITE_ENABLE_COLUMN_METADATA','-Wl,-Bsymbolic'],
       'system_library_or_global_env_changed':False,'bytes':sum(p.stat().st_size for p in dest.rglob('*') if p.is_file())}
    m.update(abi_metadata())
    private_file(dest/'runtime_manifest.json',m)
    return m
