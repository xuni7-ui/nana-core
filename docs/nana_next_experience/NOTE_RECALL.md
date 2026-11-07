# S2 sourced note recall — same Next Experience / ten-domain task

407 already delivers consented note save/correction, independent UNKNOWN reconciliation and matching APK/Web/Core. This server refinement closes a measured gap: the saved note was absent from both conversation phases (memory-notes/note-recall-baseline.json). It does not change the client protocol or require another APK.407 remains the published client.

## Actual path

Existing INTERPRET → optional bounded lookup hints → original MemoryService → existing ContextAssembler → original C's committed decision and existing RENDER. No extra model call. Hints are proposals, not facts or permission. They are consumed once in the current owner memory, bounded to64 pending entries, removed before the original persisted proposal is committed, and cleared on close/restart. Empty hints preserve the old canonical dialogue serialization. No hidden transcript/query cache is persisted.

Original MemoryService literal_notes materializes scope/entity/privacy/current note headers before reading text; only explicitly consented user-note SEMANTIC/STATEMENT sources participate. At most8 terms/4 notes; default100ms independent SQL bound, no query inside a write transaction. Interrupted lookup resets its progress handler and returns an omission marker; absence is not presumed. The existing Store and erasure graph remain authoritative. No new table/index/Store/loop/learner/affect system. This is literal source selection, not FAISS/semantic retrieval.

Notes retain explicit user-statement/non-lived-event/no-authority annotations. Identity, established Person-Self and sourced language policy precede optional recall. Oversized notes are omitted within the existing context budget rather than removing Person-Self or making ordinary chat fail. Correction/withdrawal prevents reuse of old context and old answers.

A private-capable provider does not authorize a PROJECT interaction to send PERSONAL data. Conversation context, required refs, current-goal metadata and world snapshot are now capped to the actual dialogue classification. Authorized PERSONAL interaction remains usable. This is destination/data separation; it does not remove internal motives, goals, interests, private thinking or execution grants. Verified project-work facts are filtered before PUBLIC rendering, allowing normal public chat to continue without leaking them.

## Measured evidence

Final related116 passed55.58s: actual loopback Core/Memory routing, Person-Self, project status, privacy, note authorization/UNKNOWN, model configuration swap and context boundaries. Additional inherited original S8 renewal/concern/H1 checks12 passed5.15s. Last focused7 passed6.11s includes PUBLIC chat after real owned project work. No model self-rating or new hidden authority. Initial fixture-CAS, privacy ceiling and optional-note priority failures are retained, with fixes preserving source/no-retry/privacy assertions.

English and Chinese cases persist a note, restart the same DEV identity, switch fixture model configuration, retrieve the current corrected source and remove it without reviving the old source. Unretained query canary never appears in Store artifacts. PERSONAL negative and positive cases both pass. A260-newer-note case still retrieves the old source; forced real SQLite interruption leaves the Store usable. Four large optional notes keep Person-Self and the original context limit. These prove source selection and wiring; fixture-generated wording is not real model understanding or human recall.

Synthetic original-Store scale checkpoints1000/10000/100000/200000: the old general lexical128-candidate list misses a retained CJK substring note, while the new literal lookup returns exactly the one permitted source in9/9 timing repetitions per scale, excluding another entity's same text. There is **one distinct query fixture per scale**, not9 independent semantic cases. P50/P95ms:0.35/1.95;2.28/2.64;20.31/22.79;43.31/45.74. No timeout or wrong source in those samples. These are query latency, not whole-chat speedups; outer SQL comparison labels in the raw scale log refer to a historical aggregate-join sketch. No actual provider/token/cost savings are inferred.

Scale used the post-e888 worktree with the same literal algorithm; formatting only the two new memory functions was AST-equal. Fingerprints explicitly distinguish post-format bytes. Final same-input1001 smoke captures exact executed source hashes and produces its final snapshot. It also fixes the old reproducer silently omitting nonstandard final counts when CLI args were overwritten by filter parameters. The initial consent mismatch was correctly refused by Core and fixed in the synthetic fixture, not by weakening consent.

Reproduce: qualified Python with explicit source PYTHONPATH, fresh private **synthetic** scratch, `python -m tools.nana_next_experience.memory_scale_compare --root <fresh-synthetic-dir> --count 200000 --note-recall`. Reserve sufficient temporary disk; never put production Subject data in tmpfs. No provider or private data is used.

## Remaining real gates and S8 continuity

Real provider semantic selection, human naturalness, physical phone, real cloud SDK, live authoritative DB/vector mapping and cross-day memory quality are NOT_RUN. Provider-reported tokens and billing remain distinct from UTF8 context estimates and local wire bytes; full model-specific wire budgeting remains open. No production/legacy migration update or new fee.

This is a developer S2/S5 repair, not Nana self-learning. Original S8 autonomous gap/practice/independent evaluation/transfer/reuse/counterexample/S3 need evidence from6f2a491 is preserved and regression checked. Real retrieval-error feedback must enter that same verified Experience/G chain; raw query misses alone cannot be labelled failures or force learning. Continue the existing S8/S3/S2 and product task after this patch, without inventing a second learner or declaring the whole mission complete.
