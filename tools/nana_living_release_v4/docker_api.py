"""Operator-only local Unix Docker API; no Docker CLI or SDK dependency.

Never import this module into Nana Core/LLM. Daemon access is host authority.
Only explicit pinned images and our own temporary check containers are mutable.
No method stops/removes existing services, prunes images or reads their secrets.
"""

import contextlib
import http.client
import json
import re
import socket
import stat
import io
import struct
import tarfile
import time
import shutil
from uuid import uuid4
from pathlib import Path
from urllib.parse import urlencode


class DockerError(RuntimeError):
    pass


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=60):
        super().__init__("localhost", timeout=timeout)
        self.path = str(path)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


class Docker:
    def __init__(self, path="/var/run/docker.sock", *, local_vfs_headroom_mib=0):
        self.path = Path(path).absolute()
        if not stat.S_ISSOCK(self.path.stat().st_mode):
            raise DockerError("LOCAL_DOCKER_SOCKET_REQUIRED")
        self.__temporary = set()
        self.__headroom = max(local_vfs_headroom_mib, 0) * 1024 * 1024
        if self.__headroom and self.json("GET", "/info")["Driver"] != "vfs":
            raise DockerError("LOCAL_DEV_VFS_GUARD_CONTEXT_MISMATCH")

    def before_create(self):
        # Explicit DEV-only flag: this daemon shares the caller's root filesystem.
        # Wait for asynchronous deletion BEFORE dispatch, never retry a create.
        deadline = time.monotonic() + 30
        while self.__headroom and shutil.disk_usage("/").free < self.__headroom:
            if time.monotonic() >= deadline:
                raise DockerError("LOCAL_DEV_VFS_DISK_GUARD_NO_CREATE")
            time.sleep(.25)

    @contextlib.contextmanager
    def response(self, method, path, body=None, *, chunks=False, timeout=60):
        connection = UnixConnection(self.path, timeout)
        try:
            headers = {"Content-Type": "application/x-tar" if chunks else "application/json"}
            connection.request(method, path, body=body, headers=headers, encode_chunked=chunks)
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                message = response.read(4097)
                if b"bind source path does not exist" in message:
                    raise DockerError("DOCKER_BIND_SOURCE_MISSING")
                if b"no space left on device" in message:
                    raise DockerError("DOCKER_STORAGE_FULL")
                raise DockerError("DOCKER_HTTP_" + str(response.status))
            yield response
        finally:
            connection.close()

    def json(self, method, path, body=None, *, bound=2 * 1024 * 1024, timeout=60):
        with self.response(method, path, json.dumps(body).encode() if body is not None else None, timeout=timeout) as response:
            raw = response.read(bound + 1)
        if len(raw) > bound:
            raise DockerError("DOCKER_METADATA_BOUND")
        return json.loads(raw) if raw else None

    def version(self):
        value = self.json("GET", "/version")
        return {key: value.get(key) for key in ("Version", "ApiVersion", "Os", "Arch")}

    def containers(self):
        rows = self.json("GET", "/containers/json?all=true")
        return [{"id": row["Id"], "names": row["Names"], "state": row["State"]} for row in rows]

    def image(self, image):
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
            raise DockerError("PINNED_IMAGE_REQUIRED")
        row = self.json("GET", "/images/" + image + "/json")
        return {"id": row["Id"], "architecture": row["Architecture"], "os": row["Os"],
                "user": row["Config"].get("User"), "size": row["Size"],
                "diff_ids": row.get("RootFS", {}).get("Layers")}

    def inspect(self, container):
        if not re.fullmatch(r"[a-f0-9]{64}", container):
            raise DockerError("EXACT_CONTAINER_ID_REQUIRED")
        row = self.json("GET", "/containers/" + container + "/json")
        # Do not return Config.Env, labels, auth, arguments or private log bodies.
        return {"id": row["Id"], "name": row["Name"], "image": row["Image"],
                "state": {k: row["State"].get(k) for k in ("Status", "Running", "ExitCode", "StartedAt", "FinishedAt")},
                "user": row["Config"].get("User"), "network_mode": row["HostConfig"].get("NetworkMode"),
                "readonly_rootfs": row["HostConfig"].get("ReadonlyRootfs"),
                "restart_policy": row["HostConfig"].get("RestartPolicy", {}).get("Name"),
                "mounts": [{k: m.get(k) for k in ("Type", "Source", "Destination", "RW")} for m in row.get("Mounts", [])],
                "ports": row.get("NetworkSettings", {}).get("Ports", {})}

    def create_check(self, image, *, runtime=None, core_source=None):
        self.before_create()
        metadata = self.image(image)
        if metadata["user"] != "999:999" or metadata["architecture"] != "amd64" or metadata["os"] != "linux":
            raise DockerError("IMAGE_RUNTIME_CONTRACT_MISMATCH")
        host = {"NetworkMode": "none", "ReadonlyRootfs": True, "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges"], "PidsLimit": 32,
                "Memory": 256 * 1024 * 1024, "NanoCpus": 1000000000}
        if runtime is not None:
            host["Mounts"] = [{"Type": "bind", "Source": str(runtime), "Target": "/opt/nana-core/runtime", "ReadOnly": True}]
        config = {
            "Image": image, "Cmd": ["verify"], "User": "999:999", "NetworkDisabled": True,
            "HostConfig": host,
        }
        if core_source is not None:
            if not re.fullmatch(r"[a-f0-9]{40}", core_source):
                raise DockerError("PINNED_CORE_REQUIRED")
            root = "/opt/nana-core/runtime/core-releases/" + core_source
            code = ("import sys,json,runpy,ssl,sqlite3,pydantic;from pathlib import Path;"
                    "root=Path(sys.argv[1]);runpy.run_path(str(root/'bootstrap.py'))['verify'](root);"
                    "sys.path.insert(0,str(root/'src'));"
                    "from nana_core.host_requirements import require_sqlite_runtime;require_sqlite_runtime();"
                    "\nif sys.prefix!=str(root/'.venv'):raise ValueError('QUALIFIED_INTERPRETER_BINDING_MISMATCH')\n"
                    "print(json.dumps({'state':'PRIVATE_CORE_COMPATIBLE','python':sys.version.split()[0],"
                    "'sqlite':sqlite3.sqlite_version,'openssl':ssl.OPENSSL_VERSION,'pydantic':pydantic.__version__,"
                    "'subject_opened':False,'provider_calls':0}))")
            config.update(Entrypoint=[root + "/.venv/bin/python", "-I", "-B", "-c", code, root], Cmd=[])
        row = self.json("POST", "/containers/create", config)
        container = row["Id"]
        self.__temporary.add(container)
        return container

    def remove_check(self, container):
        if container not in self.__temporary:
            raise DockerError("EXISTING_CONTAINER_MUTATION_DENIED")
        self.json("DELETE", "/containers/" + container)  # Never force a running container.
        self.__temporary.remove(container)

    def verify_check(self, container):
        if container not in self.__temporary:
            raise DockerError("EXISTING_CONTAINER_MUTATION_DENIED")
        self.json("POST", "/containers/" + container + "/start")
        result = self.json("POST", "/containers/" + container + "/wait?condition=not-running")
        return {"state": "RUNTIME_ENTRY_VERIFIED" if result["StatusCode"] == 0 else "RUNTIME_ENTRY_FAILED",
                "exit_code": result["StatusCode"], "subject_opened": False}

    def runtime_archive(self, container, target):
        if container not in self.__temporary:
            raise DockerError("EXISTING_CONTAINER_ARCHIVE_DENIED")
        path = "/containers/" + container + "/archive?" + urlencode({"path": "/opt/nana-core/runtime/."})
        size = 0
        with self.response("GET", path) as response:
            while raw := response.read(1024 * 1024):
                size += len(raw)
                if size > 1024**3:
                    raise DockerError("RUNTIME_ARCHIVE_BOUND")
                target.write(raw)
        return size

    def operator(self, image, root, mode, files, arguments):
        """Disposable, isolated staging controller; no Docker socket in child."""
        self.before_create()
        self.image(image)
        if mode not in {"check", "dry-run", "install", "rollback", "commit"} or not Path(root).is_absolute():
            raise DockerError("EXPLICIT_OPERATOR_TARGET_REQUIRED")
        work = "/run/nana-operator"
        volume = "nana-operator-" + uuid4().hex
        self.json("POST", "/volumes/create", {"Name": volume, "Labels": {"life.nana.operator.scratch": "v4"}})
        config = {
            "Image": image, "User": "0:0", "NetworkDisabled": True,
            "Entrypoint": ["/usr/bin/python3", "-I", "-B", work + "/operator_stage.py"],
            "Cmd": [mode, "--root", str(root), *arguments],
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "CapDrop": ["ALL"],
                           "CapAdd": ["CHOWN", "FOWNER", "DAC_OVERRIDE"], "SecurityOpt": ["no-new-privileges"],
                           "PidsLimit": 32, "Memory": 1536 * 1024 * 1024, "NanoCpus": 1000000000,
                           "Tmpfs": {"/tmp": "rw,nosuid,nodev,noexec,size=16m"},
                           "Mounts": [{"Type": "volume", "Source": volume, "Target": work},
                                      {"Type": "bind", "Source": str(root), "Target": str(root), "ReadOnly": mode not in {"install", "commit"}}]},
        }
        try:
            row = self.json("POST", "/containers/create", config)
        except BaseException:
            self.json("DELETE", "/volumes/" + volume)
            raise
        container = row["Id"]
        self.__temporary.add(container)
        try:
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode="w") as archive:
                for name, raw in files.items():
                    if name in {".", ".."} or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,96}", name) or len(raw) > 8 * 1024 * 1024:
                        raise DockerError("OPERATOR_INPUT_DENIED")
                    entry = tarfile.TarInfo(name)
                    entry.mode, entry.size = 0o600, len(raw)
                    archive.addfile(entry, io.BytesIO(raw))
            # A unique volume survives the Engine's stopped->started transition;
            # a pre-start tmpfs upload would disappear when that tmpfs is mounted.
            with self.response("PUT", "/containers/" + container + "/archive?path=/run/nana-operator", iter([payload.getvalue()]), chunks=True):
                pass
            self.json("POST", "/containers/" + container + "/start")
            waited = self.json("POST", "/containers/" + container + "/wait?condition=not-running", timeout=180)
            with self.response("GET", "/containers/" + container + "/logs?stdout=1&stderr=0") as response:
                raw = response.read(262145)
            body = bytearray()
            while raw:
                if len(raw) < 8:
                    raise DockerError("OPERATOR_RECEIPT_INVALID")
                size = struct.unpack(">I", raw[4:8])[0]
                body.extend(raw[8:8 + size]); raw = raw[8 + size:]
                if len(body) > 262144:
                    raise DockerError("OPERATOR_RECEIPT_BOUND")
            result = json.loads(body)
            result["operator_exit_code"] = waited["StatusCode"]
            return result
        finally:
            self.remove_check(container)
            self.json("DELETE", "/volumes/" + volume)

    def load(self, chunks):
        with self.response("POST", "/images/load?quiet=true", chunks, chunks=True, timeout=180) as response:
            count = 0
            while raw := response.readline(65537):
                count += len(raw)
                if len(raw) > 65536 or count > 262144:
                    raise DockerError("DOCKER_LOAD_RESPONSE_BOUND")
                row = json.loads(raw)
                if row.get("error") or row.get("errorDetail"):
                    raise DockerError("DOCKER_IMAGE_LOAD_REJECTED")
