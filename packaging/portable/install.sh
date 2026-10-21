#!/bin/sh
set -eu
NANA_BUNDLE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec "${1:-python3}" "$NANA_BUNDLE_ROOT/bootstrap.py" install
