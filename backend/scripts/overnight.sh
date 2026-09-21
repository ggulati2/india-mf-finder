#!/bin/bash
# Full AMFI rebuild + independent verification. Run from backend/. Log path is the first argument.
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH=.
PY=${PY:-/private/tmp/mf-venv/bin/python}
echo "== rebuild started $(date)"
$PY -u scripts/rebuild_from_amfi.py 2>&1 | grep --line-buffered -v -E "INFO|sqlalchemy"
echo "== rebuild exit ${PIPESTATUS[0]} at $(date)"
echo "== verify (NAV vs AMFI single-day reports)"
$PY -u scripts/verify_data.py 2>&1 | grep -v INFO
echo "== ALL DONE $(date)"
