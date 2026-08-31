"""Test de integracion del PLCAdapter contra un servidor Modbus TCP simulado."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pymodbus.server import StartTcpServer  # noqa: E402
from pymodbus.datastore import (  # noqa: E402
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)

from hmi.comms.plc_adapter import ModbusTCPAdapter, PLCProfile  # noqa: E402


def make_block(val=0, n=500):
    return ModbusSequentialDataBlock(1, [val] * n)


def main() -> int:
    store = ModbusDeviceContext(di=make_block(), co=make_block(),
                                hr=make_block(), ir=make_block())
    ctx = ModbusServerContext(devices={1: store})

    t = threading.Thread(
        target=lambda: StartTcpServer(ctx, address=("127.0.0.1", 15022)),
        daemon=True,
    )
    t.start()
    time.sleep(0.6)

    profile_path = PROJECT_ROOT / "config" / "plc_profiles" / "generic_kinco.json"
    prof = PLCProfile.from_json(profile_path)
    print(f"Perfil: {prof.name} ({len(prof.tags)} tags)")

    ad = ModbusTCPAdapter(prof, host="127.0.0.1", port=15022, unit_id=1, timeout=2)
    assert ad.connect(), "No se pudo conectar"
    print("[OK] Conexion establecida")

    tests = [
        ("S5_START", True),
        ("CMD_Y3", True),
        ("CMD_M1", True),
        ("BTN_STEP", False),
    ]
    for name, val in tests:
        assert ad.write_tag(name, val), f"write fallo: {name}"
        got = ad.read_tag(name)
        assert got == val, f"{name}: esperado {val}, obtenido {got}"
        print(f"[OK] write/read {name} = {got}")

    time.sleep(0.2)
    data = ad.read_all_inputs()
    assert data["S5_START"] is True
    assert data["CMD_Y3"] is True
    assert data["CMD_M1"] is True
    print(f"[OK] read_all_inputs: {len(data)} tags")

    ad.disconnect()
    print("TEST PASADO CORRECTAMENTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
