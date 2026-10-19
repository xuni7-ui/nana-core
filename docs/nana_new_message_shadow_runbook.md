# New-message shadow — development integration and next permission

Current executable adapter: `continuity.dialogue_shadow.NewMessageShadow` (import
from bridge module). It uses the existing Runtime, entity/scope binding and original
SubjectLoop, never a second companion brain. No AstrBot/QQ client is installed or
contacted. No changes to R045 observer, production plugin or Iris.

## Anonymous development rehearsal

```bash
.venv/bin/python -m tools.nana_real_life.shadow_review \
  --root /tmp/shadow-review-fresh --output /tmp/shadow-review.json
```

The reviewed JSON shows inferred/applied intent, C judgment/intention, response draft
or silence, reason and local latency. Raw anonymous text stays in interpreter RAM;
C receives minimal normalized development meaning. Explicit topic refusal persists
only through existing source/Memory deletion paths. No raw excerpt capture-all.
`ShadowBinding.enabled` defaults false. Binding mismatches, stale input, unsupported
privacy and bounds reject before semantic interpretation.32 reviews/session maximum.
Duplicate event review is not delivery; restart rejects re-review instead of silently
creating another judgment. Application should serialize review calls and give D a
reactive safe point; a queued review without a committed cycle returns a pending
error, never a fabricated completion.

Local literal baseline recognizes a few explicit phrases; ambiguous/quoted/conflicting
cues clarify. Interpretation is not authoritative intent. It cannot grant capability,
create relationship facts or certify its own HUMAN_REVIEW. Model-backed interpretation
must later use existing configured ModelPort/ContextAssembler privacy/cost contracts;
no raw-provider bypass is authorized or implemented here. No quality claim from an
input-label fixture. Current cases are manually supplied anonymous examples; no
actual user's preferred tone or blinded human quality has been measured.

## Host-facing contract

Host application owns ShadowBinding(subject_id,entity_id,scope,host_binding_id,
accepted_after_us,expires_at_us,max_age_us,enabled,source_mode). It pushes NewExcerpt
for a **new** event only. Bridge has no pull/history method and no external send.
Provider/relationship/user text cannot change the binding. A Primary User role
confers no host read/write authority. Current live mode explicitly rejects with
BLOCKED_BY_EXPLICIT_AUTHORIZATION_AND_HOST_QUALIFICATION. Do not mislabel live
QQ input as anonymous synthetic input to get around this gate.

## One next authorization, not granted by this document

Approve a specified **development** AstrBot/QQ host/controller, exact subject/person/
conversation binding, at most10 newly arriving user-owned messages over30 minutes,
revocable at once; no history fetching, group expansion, raw body persistence,
Iris access, production takeover, sends or paid calls. Raw body can be processed
only in memory by the approved local interpreter; review output is shown only to
that user. Host must stop forwarding on consent revocation, expiry, scope mismatch
or queue overload and discard transient excerpts.

After explicit consent: implement/qualify host's actual push hook and authenticated
new-event binding; add an appropriately constrained non-synthetic metadata admission
path before enabling live mode; verify minimal privacy-filtered meaning and explicit
boundary retention/deletion; then observe the bounded sample and ask for voluntary
human fit feedback. Existing constructor must keep denying LIVE until that work is
qualified. This is one scoped permission/integration milestone, not permission to
use real credentials, capture devices or send any response. Output remains shadow
only. A user-visible pilot needs its own later send/rollback authorization.
