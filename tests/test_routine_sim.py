"""Test de la rutina de la maquina en el simulador (sin Qt ni servidor).

Gobierna directamente el SimulatedPLC de tests/run_simulator.py: escribe coils
como lo haria la HMI y avanza el tiempo con _tick(), validando que la rutina
portada de plc/generic_main.st ejecuta el ciclo completo sin colgarse.

Casos:
  1. Forzado manual (MODE_MANUAL + CMD_*)
  2. Ciclo AUTOMATICO completo (dos ramas paralelas) sin modo paso a paso
  3. Modo paso a paso: avanza solo con pulso BTN_STEP
  4. Paro de emergencia resetea ambos pasos
  5. Modo continuo (S4_CONTINUOUS) reinicia el ciclo sin nuevo START
  6. Lectura por Modbus: coils, discrete inputs y holding registers

Uso: .venv/bin/python tests/test_routine_sim.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.run_simulator import SimulatedPLC, load_tags  # noqa: E402

LOOP = asyncio.new_event_loop()


class Harness:
    """Wrapper sincrono alrededor del SimulatedPLC."""

    def __init__(self, plc: SimulatedPLC):
        self.plc = plc

    def write_coil(self, name: str, value: bool):
        tag = self.plc.tags[name]
        LOOP.run_until_complete(
            self.plc.plc_action_callback(5, 0, tag["address"], 1, [], [bool(value)])
        )

    def write_hr(self, name: str, value: int):
        tag = self.plc.tags[name]
        LOOP.run_until_complete(
            self.plc.plc_action_callback(6, 0, tag["address"], 1, [], [value])
        )

    def run(self, seconds: float, dt: float = 0.1):
        n = int(round(seconds / dt))
        for _ in range(n):
            self.plc._tick(dt)

    @property
    def pa(self) -> int:
        return self.plc._paso_alambre

    @property
    def pp(self) -> int:
        return self.plc._paso_pinza

    def coil(self, name: str) -> bool:
        tag = self.plc.tags[name]
        return self.plc._coil_values.get(tag["address"], False)

    def sensor(self, name: str) -> bool:
        return self.plc._sensor(name)

    def phys(self, name: str) -> bool:
        return self.plc._phys.get(name, False)

    def read_coil_bit(self, addr: int) -> bool:
        registers = [0] * (2000 // 16)
        LOOP.run_until_complete(self.plc.plc_action_callback(1, 0, addr, 1, registers, None))
        return bool((registers[addr // 16] >> (addr % 16)) & 1)

    def read_di_bit(self, addr: int) -> bool:
        registers = [0] * (2000 // 16)
        LOOP.run_until_complete(self.plc.plc_action_callback(2, 0, addr, 1, registers, None))
        return bool((registers[addr // 16] >> (addr % 16)) & 1)

    def read_hr_val(self, addr: int) -> int:
        registers = [0] * 2000
        LOOP.run_until_complete(self.plc.plc_action_callback(3, 0, addr, 1, registers, None))
        return registers[addr]


def fresh() -> Harness:
    return Harness(SimulatedPLC(load_tags("generic_kinco")))


def test_manual_force():
    h = fresh()
    h.run(0.3)
    h.write_coil("MODE_MANUAL", True)
    h.run(0.3)
    assert h.coil("MODE_MANUAL") is True, "MODE_MANUAL debe reflejarse en la lectura"
    h.write_coil("CMD_Y6", True)
    h.run(1.0)
    assert h.phys("Y6") is True, "Y6 debe activarse en manual con CMD_Y6"
    assert h.sensor("S11") is False, "Y6 fuera de home apaga S11"
    h.write_coil("CMD_Y6", False)
    h.run(1.0)
    assert h.sensor("S11") is True, "Y6 en home enciende S11"
    print("[OK] forzado manual: CMD_Y6 activa Y6 y desconecta S11")


def test_auto_cycle():
    h = fresh()
    h.write_coil("MODE_MANUAL", False)
    h.write_coil("MODE_STEP", False)
    h.run(0.3)
    h.write_coil("CMD_START", True)  # pulso de inicio
    h.run(0.5)
    assert h.coil("CMD_START") is False, "CMD_START debe consumirse (pulso)"
    assert h.pa == 10, f"inicio de rama alambre esperado 10, got {h.pa}"

    steps_seen: set[str] = {f"pa{h.pa}", f"pp{h.pp}"}
    finished = False
    total = 0.0
    while total < 30.0 and not finished:
        h.run(0.1)
        total += 0.1
        steps_seen.add(f"pa{h.pa}")
        steps_seen.add(f"pp{h.pp}")
        if h.pp >= 90:
            finished = True

    assert finished, f"el ciclo no termino en 30s. pasos vistos: {sorted(steps_seen)}"
    h.run(3.0)  # deja cerrar los pasos 80/90 -> 0
    assert h.pa == 0, f"Paso_Alambre debe quedar en 0, got {h.pa}"
    assert h.pp == 0, f"Paso_Pinza debe quedar en 0, got {h.pp}"
    assert "pa10" in steps_seen and "pa80" in steps_seen
    assert "pp40" in steps_seen and "pp90" in steps_seen
    print(f"[OK] ciclo AUTO completo en {total:.1f}s ({len(steps_seen)} pasos vistos)")


def test_step_by_step():
    h = fresh()
    h.write_coil("MODE_MANUAL", False)
    h.write_coil("MODE_STEP", True)
    h.write_coil("CMD_START", True)
    h.run(0.5)
    assert h.pa == 10, f"arranque libre a 10 esperado, got {h.pa}"

    # S18 llega a los ~2.6s; sin BTN_STEP no debe avanzar
    h.run(5.0)
    assert h.pa == 10, f"sin BTN_STEP no debe avanzar, got {h.pa}"

    # pulso de paso siguiente -> 20
    h.write_coil("BTN_STEP", True)
    h.run(0.3)
    assert h.pa == 20, f"BTN_STEP debe avanzar a 20, got {h.pa}"
    print("[OK] modo paso a paso: avanza solo con BTN_STEP")


def test_estop_reset():
    h = fresh()
    h.write_coil("MODE_MANUAL", False)
    h.write_coil("CMD_START", True)
    h.run(4.0)
    assert h.pa > 0 or h.pp > 0, "la maquina debe estar en ciclo"
    h.plc.toggle_estop()
    h.run(0.3)
    assert h.pa == 0 and h.pp == 0, "E-Stop debe resetear ambos pasos"
    h.plc.toggle_estop()  # liberar
    print("[OK] paro de emergencia resetea la secuencia")


def test_continuous():
    h = fresh()
    h.write_coil("MODE_MANUAL", False)
    h.write_coil("MODE_STEP", False)
    h.write_coil("S4_CONTINUOUS", True)
    h.write_coil("CMD_START", True)
    h.run(16.0)
    # La rama alambre debe haber vuelto a arrancar al menos 2 veces
    h.write_coil("CMD_START", False)
    h.run(0.2)
    assert h.pa > 0, "con S4_CONTINUOUS el ciclo debe reiniciarse solo"
    print("[OK] modo continuo: reinicia el ciclo sin nuevo START")


def test_read_path():
    h = fresh()
    h.write_coil("MODE_MANUAL", True)
    h.run(0.3)
    assert h.read_coil_bit(5) is True, "lectura de coil 5 (MODE_MANUAL)"
    h.write_coil("CMD_START", True)
    h.write_coil("CMD_CYCLE_STOP", True)  # apagar cualquier avanzada
    h.run(0.3)
    assert h.read_di_bit(14) is True, "lectura de discrete 14 (S14 home)"
    assert h.read_di_bit(24) is True, "lectura de discrete 24 (E-Stop libre)"
    h.plc.toggle_estop()
    h.run(0.3)
    assert h.read_di_bit(24) is False, "E-Stop pulsado lee False"
    h.plc.toggle_estop()
    h.write_coil("MODE_MANUAL", False)
    h.write_coil("CMD_START", True)
    h.run(1.0)
    assert h.read_hr_val(400) == 10, f"Paso_Alambre HR=400 esperado 10, got {h.read_hr_val(400)}"
    assert h.read_hr_val(402) in (0, 10), f"Paso_Pinza HR=402 inesperado {h.read_hr_val(402)}"
    print("[OK] lectura Modbus: coils, discrete inputs y holding registers")


def main() -> int:
    cases = [
        ("Forzado manual", test_manual_force),
        ("Ciclo automatico", test_auto_cycle),
        ("Paso a paso", test_step_by_step),
        ("E-Stop", test_estop_reset),
        ("Continuo", test_continuous),
        ("Lectura Modbus", test_read_path),
    ]
    for name, fn in cases:
        print(f"--- {name} ---")
        fn()
    print("TEST RUTINA SIMULADOR PASADO CORRECTAMENTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())