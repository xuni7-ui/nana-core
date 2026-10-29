"""Explicit host-local archive lifecycle and separately approved claim retention.

Select frozen files by repeating --file. --synthetic requires the source's owned
.nana-synthetic-legacy.json marker. Real private source access requires the
operator's explicit --private-read-authorized flag; it does not enable import.
import-batch requires a private, expiring approval pinned to a reviewed plan;
only the already running original Core owner performs the retention operation.
Withdraw retires search/plan support while preserving frozen source bytes.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys

# In the delivered tools directory use the explicitly selected release's own
# interpreter, including isolated (-I) mode. Never discover a host database or
# credentials. Development invocation retains its explicit PYTHONPATH.
_release = Path(sys.executable).absolute().parents[2]
if (_release / 'src/nana_core/migration/archive.py').is_file():
    sys.path.insert(0, str(_release / 'src'))

from nana_core.contracts import CoreError
from nana_core.continuity.privacy import _json_object
from nana_core.life.live_api.contracts import Binding
from nana_core.migration import archive


def sha256_arg(value):
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise argparse.ArgumentTypeError("64 lowercase SHA256 hexadecimal characters required")
    return value


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("freeze", "verify", "search", "plan", "withdraw", "validate-plan", "import-batch", "withdraw-core"):
        command = commands.add_parser(name, aliases=["import-preview"] if name == "plan" else [])
        command.add_argument("--subject-id", required=True)
        command.add_argument("--lineage-binding", required=True, type=sha256_arg)
        command.add_argument("--private-read-authorized", action="store_true")
        if name == "freeze":
            command.add_argument("--source-root", required=True)
            command.add_argument("--file", action="append", required=True, dest="files")
            command.add_argument("--destination", required=True)
            command.add_argument("--synthetic", action="store_true")
        else:
            command.add_argument("--archive", required=True)
            command.add_argument("--manifest-sha256", type=sha256_arg)
        if name == "search":
            command.add_argument("--query", required=True)
            command.add_argument("--limit", type=int, default=20)
        elif name == "plan":
            command.add_argument("--batch-size", type=int, default=100)
            command.add_argument("--output-plan", help="Write a new private read-only plan file; never overwrite")
        elif name == "withdraw":
            command.add_argument("--source-id", required=True, type=sha256_arg)
        elif name == "validate-plan":
            command.add_argument("--plan-file", required=True)
        elif name in {"import-batch", "withdraw-core"}:
            command.add_argument("--home", required=True)
            command.add_argument("--approval-file", required=True)
            if name == "import-batch":
                command.add_argument("--plan-file", required=True)
                command.add_argument("--batch-id", required=True, type=sha256_arg)
            else:
                command.add_argument("--source-id", required=True, type=sha256_arg)
    return result


def load_plan(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise CoreError("LEGACY_BATCH_PLAN_PATH_UNSAFE")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise CoreError("LEGACY_BATCH_PLAN_PATH_UNSAFE")
        raw = stream.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise CoreError("LEGACY_BATCH_PLAN_BYTE_BOUND")
    return json.loads(raw, object_pairs_hook=_json_object)


def run(args):
    binding = Binding(subject_id=args.subject_id, lineage_binding=args.lineage_binding)
    if args.command in {"import-batch", "withdraw-core"}:
        from nana_core.life.control import request
        from nana_core.life.live_api.supervisor import existing_identity
        if existing_identity(args.home)[:2] != (binding.subject_id, binding.lineage_binding):
            raise CoreError('LEGACY_SUBJECT_LINEAGE_MISMATCH')
        operation = 'legacy-import-batch' if args.command == 'import-batch' else 'legacy-withdraw'
        body = {'operation': operation, 'archive': str(Path(args.archive).absolute()),
                'approval_file': str(Path(args.approval_file).absolute())}
        if args.command == 'import-batch':
            body.update(plan_file=str(Path(args.plan_file).absolute()), batch_id=args.batch_id)
        else:
            body['source_id'] = args.source_id
        result = request(args.home, body)
        if result.get('ok') is not True:
            raise CoreError(result.get('error', 'LEGACY_IMPORT_OWNER_UNAVAILABLE'))
        return result['result']
    if args.command == "freeze":
        return archive.freeze(args.source_root, args.files, args.destination, binding,
                              private_authorized=args.private_read_authorized, synthetic=args.synthetic)
    common = {"private_authorized": args.private_read_authorized,
              "expected_manifest_sha256": args.manifest_sha256}
    if args.command == "verify":
        return archive.verify(args.archive, binding=binding, **common)
    if args.command == "search":
        return archive.search(args.archive, args.query, limit=args.limit, binding=binding, **common)
    if args.command in {"plan", "import-preview"}:
        result = archive.batch_plan(args.archive, binding, batch_size=args.batch_size, **common)
        if args.output_plan:
            path = Path(args.output_plan).absolute()
            if path.resolve() != path:
                raise CoreError("LEGACY_BATCH_PLAN_PATH_UNSAFE")
            archive.private_json(path, result)
            path.chmod(0o400)
        return result
    if args.command == "withdraw":
        return archive.withdraw_source(args.archive, args.source_id, binding, **common)
    return archive.validate_batch_plan(args.archive, load_plan(args.plan_file), binding, **common)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = run(args)
    except CoreError as exc:
        result = {"state": "BLOCKED", "code": exc.code, "core_memory_imported": False,
                  "execution_authority": False}
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        result = {"state": "BLOCKED", "code": "LEGACY_ARCHIVE_INPUT_OR_IO_INVALID",
                  "core_memory_imported": False, "execution_authority": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 2 if result.get("state") == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
