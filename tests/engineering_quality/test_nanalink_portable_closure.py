"""The minimal Core package must carry the platform modules it actually imports."""
from pathlib import Path
import shutil
import subprocess
import sys

from tools.nana_portable_cloud.build import verify_runtime_closure

ROOT = Path(__file__).resolve().parents[2]


def selected_sources():
    return [line for line in (ROOT / 'packaging/portable/runtime-files.txt').read_text().splitlines()
            if line and not line.startswith('#')]


def test_current_core_platform_imports_are_in_the_portable_allowlist():
    names = [str(p.relative_to(ROOT)) for p in (ROOT / 'src/nana_core').rglob('*.py')]
    verify_runtime_closure(selected_sources(), names, lambda name: (ROOT / name).read_text())


def test_selected_package_starts_original_owner_without_optional_network_stack(tmp_path):
    root = tmp_path / 'package'
    for name in selected_sources():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    script = r'''
import builtins, json, sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'src'))
original_import=builtins.__import__
def minimal_import(name,*args,**kwargs):
    if name.split('.')[0] in {'aiohttp','qrcode','torch','cv2','PySide6'}:
        raise ImportError('OPTIONAL_STACK_NOT_INSTALLED')
    return original_import(name,*args,**kwargs)
builtins.__import__=minimal_import
from nana_core.life.config import LifeConfig,write_config
from nana_core.continuity.project_work.service import material_for
from nana_core.life.application import LifeApplication
from nana_core.life.live_api.bridge import GatewayService
from nana_core.nanalink.video_handoff import public_video_cache_handle, with_current_public_video
assert callable(public_video_cache_handle) and callable(with_current_public_video)
material=lambda name:material_for(root,'src/nana_core/continuity/'+name)
home=root.parent/'dev';home.mkdir(mode=0o700)
write_config(home,LifeConfig(project_root=str(root),materials=(material('recurrence.py'),),
    practice=material('identity.py'),heldout=material('autonomy/requests.py'),
    transfer=material('subject/social.py'),max_autonomous_materials=0))
with LifeApplication(home) as app:
    app.pause();identity=app.runtime.identity_id
    assert not app.runtime.store.all('actions')
    assert not app.runtime.store.all('cognitive_requests')
with LifeApplication(home) as app:
    app.pause();assert app.runtime.identity_id==identity
    assert not app.runtime.store.all('actions')
    assert not app.runtime.store.all('cognitive_requests')
modules=[m for n,m in sys.modules.items() if n.startswith('nana_core') and getattr(m,'__file__',None)]
assert modules and all(Path(m.__file__).is_relative_to(root/'src') for m in modules)
print(json.dumps({'same_identity':True,'loaded_core_modules':len(modules),
                 'optional_stack_imports':0,'model_calls':0,'actions':0}))
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, str(root)], cwd=tmp_path,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"same_identity": true' in result.stdout
