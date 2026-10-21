# First-Life One-Shot Closure V1 — live response compatibility checkpoint

Base `0c6bb44580563976b066671a34e3689d386da023`; same existing development branch.
The new ONE_SHOT task supersedes the preceding one-new-call/old-root-proof gate:
up to7 existing unspent slots, one new validation per repair iteration, each with
an explicit tested hypothesis/fix, independent request ID, no retry/fallback.
No new Domain, Foundation re-audit, Subject, Store, Runtime or planner.

## What was actually established

The old response body was deliberately discarded. Existing metadata establishes
HTTP200, JSON content type, parsed outer JSON, a dictionary first choice,
finish_reason=stop, visible deepseek-flash and integer usage6200/469. The missing
message/content representation and exact semantic validation path cannot be
recovered from a SHA256. `old_response_forensics.json` explicitly keeps the old
specific failing field UNKNOWN. A guessed field is not a root-cause finding.

The confirmed diagnostic defect is that multiple parser stages/types were collapsed
into PROVIDER_MALFORMED without a safe failure path. An independent synthetic
fixture reproduces one concrete compatibility defect: all-text content arrays
went directly to json.loads and raised TypeError. This is not a reconstruction of
DeepSeek's old response. A new hypothesis is permitted by the latest task4.1;
no real call has yet been made in this mission.

## Changes and boundary

- Original OpenAIJSONTransport now separates envelope/choice/message/model/usage,
  usable assistant content, semantic JSON and StructuredProposal validation.
  OpenAIMediaTransport inherits the same HTTP/parser lifecycle.
- Optional vendor fields, reasoning_content (never consumed/persisted), missing
  id/object/created, absent/null usage and legacy omitted role are compatible.
  Explicit non-assistant role is rejected. String content and1–16 all-text blocks
  are supported; concatenate text in order, then run exactly the existing strict
  JSON/StructuredProposal validation. No markdown stripping, missing-field repair,
  numeric-string coercion, relaxed enums or permissive semantic extra fields.
- length/tool_calls are recognizable non-complete responses: PARTIAL_OUTPUT,
  never automatic tool invocation/fallback. Refusal remains refusal. Requested vs
  returned model is still checked by original Core correlation; no alias rewrite.
- Typed ResponseDiagnostic captures stage/known validity flags, schema-known path,
  expected category and actual coarse type. Pydantic input/context/message/URLs,
  unknown property names, content, reasoning and headers are excluded. Secret or
  prose in an extra field is represented as `$unknown`, with its type only.
- Original terminal events append bounded diagnostic + sanitized HTTP/usage/native
  response metadata for that exact request ID. Historical rows are not rewritten;
  operational metadata is not Memory, truth, will or authorization. No new table.
- `attempt.py` executes ONE fresh source/INTERPRET per explicit iteration through
  original LifeApplication/CognitionSession/ContextAssembler/World/Concern/C.
  It pins the same restored identity, original configuration and immutable global
  reservations. It never resets budgets or reuses a failed request/old one-shot
  workflow key. Total fixture+remote count remains capped9, reservations400000
  USDmicro, leaving7 remote slots after the prior failed call. UNKNOWN blocks
  preflight, and no attempt is replayed. The iteration's hypothesis is explicit.

## Current external gate

The exact same received Subject remains at
`/workspace/nana-first-life/integration-30m-01/fresh-host`, identity
`37281abf-18c0-4460-b1de-566d3e0734b7`. Read-only checks show two request records
(one fixture/one prior failed remote),50000 USDmicro reservation,42old actions,
zero installed execution Grants, clean foreign keys. No new provider dispatch,
no new Subject/event/writer, no old Grant resurrection. Original24h staging and
old unread bundle are untouched.

The previous credential process/resolver ended. Current managed readiness has no
secret/runtime-variable/outbound-identity binding. Available tools expose readiness
but no vault/FD injection capability. Per task, historical chat keys, environment,
secret files and shell history are not searched. A current explicit host FD or
resolver binding is required before live verification. This is a credential-source
gate, not depleted calls, missing paid authorization, provider outage or a new
Foundation requirement. The same mission can resume at this checkpoint.

## Controlled continuation

With an already inherited safe FD (example FD3; no key in argv/env/config):

```bash
.venv/bin/python -m tools.nana_first_life_live_response.attempt \
  --secret-fd 3 --hypothesis BOUNDED_TEXT_BLOCK_CONTENT_COMPATIBILITY \
  --output /tmp/nana-live-response-attempt-01.json
```

The private-terminal option uses the existing tested echo-disabled input→memory
pipe→ExplicitFDResolver path when explicitly supplied a current credential. It
never reads historical credentials. Do not place a key in a command or chat.
Every iteration is separately reviewed from its safe diagnostic before any next
call; no loop automatically burns the remaining7 slots. A failed/UNKNOWN attempt
remains recorded; no budget refund or alternate provider call.

After actual semantic success, continue this same mission to live chat/restart
qualification using the same Subject; do not claim technical EXPERIENCE_READY
before that. The latest user task defines EXPERIENCE_READY as an immediately
usable technical entry; actual human review is still required for final integration
qualification. At that technical gate stop development and hand off; no Beta,
production/social/device/S10 expansion. Currently human question NOT_SENT,
HumanReview NOT_RUN, integration PARTIAL, EXPERIENCE_READY/qualified/Beta NO.

## Tests and evidence

`tests/live_response` covers canonical/DeepSeek-like/vendor/optional/null/text block,
malformed top-level/choices/message/role/content, duplicate/truncated JSON,
missing semantic fields, enum/numeric misuse, usage, incomplete finish, authority
injection, exact model mismatch and no old diagnostics on UNKNOWN/no replay.
Related suites cover existing provider routing/privacy/budget/fallback, H1 media,
Inspector/Private Intent, current project context and negative-only Manager.
Full repository regression and safe literal scan are recorded in the evidence
folder. Offline fake responses/loopback are not REAL_PROVIDER qualification.

## Final offline checkpoint

Full1388 passed/0failed/12skipped (331.60s wall); related125 passed (12.75s).
Two extra new tests added after collection passed in focused125, without a later
Core delta. First full1387/1fail/12skip retained: only missing temporary old-SQLite
launcher, restored to actual system Python3.13.5/SQLite3.46.1; original isolated
test1pass. No test deletion/version spoof/R045 source modification.

A repeated-topic fixture correctly yields no second Concern after retirement. It
was not changed to force motive generation just to produce a qualification PASS.
No real request, source promotion or human question was performed this mission.
The safe current credential binding gate is still open;7 slots remain unspent.
No credential was read, so current-key exact audit is NOT_APPLICABLE rather than
a fabricated scan. Changed/pending mission files have0 credential-literal matches.

Inherited30min pin remains629d2da/211files; this parser delta has new offline tests,
not a claimed new30min/24h residence. Original staging and bundle are untouched.
