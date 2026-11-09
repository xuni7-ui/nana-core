"""Bounded view of explicitly retained speech in the original Subject Store.

No transcript database or recovery of unretained text. Source withdrawal and
privacy are checked before reading speech; reported wording is never truth.
"""

import json

from ..continuity.person_self import rows
from ..continuity.records import RecordService
from ..contracts import CoreError


def memory_use_sources(records, record, *, privacy, entity_id, scope):
    """Bounded statement choices, not evidence that the reply mentioned them.

    Only retained user wording is suitable for this first product entry. Internal
    model proposals, feedback bodies and operational metadata stay out of it.
    The original LanguageService independently rechecks the chosen dependency.
    """
    sources = []
    for mid in records.support(record['record_id'])[:64]:
        if mid == record['payload']['user_memory_id']:
            continue
        try:
            memory = records.memory.read(mid)
        except CoreError:
            continue
        provenance = memory['source_provenance']
        if (memory['entity_id'] != entity_id or memory['scope'] != scope
                or memory['privacy_class'] not in privacy
                or provenance['domain'] != 'CONSENTED_INTERACTION'
                or provenance['source_namespace'] != 'recorded.conversation.input'
                or provenance['source_kind'] != 'USER_STATEMENT'):
            continue
        sources.append({'memory_id': mid, 'excerpt': memory['text'][:160]})
        if len(sources) == 8:
            break
    return sources


def history(app, *, privacy, scope=None, entity_id=None):
    permitted = tuple(p for p in privacy if p in app.policy.readable_privacy and p in {"PUBLIC", "PROJECT", "PERSONAL"})
    store = app.runtime.store
    records = RecordService(store)
    items, size, omitted = [], 0, 0
    scope = app.runtime.config.scopes[0] if scope is None else scope
    entity_id = app.runtime.config.entity_id if entity_id is None else entity_id
    visible = rows(store, "CONVERSATION_EXCHANGE", scope, permitted, limit=96) if scope in app.policy.allowed_scopes else ()
    for record in visible:
        data = record["payload"]
        if data["entity_id"] != entity_id:
            continue
        try:
            source = records.memory.read(data["user_memory_id"])
            if source["privacy_class"] not in permitted:
                continue
            item = {"exchange_record_id": record["record_id"],
                    "message_id": source["source_provenance"]["source_reference"],
                    "user_text": source["text"], "reply_text": data["assistant_utterance"],
                    "created_at_us": data["as_of_us"], "source_refs": list(records.support(record["record_id"])),
                    "memory_use_sources": memory_use_sources(records, record, privacy=permitted,
                                                               entity_id=entity_id, scope=scope),
                    "memory_use_delivery_proven": False}
            from ..continuity.lived_language import delivery_for_exchange
            delivery=delivery_for_exchange(records,record)
            if delivery:item['reply_delivery']=delivery
        except CoreError:
            continue
        encoded = len(json.dumps(item, ensure_ascii=False).encode())
        # Keep a complete admitted long reply recoverable. This finite UTF-8
        # projection budget stays below the existing 256KiB IPC response cap.
        if len(items) >= 32 or size + encoded > 131072:
            omitted += 1
            continue
        size += encoded
        items.append(item)
    return {"items": list(reversed(items)), "omitted_count": omitted,
            "coverage": "EXPLICITLY_RETAINED_EXCHANGES_ONLY", "transient_history_restored": False,
            "epistemic_status": "REPORTED_SPEECH_NOT_WORLD_TRUTH"}
