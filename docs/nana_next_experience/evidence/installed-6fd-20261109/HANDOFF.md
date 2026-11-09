# Candidate verification and stopped DEV continuity commands

Source6fd8ed544d5b0a195d159b6f9c75a5b36b022d5c. These paths name actual tested local artifacts; future CI artifacts have their own source/hash metadata and must not borrow this hash. Download not yet qualified at this checkpoint. CURRENT remains266+409.

```sh
# An absent private runtime slot; no Subject init or start occurs.
python3.12 -I nana-unpack.py nana-first-life-portable-v1.tar.gz   --sha256 99f869aceeb4b5210ff76089199f54556fa7c761d73fab87131a7fb78407901e   --destination /absolute/private/runtime/nana-6fd8ed5
python3.12 -I /absolute/private/runtime/nana-6fd8ed5/bootstrap.py install
/absolute/private/runtime/nana-6fd8ed5/nana preflight --home /absolute/existing/stopped/private/home
```

The preflight command checks the existing portable-CLI profile; it can correctly refuse a gateway/BFF home. The actual gateway-DEV home above is not a qualified direct portable-CLI profile (both old/new CLI refuse its adapter/provider-file checks). Use the original gateway supervisor contract rather than rewriting that home to bypass it.

Actual isolated DEV tests reused original external probes (installed Python-I-B, no repo PYTHONPATH):

```sh
/workspace/scratch/nana-causal6fd-installed/.venv/bin/python -I -B   /workspace/scratch/nana-installed-probes/verify-note-recall.py   --bundle /workspace/scratch/nana-causal6fd-installed --work /tmp/n6fdinstalled   --output /workspace/scratch/nana6fd-installed-result.json   --check-wire-reservations --check-retrieval-growth --check-streaming --check-scope32 --report-usage
/workspace/scratch/nana-causal6fd-installed/.venv/bin/python -I -B   /workspace/scratch/nana-installed-probes/verify-delivery.py   --expected-source 6fd8ed544d5b0a195d159b6f9c75a5b36b022d5c   --bundle /workspace/scratch/nana-causal6fd-installed --work /tmp/n6fddelivery   --output /workspace/scratch/nana6fd-installed-delivery-result.json
/workspace/scratch/nana-causal6fd-installed/.venv/bin/python -I -B   /workspace/scratch/nana-installed-probes/verify-binary-rollback.py   --bundle /workspace/scratch/nana-causal6fd-installed   --previous-bundle /workspace/scratch/nana-delivery008-installed   --work /tmp/n6fdinstalled --prior /workspace/scratch/nana6fd-installed-result.json   --output /workspace/scratch/nana6fd-dev-rollback-result.json
```

These are original observed invocations, not idempotent rerun instructions: fresh-probe paths/results must be absent; preserve completed homes/results and use a fresh explicitly owned DEV case. Rollback probe accepts only the bound stopped DEV marker and attaches old/new binaries sequentially; it never restores a DB or imports private history. Production upgrade remains stop→quarantined backup→independent install/check→qualified host registry/CAS config rebind if needed→same stopped home preflight→start/health, per packaging/portable/docs/MIGRATION.md. No stale DB or retired lineage may be reactivated; old008 binary does not acquire the new long-history/guidance/interest behavior. Source-lineage and actual production host activation are not inferred from these commands.
