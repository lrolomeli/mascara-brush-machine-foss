#!/usr/bin/env bash
# Arranca el HMI industrial con el venv local.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
    echo "Creando entorno virtual..."
    python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python -m hmi.main "$@"
