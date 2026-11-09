# CI bwrap host requalification — 2026-11-09

The exact original `IsolatedSkillRunner().qualify()` source probe returned `AVAILABLE` on this development host with all 11 original checks true; this is local source evidence, not GitHub runner or production qualification.

The scoped GitHub run after the container preflight change returned `bwrap: Can't mount proc on /proc: Operation not permitted`. It stopped before the full suite and produced no Core candidate. The Debian Actions job container added an outer namespace boundary that prevents the required original bwrap probe; no probe assertion was relaxed.

The workflow now runs that same probe on the disposable GitHub Ubuntu runner host. The legacy SQLite 3.46.1 fixture remains a separate Debian Trixie container, network-disabled, read-only except tmpfs `/tmp`, with the checkout mounted read-only. A runtime version assertion remains in both fixture build and invocation. The exact-source full pytest, matching double build/offline install, and Web inbox browser case will run only after the original probe reports every check passing. This workflow edit has no GitHub result yet.

No production service, Store, CURRENT selector, APK, real model, account, or device was changed or used.


Follow-up GitHub run 42718410546 confirmed the Debian SQLite fixture built and its exact 3.46.1 invocation passed, and the client job passed. Core stopped in the subsequent host preparation at `git config --system`: the Ubuntu runner user had no permission for `/etc/gitconfig`. The bwrap probe and full suite did not run; no candidate was made. The workflow now uses `sudo git config --system` for that runner-local safe.directory entry. This correction is committed separately; its real probe result remains pending.


Second follow-up run 42718858552 confirmed runner setup, dependency preparation, supported Core interpreter SQLite 3.53.1, and the separate legacy 3.46.1 fixture. The unchanged original probe then returned `UNAVAILABLE/BWRAP_NAMESPACE_OR_RUNTIME_DENIED` with exact stderr `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`; pytest did not start and no candidate was generated. Client job was still running when recorded. This matches Ubuntu 24.04's unprivileged-user-namespace AppArmor restriction. The next workflow revision adds a disposable-runner-only AppArmor profile attached specifically to `/usr/bin/bwrap`, granting only `userns,`; it preserves AppArmor and the exact original probe. Existing bwrap attachments cause an explicit fail rather than replacement. No result from that targeted profile has been observed yet.


Run 42719453260 proved the narrow profile works: the unchanged probe returned `AVAILABLE` with all 11 checks true, then the exact full pytest ran 691.98s. Result: 2150 passed, 1 failed, 1 setup error, 12 skipped; client job passed. GitHub JUnit artifact 13720761008 is retained. No candidate was built. The setup error `OLD_SQLITE_FIXTURE_REQUIRES_3_46_1` came from the old-host container not seeing pytest's script under `/tmp/nq`; the next workflow mounts that host temp directory read-only. The source failure under Ubuntu runner GnuPG 2.4.4 was the B1 packet verifier requiring only the old encrypted-data marker. The verifier now accepts the explicit AEAD payload marker while requiring a public-key session and rejecting symmetric-key session packets. Focused actual GPG roundtrip plus packet matrix passed locally under GnuPG 2.4.7; it still needs the complete CI rerun against 2.4.4.
