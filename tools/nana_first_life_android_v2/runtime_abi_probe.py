"""Run with the supplied SDK's Python -I -B in a fresh qualification container.

Only a uniquely named temporary SQLite file is written. Optional TLS checks use
one fixed public package-index URL, normal certificate validation and the host's
explicit CA mount/proxy. No Subject, Provider or credential is opened.
"""

import argparse
import ctypes
import hashlib
import json
import os
import sqlite3
import ssl
import sys
import tempfile
import urllib.request
from pathlib import Path


def probe(tls=False):
    if not (sys.flags.isolated and sys.dont_write_bytecode):
        raise RuntimeError("ISOLATED_NO_BYTECODE_REQUIRED")
    if sys.version_info[:3] != (3, 12, 14) or sys.prefix != "/opt/nana-core/runtime":
        raise RuntimeError("SUPPLIED_RUNTIME_PREFIX_REQUIRED")
    if sqlite3.sqlite_version != "3.51.3" or os.geteuid() != 999:
        raise RuntimeError("EXACT_SQLITE_NONROOT_REQUIRED")
    context = ssl.create_default_context()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise RuntimeError("TLS_VERIFICATION_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="nana-abi-") as temporary:
        with sqlite3.connect(Path(temporary) / "probe.db") as connection:
            connection.execute("pragma journal_mode=wal")
            connection.execute("create virtual table words using fts5(body)")
            connection.execute("insert into words values ('PUBLIC runtime probe')")
            connection.commit()
            if connection.execute("select count(*) from words where words match 'runtime'").fetchone()[0] != 1:
                raise RuntimeError("FTS5_REQUIRED")
            if connection.execute("select json_extract('{\"x\":1}', '$.x')").fetchone()[0] != 1:
                raise RuntimeError("JSON_REQUIRED")
            if connection.execute("pragma integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("SQLITE_INTEGRITY_REQUIRED")
    loaded = sorted({line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines()
                     if any(name in line for name in ("libsqlite3.so", "libssl.so", "libcrypto.so"))})
    if not any(name.startswith("/opt/nana-core/runtime/lib/libsqlite3.so") for name in loaded):
        raise RuntimeError("PRIVATE_SQLITE_LIBRARY_REQUIRED")
    result = {
        "scope": "ACTUAL_SUPPLIED_CLOUD_SDK_IN_ISOLATED_DEBIAN13",
        "python": sys.version.split()[0], "prefix": sys.prefix,
        "sqlite": sqlite3.sqlite_version, "openssl": ssl.OPENSSL_VERSION,
        "uid": os.geteuid(), "groups": os.getgroups(),
        "isolated": bool(sys.flags.isolated), "bytecode_disabled": sys.dont_write_bytecode,
        "loaded_libraries": loaded, "native_ctypes": bool(ctypes.sizeof(ctypes.c_void_p)),
        "sha256": hashlib.sha256(b"PUBLIC_RUNTIME_PROBE").hexdigest(),
        "sqlite_wal_fts5_json_transaction_integrity": "PASS",
        "tls": "NOT_RUN", "subject_opened": False, "provider_calls": 0,
        "private_data_used": False, "production_changed": False,
    }
    if tls:
        # No cookies, Authorization, user account, model endpoint or redirects.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), NoRedirect())
        with opener.open("https://pypi.org/simple/", timeout=15) as response:
            if response.status != 200:
                raise RuntimeError("PUBLIC_TLS_RESPONSE_NOT_200")
            response.read(1024)
            result["tls"] = "PASS_CERTIFICATE_AND_HOSTNAME_VERIFIED_HTTP_200"
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tls", action="store_true")
    print(json.dumps(probe(parser.parse_args().tls), indent=2))
