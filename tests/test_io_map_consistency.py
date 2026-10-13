"""Test de consistencia del mapa I/O HMI <-> Modbus <-> PLC.

Verifica que el perfil `generic_kinco.json` no tenga colisiones/duplicados y
que sus registros de paso coincidan con el mapa declarado en
`plc/generic_main.il` (fuente de verdad).

Ejecutar:  python tests/test_io_map_consistency.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE = PROJECT_ROOT / "config" / "plc_profiles" / "generic_kinco.json"
IL = PROJECT_ROOT / "plc" / "generic_main.il"

# Tags distintos que comparten direccion a proposito (alias).
ALIASES = [
    {"Paso_Pinza", "STEP_NUMBER"},
    {"CMD_START", "S5_START"},
    {"CMD_CYCLE_STOP", "S3_STOP"},
    {"MODE_MANUAL", "S_MANUAL"},
    {"MODE_STEP", "S_STEP_BY_STEP"},
    {"SENSOR_1", "S8"},
    {"SENSOR_2", "S23"},
    {"VALVE_1", "CMD_Y1"},
    {"VALVE_2", "CMD_Y3"},
    {"VALVE_3", "CMD_Y6"},
    {"VALVE_4", "CMD_Y7"},
    {"VALVE_5", "CMD_Y8"},
    {"VALVE_6", "CMD_Y9"},
    {"VALVE_7", "CMD_Y10"},
    {"VALVE_8", "CMD_Y11"},
    {"VALVE_9", "CMD_Y12"},
    {"VALVE_10", "CMD_Y14"},
]


def load_raw():
    return json.loads(PROFILE.read_text(encoding="utf-8"),
                      object_pairs_hook=lambda pairs: pairs)


def check_no_duplicate_keys(pairs, path=""):
    seen = Counter(k for k, _ in pairs)
    for k, v in pairs:
        if seen[k] > 1:
            raise AssertionError(f"clave duplicada en JSON: {path}{k}")
        if isinstance(v, list):
            check_no_duplicate_keys(v, path + k + "/")


def is_alias(a: str, b: str) -> bool:
    return any(a in grp and b in grp for grp in ALIASES)


def main() -> int:
    check_no_duplicate_keys(load_raw())
    print("[OK] JSON sin claves duplicadas")

    data = json.loads(PROFILE.read_text(encoding="utf-8"))
    tags = data["tags"]

    # 1. Registros de paso par y en la direccion esperada
    assert tags["Paso_Alambre"]["address"] == 400, "Paso_Alambre != %VW400"
    assert tags["Paso_Pinza"]["address"] == 402, "Paso_Pinza != %VW402"
    assert tags["STEP_NUMBER"]["address"] == 402, "STEP_NUMBER != 402"
    assert tags["MACHINE_STATE"]["address"] == 404, "MACHINE_STATE != 404"
    for name in ("Paso_Alambre", "Paso_Pinza", "STEP_NUMBER", "MACHINE_STATE"):
        addr = tags[name]["address"]
        assert addr % 2 == 0, f"{name} en %VW{addr} impar (Kinco Error 041)"
    print("[OK] registros de paso pares y sin colision")

    # 2. E-stop: fisico en discrete 24, condicion IL en coil 3 (%M0.3)
    assert tags["S1_EMERGENCY_STOP"]["type"] == "discrete_input"
    assert tags["S1_EMERGENCY_STOP"]["address"] == 24
    assert tags["CMD_ESTOP"]["type"] == "coil"
    assert tags["CMD_ESTOP"]["address"] == 3
    print("[OK] E-stop: DI 24 (fisico) + coil 3 (%M0.3)")

    # 3. Sin colisiones dentro de cada espacio Modbus (salvo alias)
    by_type: dict[str, list[tuple[str, int]]] = {}
    for name, info in tags.items():
        by_type.setdefault(info["type"], []).append((name, info["address"]))
    for t, items in by_type.items():
        used: dict[int, list[str]] = {}
        for name, addr in items:
            used.setdefault(addr, []).append(name)
        for addr, names in used.items():
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    if not is_alias(names[i], names[j]):
                        raise AssertionError(
                            f"colision {t} addr {addr}: {names[i]} vs {names[j]}")
    print("[OK] sin colisiones de direccion (salvo alias conocidos)")

    # 4. Coincidencia con el mapa declarado en el IL
    il = IL.read_text(encoding="utf-8")
    m_al = re.search(r"Paso_Alambre=%VW(\d+)", il)
    m_pz = re.search(r"Paso_Pinza=%VW(\d+)", il)
    assert m_al and m_pz, "no se encontro el mapa de pasos en el IL"
    assert int(m_al.group(1)) == tags["Paso_Alambre"]["address"]
    assert int(m_pz.group(1)) == tags["Paso_Pinza"]["address"]
    print(f"[OK] IL coincide: %VW{m_al.group(1)} / %VW{m_pz.group(1)}")

    # 5. IO-PLC.csv alineado con el IL (%I/%Q)
    io = (PROJECT_ROOT / "docs" / "IO-PLC.csv").read_text(encoding="utf-8")
    rows = {r.split(",")[1]: r.split(",")[3] for r in io.splitlines()[1:] if r}
    expected = {"S8": "%I1.0", "S23": "%I2.7", "Y1": "%Q0.0",
                "Y24": "%Q1.6", "M1": "%Q2.0", "H8": "%Q2.3", "H3": "%Q2.4"}
    for name, addr in expected.items():
        assert rows.get(name) == addr, f"IO-PLC.csv {name} != {addr} (es {rows.get(name)})"
    print("[OK] IO-PLC.csv coincide con el mapa %I/%Q del IL")

    print("TEST CONSISTENCIA I/O PASADO CORRECTAMENTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
