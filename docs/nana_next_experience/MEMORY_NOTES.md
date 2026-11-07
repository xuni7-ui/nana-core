# Explicit notes and corrections — same product / S2 refinement

The existing Memory page could preview drafts but had no save endpoint. This adds real authenticated note persistence and correction through the existing BFF → original owner IPC → MemoryService. No second memory, Store, schema, Subject, decision loop or model call. Product406 remains available; matching407 contains this addition.

## Public contract

POST /api/nana-space/v2/memories/notes: original WriteRequest revision/owner/run/idempotency fields, text1–2048chars, explicit privacy_class, consent=true (actual boolean, not1/string), optional target_id of a current user note. MANAGER required. PERSONAL additionally requires PRIVATE_CONTEXT/host privacy and the bound surface's existing personal-retention consent, checked again in Core. Native finite operation memories.note; optional capability memory_notes. Older BFF keeps draft-only UI. Generated canonical JSON Schema/OpenAPI/TypeScript updated additively; old required fields are unchanged.

New records are original SEMANTIC/STATEMENT memories with CONSENTED_INTERACTION, recorded.conversation.input, explicit note source reference, actual event/observation time, entity and scope. CURRENT means latest user declaration, not verified truth or Nana's own experience. Correction uses original correction_of/predicate family; cannot edit identity, external observations, actual experiences, lessons or Iris/archive claims. Privacy cannot be lowered. Old sources remain superseded; withdrawing the current source does not revive them. Recognizable credential patterns/structured credential fields are rejected before persistence; this is screening, not a claim of perfect secret detection.

Saving is VERIFIED only after an independent read-only original-Store lookup checks exact text/privacy/target/entity/scope/current source. A returned ID alone cannot fake saving. Stale target is rejected before dispatch. Existing ledger and Core source keys prevent duplicate commits; retired source keys cannot resurrect notes after withdrawal. Network UNKNOWN keeps the original receipt and never automatically retries; the UI disables resubmission and can GET the original receipt. No note text goes into localStorage, an APK configuration or gateway log.

## Actual user flow

Write note → select permitted scope → explicitly consent → save → original receipt → current memory card. The same card can update a user note; original observations offer withdrawal instead of editing their text. Source/provenance remain visible. Search can display up to the actual64-response horizon; ordinary recent view stays32. Private/identity/source changes clear transient drafts/results as before.

This proves storage, authorized retrieval and correction, not natural model recall. **Automatic chat recall of these new plain notes has not been qualified; merely saving or finding a note is not a claim that a future model answer recalls it accurately.** Existing language/Person-Self/ContextAssembler remain authoritative; follow-up retrieval work must be baseline-backed and source-aware. This product repair is developer work, not Nana self-learning. Original S8 renewal and Fish Heart native causal evidence are inherited unchanged.

## Validation and limits

Actual loopback BFF/original Core: save/idempotent receipt, correction, restart same subject, literal recall, withdrawal and no old-version revival. Current-source control/auth/archive21 tests passed9.11s; after final bound-surface/target preflight changes,4 actual note tests passed7.71s. Related HTTP/private/search13 passed24.38s.57 frontend unit tests;20 browser fixtures32.6s at desktop/360/390/412, including notes/correction/UNKNOWN no-repeat and old draft-only behavior. Android407 builds; exact hashes in evidence/memory-notes/apk.json. New-source complete release regression is pending, not copied from6f2a491.

Initial missing import alias, TypeScript variable typo and prior browser expectation for the replaced English provenance label are retained. One initial phone412 older-search run timed out; after inspecting its UI and retaining the failure, the unchanged timeout/test passed in the final scoped suite. The old recent32 bound is preserved; only explicit search uses64. No security assertion was broadened or test skipped.

Real provider/production/physical phone/private-history import/social/long-term memory quality NOT_RUN. Full source/API changes remain subject to matched candidate deployment by the original operator; no live config, identity or Vault has changed.


## Lost-response reconciliation completed before release

A real post-commit transport-loss test exposed the need for server-side reconciliation, beyond a UI GET button. Core now commits a sourced RUNTIME_WORK note proof bound to the original host-ledger request digest, principal/idempotency-derived opaque request ID and note support. It is metadata in the original Store, not a second memory/ledger or lived experience. Privacy retires/erases its payload with the note. GET the original UNKNOWN receipt independently checks this proof, current note, identity/scope/privacy and exact original request binding, then updates only the existing infrastructure receipt; no Core write/Provider redispatch. Actual Core stop/restart and host-ledger volatile-result reset still reconcile. Withdrawn/missing/unavailable/mismatched proof stays UNKNOWN; a crash before proof commit is not presumed successful and never authorizes retry. Returning another existing note ID cannot fake a save or reconciliation. Final6 actual-note tests passed11.08s, covering success, negative cases, real lost reply, restart and withdrawal; original initial failures remain. New modules formatted with the project-pinned Ruff0.14.1, AST-equivalent.

## Release verification found and fixed a real cross-domain regression

The initial full run at73fc941 failed:1694passed/185failed/55errors/12skipped521.98s. Most failures cascaded from exhausted owned synthetic /dev/shm storage; its raw log is retained, the inactive reproducible200001-row corpus was fingerprinted before retirement, and only owned finished test scratch was cleaned. A separate genuine H1 regression was independently reproduced: a new semantic revision of one source was suppressed by raw-root deduplication. Original coordinator/session now validates a changed sourced world snapshot and can send a pure concern back to original C without incrementing encounters. Same-world aliases, adopted work and UNKNOWN fences remain. The regression test requires two distinct C reviews, one encounter, zero action/goal and no revision replay. A complete passing rerun is still required.

UI also distinguishes explicit pre-admission revision/scope/validation rejection from transport UNKNOWN. Confirmed rejection permits correction; UNKNOWN still forbids another POST and only checks the original receipt. Unit59 and scoped responsive8 checks passed. No server rejection is falsely labelled saved.

## Matching407 delivery qualification

Final APK4.0.7-next-debug:4843428bytes SHA2565fed16c7819255a9681574563291ae3a058f9edd563e2ec73991e35882f37b20; source edd170f, same life.nana.space.dev/signer, all42 Web files byte-equal. This supersedes the earlier apk.json build; apk-final.json is authoritative. Core279files14989197bytes SHA2563ca1e517c23f43bfbce52678fde9d2514973f19d7eabd1dfeee5908b2a318159, two builds equal, actual offline installed probe including notes passed. HANDOFF_407.md preserves the existing sealed operator deployment/activation boundary and original V4 ZIP.

Full source run:1933passed/1failed/12skipped604.46s; sole failure is repository current-state evidence_refs9 exceeding its fixed8 bound. Compacted to7refs while preserving historical evidence; existing failing review-preparation test and new delivery checks5passed0.21s. Runtime code unchanged by this document repair; no second whole-suite success is claimed. Skip11 live-screen opt-in and1 live-model endpoint gate remain. Initial failure logs and all receipts retained. New read-only delivery verifier independently checks hashes, actual archived Core source and actual APK/Web equality; tests include changed file, stale Core despite new outer hashes, mismatched Web and path traversal. No claim of independent frontend source attestation beyond the build pipeline.

Next baseline is explicit: a synthetic note was saved but not selected into either actual loopback conversation phase. note-recall-baseline.json records this failure without claiming real semantic recall, then continues the same S2/S8 refinement.
