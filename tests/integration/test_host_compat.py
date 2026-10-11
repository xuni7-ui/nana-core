"""Classified ABI rejection is separate from actual interpreter verification."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
from nana_host_shadow.bootstrap_entry import check_abi, RuntimeBlocked, runtime


def metadata():
    return {'python': '3.12.3', 'python_major_minor': [3, 12], 'implementation': 'cpython',
            'SOABI': 'cpython-312-x86_64-linux-gnu', 'EXT_SUFFIX': '.cpython-312-x86_64-linux-gnu.so',
            'architecture': 'x86_64', 'system': 'Linux', 'glibc': {'kind': 'glibc', 'version': '2.39'},
            'abiflags': ''}


@pytest.mark.parametrize('field,value,reason', [
    ('implementation', 'pypy', 'BLOCKED_PYTHON_IMPLEMENTATION'),
    ('python_major_minor', [3, 13], 'BLOCKED_PYTHON_MINOR'),
    ('abiflags', 'd', 'BLOCKED_PYTHON_BUILD'),
    ('architecture', 'aarch64', 'BLOCKED_ARCH'),
    ('system', 'Darwin', 'BLOCKED_OS'),
    ('SOABI', None, 'BLOCKED_SOABI'),
    ('EXT_SUFFIX', '.abi3.so', 'BLOCKED_EXT_SUFFIX'),
    ('glibc', {'kind': 'glibc', 'version': '2.33'}, 'BLOCKED_GLIBC'),
    ('glibc', {'kind': 'musl', 'version': '1.2'}, 'BLOCKED_GLIBC'),
    ('glibc', {'kind': 'glibc', 'version': 'UNKNOWN'}, 'BLOCKED_GLIBC'),
])
def test_failure_metadata_identifies_exact_condition(field, value, reason):
    host = metadata(); host[field] = value
    before = deepcopy(host)
    with pytest.raises(RuntimeBlocked, match=reason) as failure:
        check_abi(host)
    assert failure.value.host == before and host == before


def test_patch_string_is_not_an_abi_condition():
    for version in ['3.12.3', '3.12.14', '3.12.99']:
        host = metadata(); host['python'] = version
        check_abi(host)
    # This checks the policy only, not a claim that an unrun interpreter works.


def test_missing_extension_reports_loader_stage(tmp_path):
    saved = {k: v for k, v in sys.modules.items() if k == '_sqlite3' or k == 'sqlite3' or k.startswith('sqlite3.')}
    try:
        with pytest.raises(RuntimeBlocked, match='BLOCKED_EXTENSION_LOAD') as failure:
            runtime(tmp_path)
    finally:
        for k in list(sys.modules):
            if k == '_sqlite3' or k == 'sqlite3' or k.startswith('sqlite3.'):
                del sys.modules[k]
        sys.modules.update(saved)
    assert failure.value.host['SOABI'] == 'cpython-312-x86_64-linux-gnu'
    assert failure.value.shadow['extension_ABI_target'] == failure.value.host['SOABI']
    assert failure.value.shadow['sqlite'] == 'UNKNOWN'
