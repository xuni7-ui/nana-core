"""Package the existing ORIGINAL Nana C.4 pure normalizer, without its Agent.

Legacy standalone consumers keep their existing path. This small generated copy
closes Core wheel/portable imports; --check prevents silent source drift. No
third-party code, credential discovery, fetch, pump or send function is copied.
"""
import argparse
import ast
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'src/bili_agent/bili_event_source.py'
TARGET=ROOT/'src/nana_core/nanalink/_c4_source.py'


def generated():
    raw=SOURCE.read_bytes();text=raw.decode();tree=ast.parse(text)
    functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'_as_int','normalize'}]
    if len(functions)!=2:raise ValueError('C.4 source changed; review its new pure boundary')
    header=('"""Generated ORIGINAL Nana C.4 normalize compatibility snapshot.\n'
            'Source: src/bili_agent/bili_event_source.py; regenerate with tools/nanalink_sync_c4.py.\n'
            'No legacy Agent/pump/network execution is included.\n"""\n'
            'import re\nfrom typing import Any, Dict, Optional\n\n'
            f'SOURCE_SHA256 = "{hashlib.sha256(raw).hexdigest()}"\n'
            '_BV = re.compile(r"/video/(BV[0-9A-Za-z]+)")\n\n')
    return header+'\n\n'.join(ast.get_source_segment(text,node) for node in functions)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    expected=generated()
    if args.check:
        if TARGET.read_text()!=expected:raise SystemExit('C4_SNAPSHOT_DRIFT')
        print('C4_ORIGINAL_NORMALIZER_SNAPSHOT_MATCH')
    else:TARGET.write_text(expected)
