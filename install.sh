#!/usr/bin/env bash

SCRIPT_PATH=$(readlink -f $0)
SCRIPT_DIR=${SCRIPT_PATH%/*}
cd "$SCRIPT_DIR"

[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
for script in lazysar lazysar-client lazysar-cmd lazysar-panel; do
    ln -sv "$SCRIPT_DIR/$script" /usr/local/bin/
done
