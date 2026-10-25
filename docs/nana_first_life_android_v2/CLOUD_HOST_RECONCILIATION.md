# Actual cloud inventory reconciliation — received, not deployed

Source: operator-supplied CLOUD_NANA_REAL_HOST_INVENTORY_V2.md, observation window
2026-10-25 10:58–11:05UTC. This developer read the full report; this is not a direct
SSH inspection. Personal platform IDs, private path bindings and original records
are not copied to Git. Original inventory digest is registered separately.

Confirmed by supplied report: Ubuntu24.04.4 x86_64 host, Debian13 AstrBot container,
4vCPU/3.64GiB/2.21GiB available/19GiB disk available. NO_CANONICAL_CORE_ON_HOST.
First formal activation must be one explicit canonical genesis + Legacy Source
Link, not reuse a shadow UUID or claim old Core lineage. Existing AstrBot/QQ and
Iris remain running; no cutover/data import/network change has been authorized.

SQLite3.46.1 container/3.45.1 host remain unsupported for Core. Prefer the already
qualified private CPython3.12.14+SQLite3.51.3+libffi recipe, actual standard sqlite3
binding, with official source hashes and offline wheels. No pysqlite3 substitution,
monkeypatch or LD_PRELOAD shortcut. The developer-host Python binary is NOT a
relocatable Ubuntu artifact: rebuild for the approved host or qualify a matched
Ubuntu build separately. System Python/AstrBot unchanged. Missing bwrap blocks
optional generated Python skills only. New non-root account/service is a pending
production change, never inherit docker.sock, /hostroot or a privileged container.
Target Core RSS<=300MiB; keep Android builds on the separate development host.

Legacy inputs (not read/exported here): Iris L2=1437;L3=308nodes/329edges;L1=199
surviving lines;profiles19user+5group;ledger~20820;decision155; parallel livingmemory
~96.6MiB. These are source estimates at the observation time, not transferred
experiences or validated actions. L1 loss/L2 freshness gaps remain UNKNOWN. Do not
load FAISS as truth; source summaries/profile/favour/action ledger remain claims.
No exporter or restoration has been qualified on private source bytes yet.

Fencing must cover AstrBot agent/active_reply, Iris/livingmemory, proactive_chat,
qzone/poke/qq_tools, nana_life, Bili act pump, enabled SelfEvolution cron and command
control channel. Persistently disable decision/write/send hooks and their restart
paths, not merely kill a PID. Root/dockerd/operator remain trusted host owners.
Core cannot prove fencing by trusting a frontend checkbox. A real, fresh operator
fence report and explicit cutover approval are required before production activation.

Network coordinates must include namespace: host6199=NapCat published port;
AstrBot-container6199=cmdserver;container6299=gate. Existing tailnet root routes to
that old command channel. Recommend NEW loopback127.0.0.1:18765 and separately
approved Tailnet HTTPS listener8443, leaving old route unchanged. This is a proposal,
not a claim the port/Tailscale option/certificate is qualified. Recheck Serve
version/topology/ACL immediately before approved deployment. No Funnel/public port
or insecure TLS bypass. APK's base origin/credential binding must be distinct.

Backup correction: SQLite backup API is individually consistent with WAL readers;
WAL checkpoint alone does not freeze independent writers or give a cross-database
snapshot. A coherent legacy export requires an approved quiescence/cutoff or
explicit per-source snapshot times and gaps. Do not modify private sources during
a read-only dry-run. Do not delete old backups as a rollback shortcut. Rolling
back cannot discard new effects, UNKNOWN, receipts or privacy tombstones.

Production gates still pending: non-root provision/private runtime, legacy private
export/import scope, old-writer fence, canonical activation, provider binding and
budget, new private HTTPS route, real QQ canary, physical phone, release signer,
background push, human review and72h. Supplied metadata unblocks design and tests;
it is not permission to execute these changes.
