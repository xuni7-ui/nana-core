"""Metadata-only preflight, no configuration content, host SDK or action imports."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import stat
import sys
from ..storage import canonical,digest

def probe(expected_paths=None, *, declared_host_versions=None):
    checks=[]
    def add(name,state,detail):checks.append({'check':name,'status':state,'detail':detail})
    add('python','PASS' if sys.version_info >= (3,12) else 'BLOCKED',platform.python_version())
    add('sqlite','PASS' if sqlite3.sqlite_version_info >= (3,51,3) else 'BLOCKED',sqlite3.sqlite_version)
    try:v=importlib.metadata.version('pydantic');add('pydantic','PASS' if v in {'2.13.4','2.13.5'} else 'BLOCKED',v)
    except importlib.metadata.PackageNotFoundError:add('pydantic','BLOCKED','missing')
    for dist in ('astrbot','astrbot-plugin-iris-chat-memory'):
        try:add(dist,'PASS',{'package_metadata_version':importlib.metadata.version(dist),'runtime_version':'UNKNOWN'})
        except importlib.metadata.PackageNotFoundError:add(dist,'UNKNOWN','no distribution metadata; plugin directory presence is a separate check')
    for label,path in (expected_paths or {}).items():
        p=Path(path)
        try:
            s=p.lstat();add('path:'+label,'BLOCKED' if stat.S_ISLNK(s.st_mode) else 'PASS',
                {'exists':True,'directory':stat.S_ISDIR(s.st_mode),'mode':oct(stat.S_IMODE(s.st_mode)),'uid':s.st_uid,'gid':s.st_gid,
                'readable':os.access(p,os.R_OK),'writable':os.access(p,os.W_OK),'contents_read':False})
        except FileNotFoundError:add('path:'+label,'BLOCKED',{'exists':False})
        except OSError:add('path:'+label,'UNKNOWN','metadata unavailable')
    add('disk','PASS' if shutil.disk_usage('.').free >= 64*1024*1024 else 'BLOCKED',{'free_bytes':shutil.disk_usage('.').free,'minimum_bytes':64*1024*1024,'resource_estimate':'UNKNOWN'})
    add('host_identity','PASS',{'hostname_hash':digest(platform.node()),'process_id':os.getpid(),'container_identity':'UNKNOWN'})
    add('observability','UNKNOWN',{'current_process_metadata':True,'host_process_visibility':'not probed','runtime_event_hook':'not probed'})
    add('read_only_snapshot','UNKNOWN','requires reviewed operator backup; no DB opened')
    add('shadow_barrier','PASS','package shadow execute is structurally disabled; installed hook/config not probed')
    state='BLOCKED' if any(c['status']=='BLOCKED' for c in checks) else 'UNKNOWN' if any(c['status']=='UNKNOWN' for c in checks) else 'PASS'
    return {'status':state,'checks':checks,'declared_host_versions':declared_host_versions or {},'declarations_verified':False,
        'automatic_repairs':False,'files_written':0,'private_content_read':False,'model_calls':0,'deployment_ready':False}

HostHealthProbe=probe

def main():
    p=argparse.ArgumentParser();p.add_argument('--path',action='append',default=[],help='label=expected-path; metadata only')
    a=p.parse_args(); paths=dict(x.split('=',1) for x in a.path);print(canonical(probe(paths)))
if __name__=='__main__':main()
