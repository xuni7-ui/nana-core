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
    def __init__(self, path="/var/run/docker.sock"):
        self.path = Path(path).absolute()
        if not stat.S_ISSOCK(self.path.stat().st_mode):
            raise DockerError("LOCAL_DOCKER_SOCKET_REQUIRED")
        self.__temporary = set()

    @contextlib.contextmanager
    def response(self, method, path, body=None, *, chunks=False, timeout=60):
        connection = UnixConnection(self.path, timeout)
        try:
            headers = {"Content-Type": "application/x-tar" if chunks else "application/json"}
            connection.request(method, path, body=body, headers=headers, encode_chunked=chunks)
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                raise DockerError("DOCKER_HTTP_" + str(response.status))
            yield response
        finally:
            connection.close()

    def json(self, method, path, body=None, *, bound=2 * 1024 * 1024):
        with self.response(method, path, json.dumps(body).encode() if body is not None else None) as response:
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
                "user": row["Config"].get("User"), "size": row["Size"]}

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

    def create_check(self, image):
        metadata = self.image(image)
        if metadata["user"] != "999:999" or metadata["architecture"] != "amd64" or metadata["os"] != "linux":
            raise DockerError("IMAGE_RUNTIME_CONTRACT_MISMATCH")
        row = self.json("POST", "/containers/create", {
            "Image": image, "Cmd": ["verify"], "User": "999:999", "NetworkDisabled": True,
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "CapDrop": ["ALL"],
                           "SecurityOpt": ["no-new-privileges"], "PidsLimit": 32,
                           "Memory": 256 * 1024 * 1024, "NanoCpus": 1000000000},
        })
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
