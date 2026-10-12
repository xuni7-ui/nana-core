# R042 — first one-shot production trust onboarding

Status: development implementation; no real authorization, production pin, host
operation, message or runtime proof created by Codex. Default shipping seal EMPTY.
R041 baseline c7d87018335de0797177f53bf8986f06e1e78eef. Approved Core stays ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513.

## Audit finding / boundary

R041 has a complete receipt ledger but no seal builder: one_shot.py and
one_shot_proof.py contain empty MappingProxyType maps. Its operator review/arm
cannot proceed in production. Hand-editing Python was the missing operation.
R042 adds an offline, explicit, build-time seal; not runtime trust configuration.
No new Core SQL tables/dependencies/identity/Store/ledger. Package hash checks run
before support/private runtime imports. AstrBot still imports stdlib-only client.
D-045 double permit/sanitizer gates and D-046 terminal single consumption remain.

The trust root is **an authorized, independently reviewed source build**, not a
JSON field asserting "real". Nana must verify real host metadata and Sister's
exact authorization before committing the review. Git commit/hash pins those
reviewed bytes, not the identity/honesty of their author. A privileged malicious
builder, a forged independent review knowingly accepted by the operator, or
whole-DB cloning outside the approved backup/replay protocol are NOT prevented
by hashes. Do not claim authentication of arbitrary documents as Nana evidence.
Runtime observations/fixtures/config/environment/CLI cannot set or promote pins.
The explicit offline seal command is a privileged artifact build operation and
must never be invoked by an Observer, worker, or on unreviewed fixture material.

## Immutable source locations

Default `tools/nana_astrbot_shadow/sealed_trust.py`: EMPTY, both maps empty.
Packaged copy: `package/support/tools/nana_astrbot_shadow/sealed_trust.py`.
An explicitly reviewed candidate has exactly one PRODUCTION_REVIEW_PINS entry:
review_receipt_digest -> authorization_digest, plus EXACT_RECEIPT_DIGEST and
EXACT_STORE_BINDING. It records full REVIEW_SOURCE_SHA. No wildcard/range/force,
no environment/config file/DB lookup. Caller-provided receipt/review files are
untrusted until their exact source seal validates. MappingProxyType read-only.
Any byte change requires new manifest/files/SHA256SUMS/archive SHA; old kits and
commits are preserved. Verify archive SHA through independent trusted delivery;
self-contained hashes alone do not authenticate an arbitrary replacement kit.

## Sequence / commands (future Nana + operator, NOT executed by Codex)

All paths below are example independent Shadow paths, never AstrBot/Iris paths.
Do not install into AstrBot Python, inject private _sqlite3, use JWT/Dashboard via
CLI, restart, send, or switch owner. Upload/install/load are separate manual
operator operations. Use existing approved R041 hook/client/runbook for them.
Build/audit prerequisites should be ready before the 600-second receipt window.

1. Verify the delivered EMPTY R042 archive SHA, extract to a NEW kit directory.
   Create a NEW private Shadow directory outside the package's mutable data area:

   ```sh
   mkdir -m 700 /opt/nana_shadow/r042-store
   ./r04.sh receipt init --directory /opt/nana_shadow/r042-store
   ```

   `ReceiptLedger` commits `r04.store_binding = SHA256(canonical([identity_id,
   uuid4]))` once in original core_meta/event transaction. Store reopen preserves
   it. Init also persists local HMAC domain/key. **Never export the hash key.**
   Nana supplies an explicitly authorized, host-local metadata-only input with
   exactly platform_scope/event_type_scope/sender_id/conversation_id (no body).
   Do not pass raw IDs on argv or export/commit this input. Run:

   ```sh
   ./onboarding.sh scope --directory /opt/nana_shadow/r042-store --input authorized-id-metadata.json --output scope.json
   ```

   It reuses Store's existing `MetadataSanitizer.scoped_hash` domains (`r04-host`,
   separate sender_id/conversation_id). Only hashed scope goes to stdout/output.
   No ID discovery or reading of AstrBot messages; Nana's independent approved
   metadata collection remains prerequisite. Never guess/reuse other Store hashes.

