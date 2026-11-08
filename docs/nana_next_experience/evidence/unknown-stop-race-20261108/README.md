# Release-stop pending-work race

User relayed cloud operator report: b257a09 isolated install and synthetic gate checks passed, one historical terminal UNKNOWN and zero reported active PREPARED/CALLING/RESERVED. This is user-relayed, not independently verified.

Original change_release checked pending work before stop only; the old owner could commit a new pending attempt before it stopped. Manual start also failed to reject an active pending gate when automatic=False. Source 8e7d2ad checks again after stop before selecting release and rejects manual starts with pending work. 27 targeted supervisor/dialogue/UNKNOWN tests pass, including adversarial synthetic late-pending injection; no live Store or real provider used. The prior b257a09 candidate does not contain this fix; no new host-qualified package or production upgrade readiness is claimed.

This fix does not implement financial/provider reconciliation or a safe owner-fenced way to classify stale PREPARED/CALLING/RESERVED after a crash. Avoid direct SQL, auto retry, invented terminal state, or refunds. The existing original Runtime queue.recover and CognitionSession.recover need analysis under an exclusive owner lease, host authorization, audit and process/epoch fencing, and compatibility with both new and old Supervisor versions. Cloud operator can prepare its rollback plan in parallel; no production changes authorized.
