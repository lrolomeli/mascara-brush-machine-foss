"""Servidor Modbus TCP simulado con logica de actuadores y timers.

Uso: .venv/bin/python tests/run_simulator.py [ip] [puerto] [perfil]
Por defecto: 0.0.0.0:5020 con el perfil generic_kinco.json

Comandos interactivos:
  h3 -> toggle alarma H3 (falta nylon)
  h8 -> toggle alarma H8 (baja presion)
  s  -> mostrar estado actual (pasos, sensores, alarmas)
  q  -> salir

Arquitectura:
  - SimDevice (pymodbus) con action callback para interceptar lecturas Modbus
  - SimulatedPLC mantiene el estado de actuadores y discrete inputs
  - Timer loop actualiza sensores segun actuadores activos
  - El action callback modifica los registros antes de devolver al cliente

Documentacion: docs/maquina_referencia.md seccion 5
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# TIMERS (en segundos) — el ciclo completo dura aproximadamente 6 segundos
# =============================================================================
TIMERS: dict[str, float] = {
    "Y1":  1.0,
    "Y6":  2.5,
    "Y7":  2.0,
    "Y8":  0.5,
    "Y9":  0.5,
    "Y10": 0.5,
    "Y11": 1.0,
    "Y12": 1.0,
    "Y14": 0.5,
    "Y15": 2.5,
    "Y16": 1.5,
    "Y17": 0.3,
    "Y18": 1.0,
    "Y24": 1.5,
    "Y25": 1.5,
    "M1":  2.0,
    "M2":  3.0,
}

# =============================================================================
# MAPA DE ACTUADORES -> SENSORES ASOCIADOS
# =============================================================================
ACTUATOR_CONFIG: dict[str, dict] = {
    "Y1":  {"initial": None, "final": "S9",  "intermediate": None, "returns": False},
    "Y6":  {"initial": "S11", "final": None, "intermediate": None, "returns": True},
    "Y7":  {"initial": None, "final": "S12", "intermediate": None, "returns": True},
    "Y8":  {"initial": None, "final": None,  "intermediate": None, "returns": True},
    "Y9":  {"initial": "S14", "final": "S16", "intermediate": "S10", "returns": False},
    "Y10": {"initial": None, "final": None,  "intermediate": None, "returns": False},
    "Y11": {"initial": "S15", "final": None,  "intermediate": None, "returns": True},
    "Y12": {"initial": "S17", "final": None,  "intermediate": None, "returns": True},
    "Y14": {"initial": None, "final": None,  "intermediate": None, "returns": False},
    "Y15": {"initial": ["S18", "S21"], "final": "S19", "intermediate": None, "returns": True},
    "Y16": {"initial": None, "final": "S20", "intermediate": None, "returns": True},
    "Y17": {"initial": None, "final": None,  "intermediate": None, "returns": True},
    "Y18": {"initial": None, "final": "S22", "intermediate": None, "returns": True},
    "Y24": {"initial": None, "final": None,  "intermediate": None, "returns": False},
    "Y25": {"initial": None, "final": None,  "intermediate": None, "returns": False},
    "M1":  {"initial": None, "final": None,  "intermediate": None, "returns": False},
    "M2":  {"initial": None, "final": None,  "intermediate": None, "returns": False},
    "M3":  {"initial": None, "final": None,  "intermediate": None, "returns": False},
}

# =============================================================================
# SimulatedPLC — Estado de la maquina y logica de sensores
# =============================================================================
class SimulatedPLC:
    def __init__(self, tags: dict):
        self.tags = tags
        self._lock = threading.Lock()

        self._actuator_states: dict[str, bool] = {}
        self._active_timers: dict[str, float] = {}
        self._y9_position: int = 0
        self._y9_moving_up: bool = True
        self._alarm_h3_override: bool | None = None
        self._alarm_h8_override: bool | None = None
        self._discrete_inputs: dict[int, bool] = {}
        self._sensor_addrs: dict[str, int] = {}
        self._coil_addrs: dict[str, int] = {}

        for tag, info in tags.items():
            if info.get("type") == "discrete_input":
                self._sensor_addrs[tag] = info["address"]
            elif info.get("type") == "coil":
                self._coil_addrs[tag] = info["address"]

        self._init_defaults()
        self._timer_thread: threading.Thread | None = None
        self._running = False

    def _addr(self, name: str) -> int | None:
        return self._sensor_addrs.get(name) or self._coil_addrs.get(name)

    def _init_defaults(self):
        for sensor in ("S8", "S14", "S15", "S23"):
            a = self._addr(sensor)
            if a is not None:
                self._discrete_inputs[a] = True

    def start(self):
        self._running = True
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

    def stop(self):
        self._running = False
        if self._timer_thread:
            self._timer_thread.join(timeout=2.0)

    def _timer_loop(self):
        while self._running:
            time.sleep(0.1)
            self._tick(0.1)

    def _tick(self, dt: float):
        expired = []
        with self._lock:
            for timer_key, remaining in list(self._active_timers.items()):
                self._active_timers[timer_key] = remaining - dt
                if self._active_timers[timer_key] <= 0:
                    expired.append(timer_key)
                    del self._active_timers[timer_key]
            for timer_key in expired:
                self._on_timer_expired(timer_key)

    def _on_timer_expired(self, timer_key: str):
        if timer_key == "Y9_pos1":
            self._set_sensor("S14", False)
            self._set_sensor("S10", True)
            self._y9_position = 1
            self._active_timers["Y9_pos2"] = TIMERS["Y9"]
        elif timer_key == "Y9_pos2":
            self._set_sensor("S10", False)
            self._set_sensor("S16", True)
            self._y9_position = 2
        elif timer_key == "Y9_down1":
            self._set_sensor("S16", False)
            self._set_sensor("S10", True)
            self._y9_position = 1
            self._active_timers["Y9_down2"] = TIMERS["Y9"] * 0.6
        elif timer_key == "Y9_down2":
            self._set_sensor("S10", False)
            self._set_sensor("S14", True)
            self._y9_position = 0
        elif timer_key.endswith("_return"):
            actuator = timer_key.replace("_return", "")
            self._return_actuator(actuator)

    def _set_sensor(self, sensor: str, value: bool):
        a = self._addr(sensor)
        if a is not None:
            self._discrete_inputs[a] = value

    def _return_actuator(self, actuator: str):
        config = ACTUATOR_CONFIG.get(actuator, {})
        self._actuator_states[actuator] = False
        if actuator == "Y9":
            return
        initial = config.get("initial")
        if initial:
            if isinstance(initial, list):
                for s in initial:
                    self._set_sensor(s, True)
            else:
                self._set_sensor(initial, True)

    def activate_actuator(self, actuator: str):
        with self._lock:
            if actuator == "M3":
                self._actuator_states[actuator] = True
                return
            self._actuator_states[actuator] = True
            config = ACTUATOR_CONFIG.get(actuator, {})
            initial = config.get("initial")
            returns = config.get("returns", False)
            timer_val = TIMERS.get(actuator)

            if actuator == "Y9":
                self._activate_y9()
            elif initial:
                if isinstance(initial, list):
                    for s in initial:
                        self._set_sensor(s, False)
                else:
                    self._set_sensor(initial, False)
                if returns and timer_val:
                    self._active_timers[f"{actuator}_return"] = timer_val
            else:
                if returns and timer_val:
                    self._active_timers[f"{actuator}_return"] = timer_val

    def _activate_y9(self):
        if self._y9_position == 0:
            self._set_sensor("S14", False)
            self._active_timers["Y9_pos1"] = TIMERS["Y9"]
            self._y9_moving_up = True

    def deactivate_actuator(self, actuator: str):
        with self._lock:
            self._actuator_states[actuator] = False
            if actuator == "M3":
                return
            if actuator == "Y9":
                self._deactivate_y9()
                return
            config = ACTUATOR_CONFIG.get(actuator, {})
            if config.get("returns", False):
                pass

    def _deactivate_y9(self):
        if self._y9_position > 0:
            self._set_sensor("S16", False)
            self._active_timers["Y9_down1"] = TIMERS["Y9"] * 0.6

    def toggle_h3(self):
        with self._lock:
            self._alarm_h3_override = not self._alarm_h3_override if self._alarm_h3_override else True

    def toggle_h8(self):
        with self._lock:
            self._alarm_h8_override = not self._alarm_h8_override if self._alarm_h8_override else True

    def get_status(self) -> str:
        with self._lock:
            activos = [k for k, v in self._actuator_states.items() if v]
            lines = [
                f"  Activos: {', '.join(activos) if activos else 'ninguno'}",
                f"  Timers: {', '.join(f'{k}:{v:.1f}s' for k, v in self._active_timers.items()) or 'ninguno'}",
                f"  Y9 pos: {self._y9_position} (0=abajo, 1=int, 2=arriba)",
                f"  Sensores ON: {', '.join(f'{s}({a})' for s, a in sorted(self._sensor_addrs.items(), key=lambda x: x[1]) if self._discrete_inputs.get(a))}",
                f"  Alarmas: H3={'ON' if self._alarm_h3_override else 'AUTO'} H8={'ON' if self._alarm_h8_override else 'AUTO'}",
            ]
            return "\n".join(lines)

    async def plc_action_callback(self, fc: int, start_addr: int, addr: int,
                                  count: int, registers: list, set_values):
        if fc == 2:  # Read Discrete Inputs
            self._update_di(start_addr, addr, count, registers)
        elif fc == 1:  # Read Coils
            self._update_coils(start_addr, addr, count, registers)
        elif fc == 3:  # Read Holding Registers
            self._update_hr(start_addr, addr, count, registers)
        return None

    def _update_di(self, start_addr: int, addr: int, count: int, registers: list):
        with self._lock:
            s8_addr = self._sensor_addrs.get("S8")
            s23_addr = self._sensor_addrs.get("S23")
            h3_addr = self._sensor_addrs.get("H3")
            h8_addr = self._sensor_addrs.get("H8")

            range_end = addr + 16

            for sensor_addr, value in self._discrete_inputs.items():
                if addr <= sensor_addr < range_end:
                    bit_pos = sensor_addr - start_addr
                    reg_idx = bit_pos // 16
                    bit_idx = bit_pos % 16
                    if value:
                        registers[reg_idx] |= (1 << bit_idx)
                    else:
                        registers[reg_idx] &= ~(1 << bit_idx)

            if h3_addr is not None and addr <= h3_addr < range_end:
                bit_pos = h3_addr - start_addr
                reg_idx = bit_pos // 16
                bit_idx = bit_pos % 16
                if self._alarm_h3_override is not None:
                    if self._alarm_h3_override:
                        registers[reg_idx] |= (1 << bit_idx)
                    else:
                        registers[reg_idx] &= ~(1 << bit_idx)
                elif s8_addr and self._discrete_inputs.get(s8_addr, False):
                    registers[reg_idx] |= (1 << bit_idx)
                else:
                    registers[reg_idx] &= ~(1 << bit_idx)

            if h8_addr is not None and addr <= h8_addr < range_end:
                bit_pos = h8_addr - start_addr
                reg_idx = bit_pos // 16
                bit_idx = bit_pos % 16
                if self._alarm_h8_override is not None:
                    if self._alarm_h8_override:
                        registers[reg_idx] |= (1 << bit_idx)
                    else:
                        registers[reg_idx] &= ~(1 << bit_idx)
                elif s23_addr and not self._discrete_inputs.get(s23_addr, False):
                    registers[reg_idx] |= (1 << bit_idx)
                else:
                    registers[reg_idx] &= ~(1 << bit_idx)

    def _update_coils(self, start_addr: int, addr: int, count: int, registers: list):
        with self._lock:
            range_end = addr + 16
            for tag, a in self._coil_addrs.items():
                if addr <= a < range_end:
                    bit_pos = a - start_addr
                    reg_idx = bit_pos // 16
                    bit_idx = bit_pos % 16
                    base = tag.replace("CMD_", "")
                    if self._actuator_states.get(base, False):
                        registers[reg_idx] |= (1 << bit_idx)
                    else:
                        registers[reg_idx] &= ~(1 << bit_idx)

    def _update_hr(self, start_addr: int, addr: int, count: int, registers: list):
        pass


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
    if not tags:
        print(f"ERROR: No se pudo cargar el perfil '{profile_name}'")
        return 1

    print(f"Perfil cargado: {len(tags)} tags")

    plc = SimulatedPLC(tags)
    plc.start()

    from pymodbus.simulator import SimDevice, SimData, DataType
    from pymodbus.server import StartTcpServer

    device = SimDevice(
        id=1,
        simdata=(
            [SimData(address=0, count=2000, values=False, datatype=DataType.BITS)],
            [SimData(address=0, count=2000, values=False, datatype=DataType.BITS)],
            [SimData(address=0, count=2000, values=0, datatype=DataType.REGISTERS)],
            [SimData(address=0, count=2000, values=0, datatype=DataType.REGISTERS)],
        ),
        action=plc.plc_action_callback,
    )

    print(f"Servidor Modbus TCP simulado en {ip}:{port} (perfil: {profile_name})")
    print("Ejecuta el HMI en otra terminal. Presiona Ctrl+C para detener.")
    print("Comandos: h3=toggle H3, h8=toggle H8, s=status, q=quit")

    try:
        StartTcpServer(context=device, address=(ip, port))
    except KeyboardInterrupt:
        print("\nDeteniendo...")
    finally:
        plc.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