2. Nana supplies `scope.json`, exact FOUR keys only:
   platform_scope, event_type_scope (actual audited adapter values), sender_hash,
   conversation_hash (64 lowercase hex; no raw IDs, body or attachments).

   ```sh
   ./onboarding.sh prepare --directory /opt/nana_shadow/r042-store --scope scope.json --output request-one
   ```

   Outputs receipt.json (canonical WITHOUT newline), review.json, request.json.
   Unique r04-UUID, exact Store/hash scope, UTC now/expires in <=600 seconds,
   max_uses1, real result-path source, FIRST_REAL_MESSAGE_SHADOW. No authority is
   created. `authorization_digest = SHA256(canonical(receipt except
   review_receipt_digest))`. `review_receipt_digest = SHA256(canonical(review))`.
   No circular hash: initial placeholder is excluded from authorization; final
   receipt includes review digest and has its own receipt_digest.
   Review is schema_version, authorization_digest, store_binding, receipt_id,
   review_provenance. Preparation computes the digest; **independent Nana review
   recomputes it**, validates exact Store/scope/time and checks Sister's approval.

3. After Sister explicitly authorizes exactly that digest, Nana prepares
   `approval.json` with exactly reviewer_origin=NANA_INDEPENDENT_HOST_REVIEW,
   confirmation=INDEPENDENTLY_REVIEWED_EXACT_ONE_SHOT,
   operator_authorization_digest=<exact authorization_digest>,
   host_metadata_evidence_digest=<SHA256 independently collected safe metadata>.
   These assertions must correspond to actual external approval/evidence.

   ```sh
   ./onboarding.sh review-document --preparation request-one --approval approval.json --output /path/to/review-repo/reviews/r042/one.json
   ```

   Output is still UNTRUSTED_SOURCE_REVIEW_DOCUMENT, not authority. Nana reviews
   source bytes and commits that exact file on her independent review branch.
   Only sanitized review JSON is committed; no Store, hash key, raw IDs or body.
   Use full review commit SHA R. Never use a mutable branch name/HEAD as the pin.
   The enclosing document also contains canonical receipt/review; runtime_report
   must be null at this stage. No Python editing required.

4. Authorized developer/operator builds from the independently reviewed commit:

   ```sh
   ./onboarding.sh seal --base /path/to/empty-r042-kit --output /path/to/new-one-shot-candidate --review-repo /path/to/review-repo --review-sha FULL_REVIEW_SHA --review-path reviews/r042/one.json
   ```

   Builder reads only `git show R:reviews/r042/one.json`, validates strict fields,
   canonical bytes, real review provenance, exact approval/digests/time and emits
   ONE_SHOT sealed candidate. No fixture promotion; lifecycle/local/fixture
   provenance rejects. Copies approved55 Core/runtime; modifies only generated
   support seal, sanitized review and manifests. Produces NEW -onboarding.tar.gz,
   filename/bytes/SHA256, manifest review source SHA/path/digest, exact receipt and
   Store digests, seal source hash. Not yet host binding verified.
   Base must EMPTY and contain no data/; existing/sealed destinations reject.
   No network/package deployment happens in the builder.

5. Operator verifies new archive SHA against independent build evidence, uploads
   only that candidate (or builds locally in an independent Shadow directory),
   verifies SHA256SUMS. Preserve original Store/path; never init a new Store now.
   From candidate:

   ```sh
   ./r04.sh receipt create --directory /opt/nana_shadow/r042-store --input receipt.json
   ./r04.sh receipt review --directory /opt/nana_shadow/r042-store --receipt-id EXACT_RID --input review.json
   ./r04.sh receipt verify --directory /opt/nana_shadow/r042-store --receipt-id EXACT_RID
   ./r04.sh receipt arm --directory /opt/nana_shadow/r042-store --receipt-id EXACT_RID
   ./bridge.sh preflight --directory /opt/nana_shadow/r042-store --receipt-id EXACT_RID --client-pid AUDITED_ASTRBOT_PID
   ```

   Stop if review_trusted != true, wrong Store/domain, expiration, UNKNOWN,
   API drift, native/client isolation failure or missing safe metadata. No --force.
   After passing, use R041 foreground bridge start with audited client PID and
   private ipc directory. Nana audits registration; Sister sends exactly ONE
   authorized test event (NOT performed here). One receipt/session/event, then
   stop/collect/unload/registry disappearance/zero-drift. Legacy continues; all
   proposed actions remain SHADOW_BLOCKED. No Grants/budgets/attempts/actions.

