#!/usr/bin/env bash

set -e

SCRIPT_PATH=$(readlink -f $0)
SCRIPT_DIR=${SCRIPT_PATH%/*}
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

[ -d .venv ] || python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
"$VENV_DIR/bin/pip" install -r requirements.txt
ln -sv "$SCRIPT_DIR/lazysar" /usr/local/bin/
