"""Bounded provisional text from OpenAI SSE; never a fact or execution verdict.

Original complete JSON/schema/source validation still decides the final result.
No callback sees reasoning content, tool calls, credentials or response headers.
"""

import json
import time
from ...contracts import CoreError
from ..privacy import _json_object


def json_object(raw):
    def reject(_):
        raise ValueError("nonfinite JSON")

    return json.loads(raw, object_pairs_hook=_json_object, parse_constant=reject)


class DraftPrefix:
    """Read only root.draft.text from a valid JSON prefix, with proper escapes.

    A key-looking phrase inside interpretation is never a field. Partial text
    remains provisional: a later duplicate field or invalid complete object must
    clear it. No attempt is made to repair malformed provider JSON.
    """

    def __init__(self):
        self.raw = ""
        self.emitted = ""
        self.decoder = json.JSONDecoder()
        self.blocked = False

    def _field(self, text, start, wanted):
        i = start + 1
        seen = set()
        while True:
            while i < len(text) and text[i].isspace():
                i += 1
            if i >= len(text):
                raise ValueError()
            if text[i] == "}":
                return None
            key, end = self.decoder.raw_decode(text, i)
            if type(key) is not str or key in seen:
                raise ValueError()
            seen.add(key)
            i = end
            while i < len(text) and text[i].isspace():
                i += 1
            if i >= len(text) or text[i] != ":":
                raise ValueError()
            i += 1
            while i < len(text) and text[i].isspace():
                i += 1
            if i >= len(text):
                raise ValueError()
            if key == wanted:
                return i
            _, i = self.decoder.raw_decode(text, i)
            while i < len(text) and text[i].isspace():
                i += 1
            if i >= len(text):
                raise ValueError()
            if text[i] == "}":
                return None
            if text[i] != ",":
                raise ValueError()
            i += 1

    def feed(self, fragment):
        if type(fragment) is not str or len(self.raw) + len(fragment) > 65536:
            raise CoreError("PROVIDER_STREAM_CONTENT_BOUND")
        self.raw += fragment
        if self.blocked:
            return ""
        text = self.raw.lstrip()
        try:
            if not text.startswith("{"):
                return ""
            draft = self._field(text, 0, "draft")
            if draft is None or text[draft] != "{":
                return ""
            start = self._field(text, draft, "text")
            if start is None or text[start] != '"':
                return ""
            i = start + 1
            while i < len(text):
                if text[i] == '"':
                    break
                if ord(text[i]) < 32:
                    raise ValueError()
                if text[i] == "\\":
                    if i + 1 >= len(text):
                        break
                    if text[i + 1] == "u":
                        if i + 6 > len(text):
                            break
                        if any(c not in "0123456789abcdefABCDEF" for c in text[i + 2 : i + 6]):
                            raise ValueError()
                        i += 6
                        continue
                    if text[i + 1] not in '"\\/bfnrt':
                        raise ValueError()
                    i += 2
                    continue
                i += 1
            value = json.loads('"' + text[start + 1 : i] + '"')
            if value and 0xD800 <= ord(value[-1]) <= 0xDBFF:
                value = value[:-1]
            value.encode("utf-8")  # never emit an unpaired escaped surrogate
            if len(value) > 4096:
                raise CoreError("PROVIDER_STREAM_DRAFT_BOUND")
            if not value.startswith(self.emitted):
                self.blocked = True
                return ""
            delta = value[len(self.emitted) :]
            self.emitted = value
            return delta
        except (ValueError, IndexError, UnicodeError):
            return ""


