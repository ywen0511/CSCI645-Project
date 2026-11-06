#!/usr/bin/env bash
# CPU-queue job: resolve and write the frozen v2 protocol + environment lock in the dev checkout.
set -euo pipefail
. $(dirname $0)/common.sh
export HOME=${TMPDIR:-/tmp}/c645_freezehome; mkdir -p $HOME
export PYTHONPATH=$DEV/src OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y
cd $DEV
require_clean $DEV
$PY scripts/freeze_v2.py --protocol configs/v2/protocol.json --output configs/v2/frozen --freeze-utc "$1"
$KZ/envs/csci645proj/bin/pip freeze > configs/v2/frozen/pip-freeze.txt
cmp -s configs/v2/frozen/pip-freeze.txt configs/frozen/pip-freeze.txt && echo "environment lock identical to v1" || diff configs/frozen/pip-freeze.txt configs/v2/frozen/pip-freeze.txt | head -20
ls -la configs/v2/frozen
echo FREEZE_V2_DONE