## Second independent proof pin / after experiment

Review authorization pin proves permission only; it does NOT prove real EventBus
traversal, hook registration/removal, or host zero side effects. R041 production
worker correctly leaves noncore_zero UNKNOWN. Nana independently collects these
host facts. `REAL_RUNTIME_PROOF_PINS` is separately EMPTY until that review.
Old `proof.py::TRUSTED_NANA_RECEIPTS` is a third, historical A/B/C binding verifier
anchor; it is not used by R04 one_shot_proof/R041 worker. Do NOT populate it to
bypass the R04 message proof or infer lifecycle C == real dispatcher A.

Nana builds a report with exact original receipt/Core linkage plus independently
reviewed noncore_zero all five integer0 fields and binding_evidence_digest of
host evidence. The **full persisted verifier still checks Store/commit/order/
artifacts/identity/scope/dedup/counts**, not report booleans alone.
Prepare second source document with same receipt/review and approval using:

```sh
./onboarding.sh review-document --preparation request-one --approval post-approval.json --runtime-report reviewed-report.json --output /path/to/review-repo/reviews/r042/proof.json
```

Here post-approval's host_metadata_evidence_digest must equal report binding digest.
Commit independently reviewed proof JSON on Nana's source branch. Seal from the
EMPTY base with new output and that full commit/path. New **VERIFY_ONLY** candidate:
- retains exact authorization pin only to validate historical review;
- adds exactly report_digest -> independent_host_evidence_digest proof pin;
- rejects production arm AND consume before dispatch, even if record was ARMED;
- expiration is judged at original consumed_at for proof, not time of late audit;
- fresh manifest/hash/archive, no action-enabled package or new permission.

```sh
./r04.sh observer verify --directory /opt/nana_shadow/r042-store --receipt-id EXACT_RID --input reviewed-report.json
./r04.sh receipt finalize --directory /opt/nana_shadow/r042-store --receipt-id EXACT_RID --input reviewed-report.json
```

Only complete independent pins+persisted proof allow CONSUMED->VERIFIED. Missing
host proof remains UNKNOWN/INCOMPLETE; fixture remains simulated/unverified.
Keep source pins/packages/reviews as historical evidence. Stop/unload worker.
Consumed/VERIFIED/UNKNOWN never re-arm; unconsumed abort -> receipt disarm;
expired is terminal on ledger checks. VERIFY_ONLY permanently disables ingress
in that artifact. Never delete consumption/session journal to reuse. A new
experiment needs NEW receipt/review/pin (and new package), never wildcard authority.
Official backup/replay uses recovery quarantine. Arbitrary privileged full-Store
cloning is outside existing security claims; receipt copied to another initialized
Store is blocked by binding. Do not silently claim protection against root cloning.

## Stop conditions / real states

No actual reviewed source commit/Sister authorization: STOP before seal/arm.
No safe exact scoped hashes or host API evidence: STOP preparation, no body fallback.
Window expired during review/build/upload: new receipt+review+candidate, no date edit.
Hash mismatch: BLOCKED_PACKAGE_INTEGRITY; no bypass. Consumed-but-Core-incomplete:
terminal UNKNOWN, retain evidence; no retry or second session. Report with fixture
trust/provenance, missing noncore evidence or dispatcher proof: cannot real PASS.
No approved host privileges in this task; all commands above are future operations.
Real load NOT_RUN; dispatcher NOT_VERIFIED; host bridge/one-shot NOT_RUN;
host_binding UNVERIFIED; FIRST_REAL_ASTRBOT_SHADOW BLOCKED; E12 NOT_RUN.
