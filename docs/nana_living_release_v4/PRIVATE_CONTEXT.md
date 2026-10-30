# Explicit personal context (additive live/v2 contract)

The default stays PUBLIC/PROJECT. SECRET is not a valid gateway message or
projection scope. No real private history or personal provider call was used.

PERSONAL requires all of the following independent conditions:

1. Host-approved `binding.privacy` contains PERSONAL, with the existing exact
   Subject/lineage/entity/scope. No identity is created by this configuration.
2. Host application `roles` explicitly permits `PRIVATE_CONTEXT`. A paired device
   must receive that role in an explicit original Host Admin pairing offer.
   Old paired devices do not gain this scope when the host widens its binding.
   This role is application read/conversation scope, not a Core Grant or Manager.
3. The existing `nana.space` SurfaceBinding permits PERSONAL. Retention additionally
   requires its existing `allow_personal_retention` and named consent reference,
   plus the user's per-message “remember this experience” choice.
4. Actual model dispatch still intersects the original provider/route/runtime
   privacy and budget policies. This change never authorizes remote PERSONAL,
   paid calls, platform sends, personal history import or a new credential.

The paired UI offers a per-message PERSONAL choice only for an authenticated
scope. It does not relabel PERSONAL as PROJECT after a permission change.
Remember/privacy choices survive ordinary ChatPane remounts with their draft;
identity/run/scope/source changes clear the draft and its choices together.
There is no browser body cache or second transcript/Memory Store.

Original MemoryService/Person-Self, ContextAssembler, Inspector and privacy
journal provide persisted speech, source-filtered reads and withdrawal. Receipts
remain body-free on disk; cached volatile bodies are withheld after scope/source
changes. A shared invalidation ring exposes no private source references.

An installed runtime declares `private_context_contract=1`. With a personal host
binding, an incompatible rollback target is rejected before stopping a healthy
owner. Old default PUBLIC/PROJECT clients and pairings remain supported.
Host preparation must include this explicit scope in the consolidated approval;
never edit production permissions or re-pair a device implicitly.

Qualification: original Core/HTTP synthetic PERSONAL retained→restart→read→
withdrawal, old-device isolation, provider/surface refusal and incompatible
rollback PASS. Real TLS DEV browser at desktop/360/390/412 widths PASS. Initial
browser failures exposed checkbox remount resets and are preserved beside the
fix. Actual private history, real remote model and physical phone remain NOT_RUN.
