"""Build verified local source archives in a fresh user prefix; no root/network.

CPython's real _sqlite3 links the private SQLite with RUNPATH. Never patch sqlite3,
preload a library, change system Python or install an alternative Subject Store.
Supply source digests from an independently trusted release record before use.
"""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tarfile


def extract(source, expected_sha256, destination):
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("HOST_SOURCE_DIGEST_MISMATCH")
    destination.mkdir(mode=0o700)
    with tarfile.open(source) as tar:
        members = tar.getmembers()
        if len(members) > 15000 or sum(m.size for m in members) > 512 * 1024 * 1024:
            raise ValueError("HOST_SOURCE_BOUND")
        tar.extractall(destination, filter="data")
    dirs = list(destination.iterdir())
    if len(dirs) != 1 or not dirs[0].is_dir():
        raise ValueError("SOURCE_LAYOUT_UNSUPPORTED")
    return dirs[0]


def build(root, sqlite_source, sqlite_sha256, python_source, python_sha256, ffi_source, ffi_sha256, jobs=2):
    root = Path(root).absolute()
    if not re.fullmatch(r"[A-Za-z0-9/_.-]+", str(root)):
        raise ValueError("BUILD_PREFIX_CHARACTERS_UNSUPPORTED")
    if root.exists() or root.resolve() != root or os.geteuid() == 0:
        raise ValueError("FRESH_NONROOT_PREFIX_REQUIRED")
    if type(jobs) is not int or not 1 <= jobs <= 2:
        raise ValueError("BUILD_JOBS_BOUND")
    root.mkdir(mode=0o700, parents=True)
    sqlite = extract(Path(sqlite_source), sqlite_sha256, root / "sqlite-source")
    python = extract(Path(python_source), python_sha256, root / "python-source")
    ffi = extract(Path(ffi_source), ffi_sha256, root / "ffi-source")
    sqlprefix = root / "sqlite"
    ffiprefix = root / "libffi"
    pyprefix = root / "python"
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}

    def run(command, cwd, extra=None):
        subprocess.run(command, cwd=cwd, env={**env, **(extra or {})}, check=True, timeout=1200)

    run(["./configure", "--prefix=" + str(sqlprefix), "--enable-fts5", "--disable-static"], sqlite)
    run(["make", "-j" + str(jobs)], sqlite)
    run(["make", "install"], sqlite)
    run(["./configure", "--prefix=" + str(ffiprefix), "--libdir=" + str(ffiprefix / "lib"), "--disable-static"], ffi)
    run(["make", "-j" + str(jobs)], ffi)
    run(["make", "install"], ffi)
    flags = {
        "CPPFLAGS": "-I" + str(sqlprefix / "include") + " -I" + str(ffiprefix / "include"),
        "LDFLAGS": "-L"
        + str(sqlprefix / "lib")
        + " -Wl,-rpath,"
        + str(sqlprefix / "lib")
        + " -L"
        + str(ffiprefix / "lib")
        + " -Wl,-rpath,"
        + str(ffiprefix / "lib"),
        "PKG_CONFIG_PATH": str(sqlprefix / "lib/pkgconfig") + ":" + str(ffiprefix / "lib/pkgconfig"),
        "LIBFFI_CFLAGS": "-I" + str(ffiprefix / "include"),
        "LIBFFI_LIBS": "-L" + str(ffiprefix / "lib") + " -Wl,-rpath," + str(ffiprefix / "lib") + " -lffi",
        "LIBSQLITE3_CFLAGS": "-I" + str(sqlprefix / "include"),
        "LIBSQLITE3_LIBS": "-L" + str(sqlprefix / "lib") + " -Wl,-rpath," + str(sqlprefix / "lib") + " -lsqlite3",
    }
    run(
        [
            "./configure",
            "--prefix=" + str(pyprefix),
            "--with-ensurepip=install",
            "--disable-test-modules",
            "--without-static-libpython",
        ],
        python,
        flags,
    )
    run(["make", "-j" + str(jobs)], python, flags)
    run(["make", "install"], python, flags)
    interpreter = pyprefix / "bin/python3.12"
    probe = "import sys,json;sys.path.insert(0,sys.argv[1]);from nana_core.host_requirements import sqlite_runtime_report,python_runtime_report;print(json.dumps({'python':list(sys.version_info[:3]),'sqlite':sqlite_runtime_report(),'native':python_runtime_report()}))"
    source_root = str(Path(__file__).resolve().parents[2] / "src")
    observed = json.loads(
        subprocess.check_output([str(interpreter), "-I", "-c", probe, source_root], env=env, text=True)
    )
    if observed["python"][:2] != [3, 12] or not observed["sqlite"]["supported"] or not observed["native"]["supported"]:
        raise ValueError("PRIVATE_BINDING_UNQUALIFIED")
    receipt = {
        "execution": "REAL_NONROOT_SOURCE_BUILD_NOT_SYSTEM_INSTALL",
        "interpreter": str(interpreter),
        "sqlite_prefix": str(sqlprefix),
        "libffi_prefix": str(ffiprefix),
        "source_sha256": {"sqlite": sqlite_sha256, "python": python_sha256, "libffi": ffi_sha256},
        "observed": observed,
        "system_python_changed": False,
        "runtime_monkeypatch": False,
        "network_in_build": False,
        "LD_PRELOAD": False,
    }
    (root / "build-result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--sqlite-source", type=Path, required=True)
    p.add_argument("--sqlite-sha256", required=True)
    p.add_argument("--python-source", type=Path, required=True)
    p.add_argument("--python-sha256", required=True)
    p.add_argument("--ffi-source", type=Path, required=True)
    p.add_argument("--ffi-sha256", required=True)
    a = p.parse_args()
    print(
        json.dumps(
            build(
                a.root, a.sqlite_source, a.sqlite_sha256, a.python_source, a.python_sha256, a.ffi_source, a.ffi_sha256
            ),
            indent=2,
        )
    )
