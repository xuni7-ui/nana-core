# Existing Operator: qualified interpreter / flag correction

The observed private `_ssl` in this image loads Debian13 `/lib/x86_64-linux-gnu/libssl.so.3`
and `libcrypto.so.3` (OpenSSL3.5.7). Moving only the Python prefix to Ubuntu does
not supply those libraries. `operator_check.py` routes the existing checking
script through Core's pinned container/.venv interpreter. It neither patches
Ubuntu's SSL nor edits the original SDK seals. See actual operator-abi.json.

Minimal existing Operator integration (its real source was not provided here):
replace only the `genesis.dryrun` interpreter/argument invocation with this
adapter. Preserve existing authorization and exact original script/approval/plan.
Use the shipped tool, pinned image/source from release.json, explicit narrow
read-only root and the SHA256 of the ORIGINAL checker reviewed by the operator:

```
python3 tools/operator_check.py --image <image_id> --source <core_commit> \
  --mode abi
python3 tools/operator_check.py --image <image_id> --source <core_commit> \
  --mode dry-run --read-root /srv/nana-core \
  --script /srv/nana-core/operator/ACTUAL_ORIGINAL_SCRIPT.py \
  --script-sha256 <original_script_sha256> -- <original plan/home/approval args>
```

These are integration parameters, not a claim that that script path already
exists. The final deployment installer provides fixed artifact paths; use the
actual cloud script and preserve its arguments. `container_check.py` must be
readable by UID999; normal Git/installation0644 is sufficient. Private input
permissions must already allow the selected numeric user; do not add root caps
or copy a private DB to make the test work. Entire supplied roots are mounted
read-only at their SAME absolute paths; no empty `/opt/...` host bind is added.

The minimal flag fix is `normalize_args(original_args, "dry-run")`: remove only
`--dry-run` and `--verify-only` tokens, append exactly `--dry-run`. For verify-only,
append that mode instead. Effect mode flags and ambiguous boolean assignments
are refused. The original checker remains the checker; its output and exit code
are forwarded unchanged. No new thirteen-item checker is invented.

Actual evidence: corrected container ABI, synthetic mutually exclusive parser
receiving only dry-run, and an attempted fixture write rejected by the readonly
mount. Original cloud checker13/13 remains NOT_RUN until its actual script and
report are available. The original canonical plan digest and C-only approval are
unchanged, and these tools contain no create/activate command.
