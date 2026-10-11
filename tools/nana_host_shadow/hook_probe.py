"""Static metadata only. API-name presence cannot prove safe hot registration."""
import ast
import importlib.metadata
from pathlib import Path
from .safety import checked_path, digest


def probe(source_files=()):
    try:version=importlib.metadata.version('astrbot')
    except importlib.metadata.PackageNotFoundError:version='UNKNOWN'
    names=set();fingerprints=[]
    for name in source_files:
        p=checked_path(name)
        if p.suffix!='.py' or p.stat().st_size>256*1024:raise ValueError('HOOK_SOURCE_SCOPE_BLOCKED')
        # Only an explicitly selected API module, never an arbitrary config/log.
        if p.name not in {'event_bus.py','event.py','filter.py','event_hook.py'}:
            raise ValueError('HOOK_SOURCE_SCOPE_BLOCKED')
        raw=p.read_bytes();tree=ast.parse(raw)
        names.update(n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                     and any(s in n.name.lower() for s in ('hook','register','unregister','observer')))
        fingerprints.append(digest(raw))
    return {'status':'UNKNOWN','AstrBot_distribution_version':version,'available_API_names':sorted(names),
            'source_hashes':fingerprints,'dynamic_registration':'UNKNOWN','dynamic_unregistration':'UNKNOWN',
            'restart_required':'UNKNOWN','strict_synthetic_probe_isolation':'UNKNOWN',
            'FIRST_REAL_MESSAGE_STREAM_SHADOW':'BLOCKED_HOOK_COMPATIBILITY_UNVERIFIED',
            'hook_installed':False,'host_imports':0,'files_written':0}
