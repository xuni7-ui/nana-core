#!/bin/sh
set -eu
NANA_BUNDLE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec "$NANA_BUNDLE_ROOT/nana" start "$@"
