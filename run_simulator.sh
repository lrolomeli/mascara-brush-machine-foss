#!/usr/bin/env bash
# Inicia un servidor Modbus TCP simulado en localhost:5020
# Utiles para probar la HMI sin PLC fisico: .venv/bin/python tests/run_simulator.py
set -e
cd "$(dirname "$0")"
exec .venv/bin/python tests/run_simulator.py "$@"
