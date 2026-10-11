"""One-way allowlist boundary. Never walks objects or formats input exceptions."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import hmac
import re

PROBE = re.compile(r'nana-probe-[a-z0-9-]{1,48}\Z')
LABEL = re.compile(r'[a-zA-Z][a-zA-Z0-9_.-]{0,47}\Z')
FORBIDDEN_VALUE = re.compile(r'(?:sk-|gh[pousr]_|github_pat_|Bearer |eyJ|token|cookie|session)', re.I)

@dataclass(frozen=True, slots=True)
class Metadata:
    platform: str | None
    type: str | None
    event_id: str
    timestamp: str | None
    conversation_hash: str | None
    sender_hash: str | None
    event_source: str
    synthetic: bool
    probe_id: str

    def public(self):
        return asdict(self)

@dataclass(frozen=True, slots=True)
class SanitizeResult:
    status: str
    metadata: Metadata | None = None

class MetadataSanitizer:
    def __init__(self, *, scope: str, hash_key: bytes, probe_ids: frozenset[str]):
        if type(scope) is not str or not LABEL.fullmatch(scope): raise ValueError('INVALID_HASH_SCOPE')
        if type(hash_key) is not bytes or len(hash_key) != 32: raise ValueError('INVALID_SCOPED_HASH_KEY')
        if type(probe_ids) is not frozenset or not probe_ids or any(type(p) is not str or not PROBE.fullmatch(p) for p in probe_ids):
            raise ValueError('INVALID_PROBE_SCOPE')
        self.scope, self._key, self.probe_ids = scope, hash_key, probe_ids

    def scoped_hash(self, kind, value):
        if type(value) is not str or not 1 <= len(value) <= 256: raise ValueError('INVALID_METADATA_ID')
        # Length-delimited scope prevents concatenation ambiguity; independent domains.
        parts = [self.scope, kind, value]
        msg = b''.join(len(p.encode()).to_bytes(4, 'big') + p.encode() for p in parts)
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()

    def sanitize(self, event):
        try:
            # Exact built-in dict only: no getters, repr, getattr, custom Mapping,
            # raw serialization, iteration over unknown values, nested traversal.
            if type(event) is not dict or len(event) > 64: return SanitizeResult('DROP_SHAPE')
            probe = event.get('probe_id')
            if type(probe) is not str or probe not in self.probe_ids or not PROBE.fullmatch(probe):
                return SanitizeResult('DROP_PROBE_SCOPE')
            if event.get('synthetic') is not True or event.get('event_source') != 'operator_probe':
                return SanitizeResult('DROP_NOT_INTERNAL_PROBE')
            def label(key):
                v = event.get(key)
                if v is None: return None
                if type(v) is not str or not LABEL.fullmatch(v) or FORBIDDEN_VALUE.search(v):
                    raise ValueError('INVALID_METADATA_LABEL')
                return v
            def identifier(key, required=False):
                v = event.get(key)
                if v is None and not required: return None
                return self.scoped_hash(key, v)
            raw_time = event.get('timestamp')
            timestamp = None
            if raw_time is not None:
                if type(raw_time) is not str or len(raw_time) > 40: raise ValueError('INVALID_METADATA_TIME')
                dt = datetime.fromisoformat(raw_time)
                if dt.tzinfo is None: raise ValueError('NAIVE_METADATA_TIME')
                timestamp = dt.astimezone(timezone.utc).isoformat()
            return SanitizeResult('ACCEPT', Metadata(label('platform'), label('type'), identifier('event_id', True),
                timestamp, identifier('conversation_id'), identifier('sender_id'), 'operator_probe', True, probe))
        except BaseException:
            # Do not expose exception text/type from attacker-controlled objects.
            return SanitizeResult('DROP_INVALID_METADATA')

    def validate_output(self, metadata):
        if type(metadata) is not Metadata: raise ValueError('SANITIZED_METADATA_REQUIRED')
        p = metadata.public()
        if p['synthetic'] is not True or p['event_source'] != 'operator_probe' or p['probe_id'] not in self.probe_ids:
            raise ValueError('METADATA_SCOPE_DRIFT')
        for key in ('event_id', 'sender_hash', 'conversation_hash'):
            v = p[key]
            if (key=='event_id' and v is None) or (v is not None and (type(v) is not str or not re.fullmatch(r'[0-9a-f]{64}', v))):
                raise ValueError('METADATA_ID_NOT_HASHED')
        for key in ('platform', 'type'):
            v = p[key]
            if v is not None and (type(v) is not str or not LABEL.fullmatch(v) or FORBIDDEN_VALUE.search(v)):
                raise ValueError('METADATA_LABEL_INVALID')
        if p['timestamp'] is not None:
            dt = datetime.fromisoformat(p['timestamp'])
            if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0: raise ValueError('METADATA_TIME_INVALID')
        return metadata
