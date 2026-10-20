"""Finite local IPC frames. A dribbling peer cannot renew the total deadline."""
import json
import time
from ..privacy import _json_object


def receive_object(conn, *, limit, seconds):
    deadline=time.monotonic()+seconds
    raw=b''
    while b'\n' not in raw:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('IPC_FRAME_DEADLINE')
        conn.settimeout(remaining)
        part=conn.recv(min(4096,limit+1-len(raw)))
        if not part:raise ValueError('IPC_INCOMPLETE_FRAME')
        raw+=part
        if len(raw)>limit:raise ValueError('IPC_FRAME_BOUND')
    if not raw.endswith(b'\n') or b'\n' in raw[:-1]:raise ValueError('IPC_SINGLE_FRAME_REQUIRED')
    try:value=json.loads(raw,object_pairs_hook=_json_object)
    except (RecursionError,UnicodeError):raise ValueError('IPC_INVALID_JSON') from None
    if type(value) is not dict:raise ValueError('IPC_OBJECT_REQUIRED')
    return value
