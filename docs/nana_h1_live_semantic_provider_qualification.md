# H1-LIVE TianToken qualification — PARTIAL (2026-10-17)

[真实开发relay调用/本地核验] Branch
`dev/nana-core-h1-live-semantic-provider-v1-codex`, base
`c3cd0017d2dd88169a7993905c29ff0844183967`, parent offline anchor
`f6aabc3c8e8712b811540764a3937cc9283861af`. The containing delivery commit records
this experiment; its final SHA is obtained with `git rev-parse HEAD`. This
supersedes the earlier missing-provider blocker only as configuration/readiness.
**PARTIAL_PROVIDER_QUALIFICATION**, not full semantic/provider/H2 readiness.

## Official endpoint and identity

The user confirmed TianToken. Live public `https://api.tiantoken.com/api/status`
provided server_address/api_info `https://api.tiantoken.com` and its Chinese
documentation link `https://tokenmarket.apifox.cn`. Provider-linked documentation
`https://tokenmarket.apifox.cn/502442100e0` explicitly shows
`POST https://api.tiantoken.com/v1/chat/completions` and Bearer Authorization;
`502442067e0` documents chat/image variants. The site currently brands itself
“词元流墟”; the user's relay name was “词元流域”. No credential was sent until
this exact endpoint/host chain was established. Direct Apifox root fetch returned
503; documentation text was read through its indexed official page. No guessed
endpoint, redirects or credential-bearing third-party requests were used.

Base URL: `https://api.tiantoken.com/v1`. Protocol: OpenAI-compatible non-streaming
Chat Completions, JSON-object output and image_url. The returned model exactly
matched requested `qwen3.8-flash` on received inference envelopes. This is
**RELAY_CLAIMED_UNVERIFIED** upstream identity, not proof of official Qwen routing.
No other model selected; no audio/ASR calls. Neither relay nor model is a permanent
default. Network availability and model branding grant no Subject authority.

## Actual calls and qualification scope

The finite cap was12 relay requests, including discovery. Actual9:
1 models GET;1 deterministic text POST (`H1_OK`);6 IMAGE POST;1 VIDEO_VISUAL POST.
MEDIA:3 PROPOSED,1 FAILED strict schema,3 UNKNOWN timeout. The text probe returned
200. One accepted color contrast and two accepted `ORBIT 27` OCR responses were
grounded. The first original-color request, injection image and sampled video
exceeded the existing30s bound; completion/billing remain unknown. Unknown call
keys and sources were not retried. Contrast/OCR repetitions were separately
scheduled qualification cases. The original broad formatting schema was narrowed
to reachable media definitions for later independent fixtures; strict local
CognitionReply/StructuredProposal/MediaSemantics validation was unchanged.

The rejected color response put `confidence_semantics` at the wrong nesting level.
It was not silently repaired into acceptance despite correct visible object words.
The accepted shape response omitted explicit count/right wording: the conservative
lexical rubric credits3/4 features and calls it PARTIAL. OCR matches the single
known string twice, not general OCR accuracy. No accepted video or visual-injection
response exists. Do not label either quality or live-injection defense PASS.
Public generator parameters/digests and exact model labels are in the evidence;
no personal media, capture, external URLs or hidden relationship context were used.

## Wire measurements and billing

The existing OpenAIJSONTransport now records an allowlisted HTTPObservation:
exact request-body SHA256, received raw-response SHA256, status, sanitized native
request/response IDs, UTC times and monotonic latency. Authorization, arbitrary
headers, raw body and credential are never put into the DTO. Completed malformed
responses can still be audited. Timeout measurements carry no invented response
digest. The initial pre-instrumentation image timeout has no completed HTTP trace;
its persistent CognitionRequest/source correlation remains. Raw bodies were
examined only as public qualification responses, not committed; model reasoning
is not committed. Reply/proposal hashes remain distinct from raw HTTP hashes.

The optional measurement field serializes away when absent, preserving existing
persisted reply hashes. New records use the original Record/Artifact mechanism;
schema13/43 tables, no migrations or dependency change. C7/D8 defaults unchanged.
No extra worker, queue, Runtime, Store, SubjectLoop or model authority was created.

Relay usage fields are known only for returned responses. `usage.cost` has no
confirmed unit/currency/settlement meaning here; ACTUAL_COST=UNKNOWN. Official
upstream pricing is not substituted. Unknown calls retain unknown usage/billing.
Ledger reservation10,000 micro-units per media request is an accounting ceiling,
not a guarantee about an unverified relay bill. Output/bytes/calls were bounded;
no balance/account/billing login or purchase occurred.

## Subject, provenance, correction and recovery

Real provider -> accepted MODEL_DERIVATION Memory -> existing WorldModel ->
source-backed local lab review/Concern -> original C SubjectLoop was executed.
The local review policy offers WATCH with no objective. It is explicitly a
synthetic deterministic application review, not an extra live cognition call or a
media model's final judgment. Original C chose WATCH/BACKGROUND_WATCH/NO_ACTION.
Actual Action, Grant, adopted Goal counts remain0. Primary User/relationship/
Manager/privacy/Grant/Budget/Verify semantics and F/G/I implementations unchanged.

