"""Authorized public source reader and evidence-based locator, via existing ports.

URL/method bindings are immutable operator records, never model parameters.
The downloaded document is untrusted data. No link following or code execution.
"""
import base64
from html.parser import HTMLParser
import json
from ..contracts import CoreError, Receipt, SourceArgs, Verification
from ..storage import canonical, digest, uid
from .public_http import FetchResponse, PublicHTTPTransport, WebSpec


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "br", "div", "h1", "h2", "li"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden-1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(body, content_type):
    if not content_type.startswith(("text/plain", "text/html")):
        raise CoreError("WEB_CONTENT_TYPE_REJECTED")
    text = body.decode("utf-8", errors="replace")
    if content_type.startswith("text/html"):
        parser = TextExtractor(); parser.feed(text); parser.close()
        text = "".join(parser.parts)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


class WebSourcePort:
    def __init__(self, store, bindings, journal, authority, transport=None):
        if journal.path.resolve() == store.path.resolve():
            raise CoreError("WEB_JOURNAL_MUST_BE_SEPARATE")
        if not bindings or any(not key.startswith("source://public/") for key in bindings):
            raise CoreError("PUBLIC_SOURCE_BINDINGS_REQUIRED")
        self.store, self.journal, self.path = store, journal, journal.path
        self.last_error = None
        self._bindings = {key: WebSpec.model_validate(spec.model_dump()) for key, spec in bindings.items()}
        self.transport = transport or PublicHTTPTransport()
        for resource, spec in self._bindings.items():
            if (spec.provenance == "public_read") != bool(self.transport.is_public_transport):
                raise CoreError("WEB_TRANSPORT_PROVENANCE_MISMATCH")
            key = "development.web_binding:" + resource
            value = {"spec": spec.model_dump(), "binding_hash": digest(spec.model_dump()), "issuer": authority.principal}
            old = store.one("core_meta", key)
            if old:
                if json.loads(old["value_json"]) != value:
                    raise CoreError("WEB_BINDING_COLLISION")
            else:
                with store.transaction("authorization.web_source_bound", {"resource": resource, **value}) as tx:
                    tx.put("core_meta", {"key": key, "value_json": canonical(value)})

    def _spec(self, invocation):
        args = SourceArgs.model_validate(invocation.args)
        if (invocation.capability not in {"reading.source.read", "reading.source.locate"}
            or args.source_id != invocation.resource or invocation.args_hash != digest(invocation.args)):
            raise CoreError("INVALID_WEB_SOURCE_INVOCATION")
        spec = self._bindings.get(invocation.resource)
        old = self.store.one("core_meta", "development.web_binding:"+invocation.resource)
        if not spec or not old or json.loads(old["value_json"])["binding_hash"] != digest(spec.model_dump()):
            raise CoreError("AUTHORIZED_WEB_BINDING_REQUIRED")
        return spec

    def _read_result(self, invocation, spec, response):
        if (not isinstance(response, FetchResponse) or response.approved_url != spec.url
            or response.method != spec.method or not 200 <= response.status < 300
            or len(response.body) > spec.max_bytes):
            raise CoreError("WEB_RESPONSE_CONTRACT_REJECTED")
        content_type = response.headers.get("content-type", "")
        text = plain_text(response.body, content_type) if spec.method == "GET" else "HEAD metadata only; no document body."
        if not text or bool(response.evidence.get("public_fetch")) != (spec.provenance == "public_read"):
            raise CoreError("WEB_RESPONSE_PROVENANCE_REJECTED")
        return {"source_id": invocation.resource, "text": text, "source_digest": digest(text.encode()),
            "source_blob_sha256": digest(response.body), "source_url": response.approved_url,
            "method": response.method, "status": response.status, "fetched_at_us": response.fetched_at_us,
            "response_headers": response.headers, "body_b64": base64.b64encode(response.body).decode(),
            "text_derivation": "UTF-8 replacement decode; HTML scripts/styles excluded; full raw bytes retained",
            "body_coverage": "HEAD_NO_BODY" if spec.method == "HEAD" else "FULL", "trust": "UNTRUSTED_SOURCE_DATA", "provenance": spec.provenance,
            "binding_hash": digest(spec.model_dump()), "transport_evidence": response.evidence,
            "read_action_id": invocation.action_id, "read_operation_key": invocation.idempotency_key}

    def _verified_upstream(self, invocation):
        action = self.store.one("actions", invocation.action_id)
        if not action or not action["goal_id"] or not action["plan_id"]:
            raise CoreError("VERIFIED_UPSTREAM_READ_REQUIRED")
        reads = [a for a in self.store.all("actions") if a["goal_id"] == action["goal_id"]
                 and a["plan_id"] == action["plan_id"] and a["resource"] == invocation.resource
                 and a["capability"] == "reading.source.read" and a["state"] == "SUCCEEDED"]
        if len(reads) != 1:
            raise CoreError("VERIFIED_UPSTREAM_READ_REQUIRED")
        read = reads[0]; result = json.loads(read["result_json"])
        row = self.journal.db.execute("SELECT * FROM operations WHERE operation_key=?", (read["idempotency_key"],)).fetchone()
        if not row or json.loads(row["result_json"]) != result or result["method"] != "GET":
            raise CoreError("VERIFIED_UPSTREAM_READ_REQUIRED")
        return read, result

    @staticmethod
    def _locator_result(invocation, spec, read, upstream):
        return {"source_id": invocation.resource, "source_digest": upstream["source_digest"],
            "source_blob_sha256": upstream["source_blob_sha256"], "source_url": upstream["source_url"],
            "locator": upstream["source_url"]+" (verified document, extracted line 1)",
            "upstream_action_id": read["action_id"],
            "upstream_verification_event_id": json.loads(read["body_json"])["verification_event_id"],
            "binding_hash": digest(spec.model_dump()), "provenance": spec.provenance}

    def execute(self, invocation):
        spec = self._spec(invocation)
        db = self.journal.db
        old = db.execute("SELECT * FROM operations WHERE operation_key=?", (invocation.idempotency_key,)).fetchone()
        if old:
            if (old["capability"], old["resource"], old["args_hash"]) != (
                invocation.capability, invocation.resource, invocation.args_hash):
                raise CoreError("IDEMPOTENCY_COLLISION")
            return Receipt(external_id=old["external_id"], result=json.loads(old["result_json"]))
        db.execute("INSERT INTO calls(operation_key,capability,resource,kind) VALUES(?,?,?,'EXECUTE')",
                   (invocation.idempotency_key, invocation.capability, invocation.resource))
        if invocation.capability == "reading.source.read":
            try:
                result = self._read_result(invocation, spec, self.transport.fetch(spec))
            except CoreError as exc:
                self.last_error = exc.code
                raise
        else:
            read, upstream = self._verified_upstream(invocation)
            result = self._locator_result(invocation, spec, read, upstream)
        external_id = uid()
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)", (invocation.idempotency_key,
                invocation.capability, invocation.resource, invocation.args_hash, canonical(result), external_id))
            if invocation.capability == "reading.source.read" and spec.method == "GET":
                db.execute("INSERT INTO sources VALUES(?,?,?) ON CONFLICT(source_id) DO UPDATE SET text=excluded.text,pages_json=excluded.pages_json",
                    (invocation.resource, result["text"], canonical([{"text": result["text"], "locator": result["source_url"]}])))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        return Receipt(external_id=external_id, result=result)

    def verify(self, invocation):
        spec = self._spec(invocation)
        db = self.journal.db
        db.execute("INSERT INTO calls(operation_key,capability,resource,kind) VALUES(?,?,?,'VERIFY')",
                   (invocation.idempotency_key, "reading.action.verify", invocation.resource))
        row = db.execute("SELECT * FROM operations WHERE operation_key=?", (invocation.idempotency_key,)).fetchone()
        if not row:
            return Verification(verdict="INCONCLUSIVE", evidence={"reason": "NO_DURABLE_HTTP_RECEIPT", "no_refetch": True})
        result = json.loads(row["result_json"])
        matches = (row["capability"], row["resource"], row["args_hash"]) == (
            invocation.capability, invocation.resource, invocation.args_hash)
        matches = matches and result["binding_hash"] == digest(spec.model_dump()) and result["source_url"] == spec.url
        if invocation.capability == "reading.source.read":
            raw = base64.b64decode(result["body_b64"], validate=True)
            text = plain_text(raw, result["response_headers"].get("content-type", "")) if spec.method == "GET" else "HEAD metadata only; no document body."
            matches = bool(matches and len(raw) <= spec.max_bytes and result["source_blob_sha256"] == digest(raw)
                and result["text"] == text and result["source_digest"] == digest(text.encode())
                and result["method"] == spec.method and 200 <= result["status"] < 300
                and result["body_coverage"] == ("HEAD_NO_BODY" if spec.method == "HEAD" else "FULL")
                and (spec.method != "HEAD" or raw == b"")
                and result["read_action_id"] == invocation.action_id and result["read_operation_key"] == invocation.idempotency_key)
        else:
            read, upstream = self._verified_upstream(invocation)
            matches = bool(matches and result == self._locator_result(invocation, spec, read, upstream))
        return Verification(verdict="MATCH" if matches else "EFFECT_MISMATCH", evidence={
            "result": result, "operation_key": invocation.idempotency_key, "external_id": row["external_id"],
            "independent_readback": True, "verification_scope": "durable HTTP evidence and body hash; no network re-fetch",
            "external_world": spec.provenance})
