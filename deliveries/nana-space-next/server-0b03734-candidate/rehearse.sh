set -eu
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm
probe=$1
slot=$2
work=$3
report=$4
fallback=${5:?Usage: rehearse.sh PROBES SLOT WORK REPORT FALLBACK_SLOT}
mkdir -p "$report"
"$slot/.venv/bin/python" -I -B "$probe/installed_gateway_probe.py" --bundle "$slot" --work "$work" --output "$report/gateway.json" --check-memory-notes > "$report/gateway.txt"
"$slot/.venv/bin/python" -I -B "$probe/integrated_setup_probe.py" --bundle "$slot" --work "$work" --gateway "$report/gateway.json" --output "$report/setup.json" > "$report/setup.txt"
"$slot/.venv/bin/python" -I -B "$probe/installed_note_recall_probe.py" --bundle "$slot" --work "$work" --continue-gateway-result "$report/gateway.json" --output "$report/growth.json" --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage > "$report/growth.txt"
"$slot/.venv/bin/python" -I -B "$probe/installed_living_memory_probe.py" --bundle "$slot" --work "$work" --prior "$report/growth.json" --output "$report/living.json" > "$report/living.txt"
for phase in before fallback return; do
    active="$slot"
    if [ "$phase" = fallback ]; then active="$fallback"; fi
    "$active/.venv/bin/python" -I -B "$probe/continuity-reader.py" --bundle "$active" --work "$work" --gateway "$report/gateway.json" --setup "$report/setup.json" --output "$report/reader-$phase.json" > "$report/reader-$phase.txt"
done
"$slot/.venv/bin/python" -I -B - "$report" "$slot" "$fallback" <<'PY'
from pathlib import Path
import sys,json
d,slot,fallback=map(Path,sys.argv[1:])
read=lambda p:json.loads(p.read_text())
snapshots=[read(d/f'reader-{x}.json') for x in ('before','fallback','return')]
for row in snapshots:row.pop('clock_us')
assert snapshots[0]==snapshots[1]==snapshots[2]
proof={'source':read(slot/'runtime.json')['source_commit'],'fallback':read(fallback/'runtime.json')['source_commit'],
      'same_stopped_dev':True,'counts':snapshots[0]['counts'],'real_provider_calls':0}
(d/'integrated.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
PY