Local mutations of an accepted real reply were rejected for wrong correlation,
wrong model and authority-bearing interests. Stale/deleted-source replies were
STALE. A controlled local CALLING record became UNKNOWN without a call; this is
not a live provider SIGKILL experiment. Separate interpreter reopen preserved the
same identity, accepted belief materialization and exactly1 C cycle. Erasure
propagated to derived concern/cycle payload; replay of erased input was rejected,
not reconstructed from an audit. Opaque WATCH/NO_ACTION columns remain queryable.
No provider call occurred in the keyless recovery commands.

One actual integration issue was exposed: independent model replies may change
observation order. The initial lab caller reused an ordinal predicate across
replies, conflating OCR and background atoms at ordinal0. WorldModel correctly
retained CONFLICT. An independent rendered-text/pixel-bound observation superseded
one missing-region interpretation while another distinct alternative remained
CONFLICT; no forced truth winner or false factual OCR-error claim. Future lab
calls now bind request-scoped predicates. Stable cross-call semantic ontology is
not established by model array position. Historical claims were not rewritten.

## Tests and observed transient

Final offline full repository1060 passed/0 failed/1 skipped(E12),151.84s.
The initial full run1059/0/1 was followed by a collector-correlation regression
and a final full run. New wire/collector guards11 PASS; prior combined focused42 PASS. Initial focused
42 PASS. A later focused run had41 PASS/1 FAIL in the existing bounded FFmpeg
sandbox decode (`MEDIA_MALFORMED_OR_UNSUPPORTED`); stderr was not retained by that
existing decoder, so root cause is UNKNOWN. No decoder limit/guard/assertion was
changed. Unchanged isolated life2-case recheck passed, and full focused42 recheck
passed. Both the failed run and successful rechecks are recorded, not suppressed.
Final new-source smoke includes keyless recovery and offline wire/host/privacy
checks. Pytest does not prompt for or read live credentials and never calls relay.

## Reproduction and boundaries

Offline: `.venv/bin/python -m pytest -q tests/h1_live_semantics tests/h1_semantics`.
Full: `.venv/bin/python -m pytest -q tests`.

Only with fresh explicit authorization/finite budget:
`PYTHONPATH=src:. .venv/bin/python -m tools.nana_h1_live_qualification.run --live --directory /tmp/FRESH_PUBLIC_LAB --evidence /tmp/PUBLIC_LAB_EVIDENCE`.
The credential prompt does not echo; no shell-profile/env-file discovery. The
explicit continuation flag allows only remaining unattempted fixtures after an
UNKNOWN stop; unknown fixture/key is never retried. This run's budget is closed.

Keyless reopen: `PYTHONPATH=src:. .venv/bin/python -m tools.nana_h1_live_qualification.recover --directory /tmp/EXISTING_PUBLIC_LAB --evidence /tmp/PUBLIC_LAB_EVIDENCE`.
This lab checker expects this run's labelled contrast/text records and is not a
production recovery command. Managed deletion does not revoke detached public
qualification reports; those are not executable/current memory authority.

No new provider benchmark, Registry/UI, H2, capture, Hands, real social send,
production/main/R045 change, private data or external action. E12 remains NOT_RUN.
Future capability routing is an architecture decision only: separate replaceable
text/reasoning, vision, audio understanding, ASR, TTS, embedding, image generation,
video and future ports, with configured primary/fallback and secret references.
Fallback is never permission to switch the exact model during qualification.

## A–J / next recommendation

A–D remain inherited identity/memory/Subject/runtime foundations. E gained bounded
real transport and actual revisable semantic beliefs; it has not gained general
live cognition or E12 qualification. F/G/I were reused/unchanged; no new live
planning, learner or installation authority was acquired. H gained partial live
image grounding; video/live injection remain UNKNOWN, audio/ASR deferred. H2 is
not yet the next automatic step. J recovery/deletion was reused and exercised
keylessly; no result requires advanced J before a reviewed follow-up H1 session.
Provider selection is no longer the blocker. Address measured protocol/latency
and bounded semantic qualification gaps only under a fresh finite authorization;
do not retry these unknown calls. Final push is independently recorded by the
user-facing `git ls-remote` verification, not assumed by this evidence.

### Collector correlation fix
The lab collector initially selected the last completed envelope metadata on a
new timeout. That was not a CognitionSession reply reuse or belief promotion.
Uncorrelated usage/ID was removed from the UNKNOWN row; the helper now returns
metadata only when the current exchange produced a new response. Its retained
regression passes, as does the final1060/0/1 suite. The billing sum covers five
actually received inference envelopes; unknown usage remains unknown.
Source event/observation timestamps are virtual fixture times; HTTP timestamps
and latencies are actual wall measurements. No real-world sensor event is claimed.