class OpenAIEvents:
    def __init__(self, publish):
        self.publish = publish
        self.prefix = DraftPrefix()
        self.content = ""
        self.model = None
        self.response_id = None
        self.usage = None
        self.finish_reason = None
        self.done = False

    def event(self, data):
        if self.done:
            raise CoreError("PROVIDER_STREAM_AFTER_DONE")
        if data == "[DONE]":
            self.done = True
            return
        row = json_object(data)
        if type(row) is not dict:
            raise CoreError("PROVIDER_STREAM_INVALID")
        model = row.get("model")
        if model is not None:
            if type(model) is not str or not 1 <= len(model) <= 96 or (self.model and self.model != model):
                raise CoreError("PROVIDER_STREAM_MODEL_CHANGED")
            self.model = model
        if self.response_id is None:
            self.response_id = row.get("id")
        choices = row.get("choices")
        if type(choices) is not list or len(choices) > 1:
            raise CoreError("PROVIDER_STREAM_INVALID")
        if row.get("usage") is not None:
            self.usage = row["usage"]
        if not choices:
            return
        choice = choices[0]
        if type(choice) is not dict or choice.get("index", 0) != 0:
            raise CoreError("PROVIDER_STREAM_INVALID")
        delta = choice.get("delta")
        if type(delta) is not dict or delta.get("role", "assistant") != "assistant" or delta.get("tool_calls"):
            raise CoreError("PROVIDER_STREAM_INVALID")
        fragment = delta.get("content")
        if fragment is not None:
            if self.finish_reason is not None:
                raise CoreError("PROVIDER_STREAM_AFTER_FINISH")
            if type(fragment) is not str:
                raise CoreError("PROVIDER_STREAM_INVALID")
            self.content += fragment
            piece = self.prefix.feed(fragment)
            if piece:
                self.publish(piece)
        finish = choice.get("finish_reason")
        if finish is not None:
            if type(finish) is not str or self.finish_reason is not None:
                raise CoreError("PROVIDER_STREAM_INVALID")
            self.finish_reason = finish

    def envelope(self):
        if not self.done or self.finish_reason is None or not self.model:
            raise CoreError("PROVIDER_STREAM_INTERRUPTED_BILLING_UNKNOWN")
        return {
            "id": self.response_id,
            "model": self.model,
            "choices": [
                {"message": {"role": "assistant", "content": self.content}, "finish_reason": self.finish_reason}
            ],
            **({"usage": self.usage} if self.usage is not None else {}),
        }


def read_piece(response, size, deadline=None):
    """One available bounded chunk, with an absolute per-attempt deadline.

    read()/readline() can wait forever if a peer trickles before each socket
    timeout. HTTPResponse.read1() returns available bytes; the next read uses
    only the remaining deadline, never a fresh full-call timeout.
    """
    if deadline is not None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("PROVIDER_TIMEOUT")
        sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
        if sock is not None:
            sock.settimeout(remaining)
    chunk = (getattr(response, "read1", None) or response.read)(size)
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("PROVIDER_TIMEOUT")
    return chunk


def read_body(response, bound, deadline):
    data = bytearray()
    while len(data) <= bound:
        chunk = read_piece(response, min(4096, bound - len(data) + 1), deadline)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def response_lines(response, bound, deadline):
    pending = bytearray()
    received = 0
    while True:
        chunk = read_piece(response, min(4096, bound - received + 1), deadline)
        if not chunk:
            if pending:
                yield bytes(pending)
            return
        received += len(chunk)
        if received > bound:
            raise CoreError("PROVIDER_RESPONSE_BOUND")
        pending.extend(chunk)
        while (end := pending.find(b"\n")) >= 0:
            if end + 1 > 65536:
                raise CoreError("PROVIDER_RESPONSE_BOUND")
            line = bytes(pending[: end + 1])
            del pending[: end + 1]
            yield line
        if len(pending) > 65536:
            raise CoreError("PROVIDER_RESPONSE_BOUND")


def receive(response, bound, publish, *, deadline=None):
    """Return reconstructed OpenAI envelope plus exactly consumed SSE bytes."""
    parser = OpenAIEvents(publish)
    raw = bytearray()
    fields = []
    events = 0
    for line in response_lines(response, bound, deadline):
        raw.extend(line)
        text = line.decode("utf-8").rstrip("\r\n")
        if not text:
            if fields:
                events += 1
                if events > 4096:
                    raise CoreError("PROVIDER_STREAM_EVENT_BOUND")
                parser.event("\n".join(fields))
                fields = []
                if parser.done:
                    break
        elif text.startswith("data:"):
            fields.append(text[5:].lstrip(" "))
        elif text.startswith(":") or text.startswith(("event:", "id:", "retry:")):
            continue
        else:
            raise CoreError("PROVIDER_STREAM_INVALID")
    return parser.envelope(), bytes(raw)
