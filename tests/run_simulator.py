"""Servidor Modbus TCP simulado para pruebas sin PLC fisico.

Uso: .venv/bin/python tests/run_simulator.py [ip] [puerto] [perfil]
Por defecto: 0.0.0.0:5020 con el perfil generic_kinco.json

Nota: No ejecuta la logica ST de la maquina; solo responde a las direcciones
del perfil para validar la comunicacion HMI <-> PLC y mostrar sensores/
pasos de ejemplo en la interfaz.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_block(val=0, n=2000):
    return ModbusSequentialDataBlock(1, [val] * n)


def load_tags(profile_name: str) -> dict:
    path = PROJECT_ROOT / "config" / "plc_profiles" / f"{profile_name}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("tags", {})


def main() -> int:
    ip = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5020
    profile_name = sys.argv[3] if len(sys.argv) > 3 else "generic_kinco"

    tags = load_tags(profile_name)
    co = [0] * 2000
    di = [0] * 2000
    hr = [0] * 2000
    ir = [0] * 2000

    def addr(tag: str) -> int | None:
        t = tags.get(tag)
        return t["address"] if t else None

    # Sensores de demostracion (Discrete Inputs) - activar algunos
    for tag in ("S8", "S14", "S15", "S23"):
        a = addr(tag)
        if a is not None:
            di[a] = 1

    # Coils de comando leidos por el HMI -> mostrar algunas salidas activas
    for tag in ("Y14", "Y24", "M1"):
        a = addr(tag)
        if a is not None:
            co[a] = 1

    # Pasos de la secuencia en Holding Registers
    a_alambre = addr("Paso_Alambre")
    a_pinza = addr("Paso_Pinza")
    if a_alambre is not None:
        hr[a_alambre] = 3
    if a_pinza is not None:
        hr[a_pinza] = 40

    # Estado de maquina
    a_state = addr("MACHINE_STATE")
    if a_state is not None:
        hr[a_state] = 1  # Automatico

    co_block = ModbusSequentialDataBlock(1, co)
    di_block = ModbusSequentialDataBlock(1, di)
    hr_block = ModbusSequentialDataBlock(1, hr)
    ir_block = ModbusSequentialDataBlock(1, ir)

    store = ModbusDeviceContext(di=di_block, co=co_block, hr=hr_block, ir=ir_block)
    ctx = ModbusServerContext(devices={1: store})

    print(f"Servidor Modbus TCP simulado en {ip}:{port} (perfil: {profile_name})")
    print("Sensores ON de demo: S8, S14, S15, S23 | Salidas de demo: Y14, Y24, M1")
    print("Presiona Ctrl+C para detener.")
    try:
        StartTcpServer(ctx, address=(ip, port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
