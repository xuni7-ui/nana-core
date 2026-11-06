"""Follow the registered active release before starting this single Gateway.

No live process switch, new Subject, Store write or credential inspection. The
operator's private registry and existing Supervisor snapshot select the sealed
release; the target bootstrap rechecks its own complete bundle before imports.
"""

import os
import sys
from pathlib import Path

from .contracts import ApiError, Realm
from .state import AtomicDocument


def gateway_release(cfg, *, current_root=None):
    root = Path(current_root) if current_root is not None else Path(__file__).resolve().parents[4]
    path = Path(cfg.host_state).absolute()/'supervisor.json'
    try:
        path.lstat()
    except FileNotFoundError:
        state = None
        selected = cfg.active_release
    else:
        state = AtomicDocument.read_existing(path)
        selected = state.get('active_release')
    registry = {release.release_id:release for release in cfg.releases}
    if len(registry)!=len(cfg.releases) or selected not in registry:
        raise ApiError('RELEASE_REGISTRY_INVALID', 409)
    target = registry[selected]
    if Path(target.root)==root:
        return None  # Normal Supervisor validation remains authoritative.
    target.validate_local(qualified=cfg.binding.realm==Realm.PRODUCTION)
    entry = Path(target.root)/'host_gateway.py'
    if not entry.is_file() or entry.resolve()!=entry:
        raise ApiError('GATEWAY_RELEASE_ENTRY_REQUIRED', 409)
    if cfg.binding.realm==Realm.PRODUCTION:
        names = [line.split('  ',1)[1] for line in (Path(target.root)/'SHA256SUMS').read_text().splitlines()]
        if not {'host_gateway.py','src/nana_core/life/live_api/__main__.py'} <= set(names):
            raise ApiError('GATEWAY_RELEASE_SEAL_REQUIRED', 409)
    if state is not None and AtomicDocument.read_existing(path)!=state:
        raise ApiError('HOST_STATE_CHANGED_DURING_GATEWAY_SELECTION', 409)
    return target


def follow_gateway_release(cfg):
    target = gateway_release(cfg)
    if target is None:
        return
    if os.environ.get('NANA_GATEWAY_REEXEC'):
        raise ApiError('GATEWAY_RELEASE_SELECTION_LOOP', 409)
    # Public marker only. Explicit inherited secret FDs are not read or copied;
    # exec replaces this bootstrap process and preserves their inheritance flags.
    os.environ['NANA_GATEWAY_REEXEC'] = target.release_id
    os.execv(target.python, [target.python, '-I', '-B', str(Path(target.root)/'host_gateway.py'), *sys.argv[1:]])
