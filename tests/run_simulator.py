"""Servidor Modbus TCP simulado de la maquina Ma1, con la rutina del PLC.

Simula el PLC Kinco (rutina Structured Text de ``plc/generic_main.st``) y la
planta fisica (actuadores -> sensores con tiempos de carrera). Permite probar el
HMI completo contra el simulador:

- Ciclo AUTOMATICO real: Paso_Alambre/Paso_Pinza avanzan solos (rutina de dos
  ramas paralelas portada del ST), con multiplexor Auto/Manual.
- Paso a paso: con MODE_STEP activo, cada paso espera el pulso BTN_STEP.
- Forzado manual: con MODE_MANUAL activo, las salidas fisicas siguen CMD_*.
- Alarmas H3/H8, paro de emergencia interactivo y estado en vivo.

Uso: .venv/bin/python tests/run_simulator.py [ip] [puerto] [perfil]
Por defecto: 0.0.0.0:5020 con el perfil generic_kinco.json

Comandos interactivos (especificar la terminal del simulador):
  h3 -> toggle alarma H3 (falta nylon)
  h8 -> toggle alarma H8 (baja presion)
  e  -> toggle paro de emergencia (S1)
  s  -> mostrar estado actual (pasos, actuadores, sensores, alarmas)
  q  -> salir

Rutina portada de ``plc/generic_main.st`` (2 ramas paralelas):
  Rama Alambre  (Paso_Alambre):  0 -> 10 -> 20 -> ... -> 80 -> 0
  Rama Pinza    (Paso_Pinza):    0 -> 10 -> 20 -> ... -> 90 -> 0
  Sincronizacion: la rama alambre espera en 50 a S16 y S20.
  Multiplexor:  Yn = SEL(S_MANUAL, Auto_Yn, CMD_Yn).

Notas sobre tiempos:
  - Los temporizadores TON del ST conservan los PT reales (T_2T5=2.5s ...).
  - Los tiempos de carrera de los actuadores estan ajustados para que el
    handshake fisico produzca los sensores que la rutina espera (p. ej. S18
    llega despues de T_2T5 y S10 despues de T_2T4).
  - El ciclo completo dura aproximadamente 14 segundos.

Documentacion: docs/simulador.md y docs/maquina_referencia.md
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# TIEMPOS DE CARRERA DE LA PLANTA (segundos por actuador)
#   "Y15":  {"fwd": 2.6, "home": 0.8}  -> tiempo distinto por direccion
#   Ajustados para que cada condicion de la rutina sea alcanzable:
#     - Y15 fwd (S18/S21) llega DESPUES de T_2T5 (2.5s)  -> arranca rama pinza
#     - Y9 down (S10) llega DESPUES de T_2T4 (2.0s)      -> M1 se apaga a tiempo
# =============================================================================
TRAVEL: dict[str, float | dict[str, float]] = {
    "Y1": 0.4,
    "Y5": 0.4,
    "Y6": 0.4,
    "Y7": 0.4,
    "Y8": 0.4,
    "Y10": 0.4,
    "Y11": 0.3,
    "Y12": 0.4,
    "Y14": 0.4,
    "Y15": {"fwd": 2.6, "home": 0.3},
    "Y16": 0.1,
    "Y17": 0.4,
    "Y18": 0.2,
    "Y24": 0.4,
}

# =============================================================================
# PLANTA: sensores por posicion de cada actuador
#   "fwd"  : sensores con su valor cuando el actuador esta extendido
#   "home" : sensores con su valor cuando el actuador esta en reposo
#   Los sensores que gobierna un actuador aparecen en AMBAS posiciones (el
#   valor de la posicion contraria se aplica al cambiar de posicion).
#   Y9 (3 posiciones: S14 abajo / S10 intermedio / S16 arriba) se gestiona
#   aparte con su propia maquina de estados.
# =============================================================================
PLANT: dict[str, dict[str, dict[str, bool]]] = {
    "Y1":  {"fwd": {"S9": True},   "home": {"S9": False}},
    "Y5":  {"fwd": {"S15": True},  "home": {}},
    "Y6":  {"fwd": {"S11": False}, "home": {"S11": True}},
    "Y7":  {"fwd": {"S12": True,  "S13": False}, "home": {"S12": False, "S13": True}},
    "Y8":  {"fwd": {}, "home": {}},
    "Y10": {"fwd": {}, "home": {}},
    "Y11": {"fwd": {"S15": False}, "home": {"S15": True}},
    "Y12": {"fwd": {"S17": True},  "home": {"S17": False}},
    "Y14": {"fwd": {}, "home": {}},
    "Y15": {"fwd": {"S18": True, "S19": False, "S21": True},
            "home": {"S18": False, "S19": True, "S21": False}},
    "Y16": {"fwd": {"S20": True},  "home": {"S20": False}},
    "Y17": {"fwd": {}, "home": {}},
    "Y18": {"fwd": {"S22": True},  "home": {"S22": False}},
    "Y24": {"fwd": {}, "home": {}},
    "M1":  {"fwd": {}, "home": {}},
    "M2":  {"fwd": {}, "home": {}},
    "M3":  {"fwd": {}, "home": {}},
}

# Tiempos de la pinza Y9 (3 posiciones). La bajada pasa por S10 (posicion
# intermedia) DESPUES de T_2T4 para respetar el apagado de M1 en el ST.
Y9_UP_MID: float = 0.5
Y9_UP_END: float = 1.0
Y9_DOWN_MID: float = 2.2
Y9_DOWN_END: float = 2.8

# =============================================================================
# TEMPORIZADORES TON DE LA RUTINA (PT reales del ST) -> (PT segundos, condicion IN)
# =============================================================================
ST_TIMERS: dict[str, tuple[float, object]] = {
    "T_2T5": (2.5, lambda a, p: a == 10),
    "T_1T3": (1.5, lambda a, p: p == 10),
    "T_2T4": (2.0, lambda a, p: p == 30),
    "T_1T1": (3.0, lambda a, p: p == 40),
    "T_1T5": (1.5, lambda a, p: a == 70),
    # NOTA: el ST de produccion gatea T_2T7 con Paso_Pinza=60 pero lo consume
    # en el paso 70; al salir de 60 el TON se reinicia y Q queda FALSO -> cuelga.
    # En el simulador se gatea en el paso que lo espera (70), como T_2T6.
    "T_2T7": (2.0, lambda a, p: p == 70),
    "T_2T6": (1.5, lambda a, p: p == 80),
}

def _load_tags(profile_name: str) -> dict:
    path = PROJECT_ROOT / "config" / "plc_profiles" / f"{profile_name}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("tags", {})


class SimulatedPLC:
    """Planta fisica + rutina del PLC (port de plc/generic_main.st)."""

    def __init__(self, tags: dict):
        self.tags = tags
        self._lock = threading.RLock()

        # Mapeos por tipo de tag
        self._sensor_addrs: dict[str, int] = {}
        self._coil_addrs: dict[str, int] = {}
        self._hr_addrs: dict[str, int] = {}
        self._ir_addrs: dict[str, int] = {}
        for tag, info in tags.items():
            t = info.get("type")
            a = info["address"]
            if t == "discrete_input":
                self._sensor_addrs[tag] = a
            elif t == "coil":
                self._coil_addrs[tag] = a
            elif t == "holding_register":
                self._hr_addrs[tag] = a
            elif t == "input_register":
                self._ir_addrs[tag] = a

        # Salidas fisicas = coils Y*/M* (excluye CMD_*, MODE_*, etc.)
        self._phys_names: list[str] = [
            t for t in self._coil_addrs if re.fullmatch(r"(?:Y|M)\d+", t)
        ]
        self._phys_addrs: set[int] = {self._coil_addrs[t] for t in self._phys_names}
        self._cmd_addr: dict[str, int] = {}
        for name in self._phys_names:
            cmd = f"CMD_{name}"
            if cmd in self._coil_addrs:
                self._cmd_addr[name] = self._coil_addrs[cmd]

        # Estado de la planta
        self._discrete: dict[int, bool] = {}
        self._active_timers: dict[str, float] = {}
        self._act_pos: dict[str, str] = {}
        self._y9_position: int = 0
        self._y9_busy: bool = False
        self._alarm_h3_override: bool | None = None
        self._alarm_h8_override: bool | None = None

        # Estado del HMI (escrituras recibidas por Modbus)
        self._coil_written: dict[int, bool] = {}
        self._coil_values: dict[int, bool] = {}
        self._reg_written: dict[int, int] = {}
        self._reg_values: dict[int, int] = {}

        # Estado de la rutina PLC
        self._paso_alambre: int = 0
        self._paso_pinza: int = 0
        self._auto: dict[str, bool] = {}
        self._phys: dict[str, bool] = {}
        self._ton: dict[str, float] = {}
        self._btn_mem: bool = False
        self._start_mem: bool = False
        self._start_latch: bool = False

        self._init_defaults()
        self._timer_thread: threading.Thread | None = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Inicializacion
    # ------------------------------------------------------------------
    def _init_defaults(self):
        for name in self._phys_names:
            self._act_pos[name] = "home"
            self._auto[name] = False
            self._phys[name] = False
        for name in ST_TIMERS:
            self._ton[name] = 0.0

        # Sensores en reposo
        for sensor in ("S8", "S23"):
            a = self._sensor_addrs.get(sensor)
            if a is not None:
                self._discrete[a] = True
        # Y9 abajo (home), Y7 abajo, Y6 arriba, Y11/Y15 retraidos
        self._apply_pos_now("Y7", "home")
        self._apply_pos_now("Y6", "home")
        self._apply_pos_now("Y11", "home")
        self._apply_pos_now("Y15", "home")
        self._set_sensor("S14", True)  # pinza abajo (Y9 en 0)
        self._set_sensor("S16", False)
        # E-Stop fisico NC: lecturas ON = no pulsado
        estop = self._sensor_addrs.get("S1_EMERGENCY_STOP")
        if estop is not None:
            self._discrete[estop] = True

    def _apply_pos_now(self, actuator: str, pos: str):
        cfg = PLANT.get(actuator, {})
        for sensor, value in cfg.get(pos, {}).items():
            self._set_sensor(sensor, value)

    # ------------------------------------------------------------------
    # Acceso a sensores / coils
    # ------------------------------------------------------------------
    def _sensor(self, name: str) -> bool:
        a = self._sensor_addrs.get(name)
        return self._discrete.get(a, False) if a is not None else False

    def _set_sensor(self, name: str, value: bool):
        a = self._sensor_addrs.get(name)
        if a is not None:
            self._discrete[a] = value

    def _coil_by_addr(self, addr: int) -> bool:
        return self._coil_values.get(addr, False)

    # ------------------------------------------------------------------
    # Hilo de simulacion
    # ------------------------------------------------------------------
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
        with self._lock:
            self._process_timers(dt)
            self._plc_scan(dt)

    # ------------------------------------------------------------------
    # Planta fisica: timers y movimientos
    # ------------------------------------------------------------------
    def _process_timers(self, dt: float):
        expired = []
        for key, remaining in list(self._active_timers.items()):
            nxt = remaining - dt
            if nxt <= 0:
                expired.append(key)
                del self._active_timers[key]
            else:
                self._active_timers[key] = nxt
        for key in expired:
            self._on_timer_expired(key)

    def _on_timer_expired(self, key: str):
        if key == "Y9_up_mid":
            self._set_sensor("S10", True)
            self._y9_position = 1
            self._active_timers["Y9_up_end"] = Y9_UP_END - Y9_UP_MID
        elif key == "Y9_up_end":
            self._set_sensor("S10", False)
            self._set_sensor("S16", True)
            self._y9_position = 2
            self._y9_busy = False
        elif key == "Y9_down_mid":
            self._set_sensor("S10", True)
            self._y9_position = 1
            self._active_timers["Y9_down_end"] = Y9_DOWN_END - Y9_DOWN_MID
        elif key == "Y9_down_end":
            self._set_sensor("S10", False)
            self._set_sensor("S14", True)
            self._y9_position = 0
            self._y9_busy = False
        elif key.startswith("MOVE:"):
            _, actuator, sensor, value = key.split(":")
            self._set_sensor(sensor, value == "1")

    def _command_actuator(self, actuator: str, commanded: bool):
        """Mueve la planta hacia la posicion ordenada por el multiplexor."""
        if actuator == "Y9":
            if commanded:
                self._activate_y9()
            else:
                self._deactivate_y9()
            return
        target = "fwd" if commanded else "home"
        if self._act_pos.get(actuator) == target:
            return
        self._act_pos[actuator] = target

        for k in list(self._active_timers):
            if k.startswith(f"MOVE:{actuator}:"):
                del self._active_timers[k]

        travel = TRAVEL.get(actuator, 0.4)
        if isinstance(travel, (int, float)):
            travel = {"fwd": travel, "home": travel}
        delay = travel.get(target, 0.4)
        cfg = PLANT.get(actuator, {})
        for sensor, value in cfg.get(target, {}).items():
            self._active_timers[f"MOVE:{actuator}:{sensor}:{'1' if value else '0'}"] = delay

    def _activate_y9(self):
        if self._y9_busy or self._y9_position != 0:
            return False
        self._set_sensor("S14", False)
        self._set_sensor("S10", False)
        self._set_sensor("S16", False)
        self._active_timers["Y9_up_mid"] = Y9_UP_MID
        self._y9_busy = True
        return True

    def _deactivate_y9(self):
        if self._y9_busy or self._y9_position <= 0:
            return False
        self._set_sensor("S16", False)
        self._active_timers["Y9_down_mid"] = Y9_DOWN_MID
        self._y9_busy = True
        return True

    # ------------------------------------------------------------------
    # Rutina del PLC (port de plc/generic_main.st)
    # ------------------------------------------------------------------
    def _plc_scan(self, dt: float):
        # --- Entradas (ultima escritura del HMI) ---
        estop = self._sensor("S1_EMERGENCY_STOP")
        start = self._coil_written.get(0, False)      # CMD_START / S5_START
        stop = self._coil_written.get(1, False)       # CMD_CYCLE_STOP / S3_STOP
        pause = self._coil_written.get(2, False)      # CMD_PAUSE (RESET)
        manual = self._coil_written.get(5, False)     # MODE_MANUAL / S_MANUAL
        step_mode = self._coil_written.get(6, False)  # MODE_STEP / S_STEP_BY_STEP
        continuous = self._coil_written.get(8, False) # S4_CONTINUOUS
        btn = self._coil_written.get(20, False)       # BTN_STEP

        # Flanco de avance manual
        trig = btn and not self._btn_mem
        self._btn_mem = btn

        # Pulso de arranque (Boton INICIO del HMI) -> latch
        if start and not self._start_mem and self._paso_alambre == 0 and self._paso_pinza == 0:
            self._start_latch = True
        self._start_mem = start

        # --- Reset general (ST): estop / stop / manual ---
        if (not estop) or stop or manual or pause:
            self._paso_alambre = 0
            self._paso_pinza = 0
            self._start_latch = False

        # --- Subproceso Orientador (ST: fuera del bloque automatico) ---
        self._auto["Y1"] = self._sensor("S14") and not self._sensor("S9")

        if not manual:
            pa = self._paso_alambre
            pp = self._paso_pinza
            gate = (not step_mode) or trig

            # ==================== RAMA ALAMBRE ====================
            if pa == 0:
                if self._start_latch and self._sensor("S14"):
                    if not continuous:
                        self._start_latch = False
                    self._paso_alambre = 10
            elif pa == 10:
                self._auto["Y15"] = True
                self._auto["Y14"] = True
                self._auto["Y9"] = True
                if self._sensor("S18") and gate:
                    self._paso_alambre = 20
            elif pa == 20:
                self._auto["Y17"] = True
                if self._sensor("S21") and gate:
                    self._paso_alambre = 30
            elif pa == 30:
                self._auto["Y17"] = False
                self._auto["Y15"] = False
                if self._sensor("S19") and gate:
                    self._paso_alambre = 40
            elif pa == 40:
                self._auto["Y18"] = True
                if self._sensor("S22") and gate:
                    self._paso_alambre = 50
            elif pa == 50:
                self._auto["Y16"] = True
                if self._sensor("S20") and self._sensor("S16") and gate:
                    self._paso_alambre = 60
            elif pa == 60:
                self._auto["Y18"] = False
                self._auto["Y12"] = True
                if self._sensor("S17") and gate:
                    self._paso_alambre = 70
            elif pa == 70:
                self._auto["Y14"] = False
                self._auto["Y10"] = True
                self._auto["Y16"] = False
                if self._ton["T_1T5"] >= ST_TIMERS["T_1T5"][0] and gate:
                    self._paso_alambre = 80
            elif pa == 80:
                self._auto["Y12"] = False
                # Al fin del ciclo se retrae Y9: si no, queda latcheado TRUE del
                # paso 10 y S14 (home) nunca vuelve -> el reinicio en continuo
                # (y la re-iniciacion en ciclo simple) se cuelga.
                self._auto["Y9"] = False
                self._paso_alambre = 0
                if continuous:
                    self._start_latch = True  # ciclo continuo

            # ==================== RAMA PINZA ====================
            if pp == 0:
                if self._paso_alambre >= 10 and self._ton["T_2T5"] >= ST_TIMERS["T_2T5"][0]:
                    self._paso_pinza = 10
            elif pp == 10:
                self._auto["Y3"] = True
                self._auto["Y10"] = False
                if self._ton["T_1T3"] >= ST_TIMERS["T_1T3"][0] and gate:
                    self._paso_pinza = 20
            elif pp == 20:
                self._auto["Y11"] = False
                self._auto["Y12"] = False
                if self._sensor("S15") and gate:
                    self._paso_pinza = 30
            elif pp == 30:
                self._auto["M1"] = True
                self._auto["Y9"] = False
                if self._ton["T_2T4"] >= ST_TIMERS["T_2T4"][0]:
                    self._auto["M1"] = False
                if self._sensor("S10") and gate:
                    self._paso_pinza = 40
            elif pp == 40:
                self._auto["M2"] = True
                self._auto["Y6"] = True
                self._auto["Y11"] = True
                self._auto["Y24"] = False
                if self._ton["T_1T1"] >= ST_TIMERS["T_1T1"][0] and gate:
                    self._paso_pinza = 50
            elif pp == 50:
                self._auto["M2"] = False
                self._auto["Y6"] = False
                if self._sensor("S11") and gate:
                    self._paso_pinza = 60
            elif pp == 60:
                self._auto["Y7"] = True
                if self._sensor("S12") and gate:
                    self._paso_pinza = 70
            elif pp == 70:
                self._auto["Y8"] = True
                if self._ton["T_2T7"] >= ST_TIMERS["T_2T7"][0] and gate:
                    self._paso_pinza = 80
            elif pp == 80:
                self._auto["Y8"] = False
                if self._ton["T_2T6"] >= ST_TIMERS["T_2T6"][0] and gate:
                    self._paso_pinza = 90
            elif pp == 90:
                self._auto["Y7"] = False
                self._auto["Y24"] = True
                if self._sensor("S13") and gate:
                    self._auto["Y3"] = False
                    self._auto["Y24"] = False
                    self._paso_pinza = 0  # FIN DE CICLO

        # --- TON de la rutina ---
        for name, (pt, cond) in ST_TIMERS.items():
            if cond(self._paso_alambre, self._paso_pinza):
                self._ton[name] += dt
            else:
                self._ton[name] = 0.0

        # --- Multiplexor SEL(S_MANUAL, Auto_*, CMD_*) ---
        for name in self._phys_names:
            if manual:
                addr = self._cmd_addr.get(name)
                value = self._coil_written.get(addr, False) if addr is not None else False
            else:
                value = bool(self._auto.get(name, False))
            self._phys[name] = value
            self._command_actuator(name, value)

        # Botones momentaneos (INICIO/STOP/RESET/STEP): se consumen
        for addr in (0, 1, 2, 20):
            self._coil_written.pop(addr, None)

        # --- Overlay para lecturas Modbus ---
        self._coil_values = dict(self._coil_written)
        self._coil_values[0] = self._start_latch
        self._coil_values[20] = False
        for name in self._phys_names:
            self._coil_values[self._coil_addrs[name]] = self._phys.get(name, False)

        self._reg_values = dict(self._reg_written)
        pa_addr = self._hr_addrs.get("Paso_Alambre")
        pp_addr = self._hr_addrs.get("Paso_Pinza")
        ms_addr = self._hr_addrs.get("MACHINE_STATE")
        if pa_addr is not None:
            self._reg_values[pa_addr] = self._paso_alambre
        if pp_addr is not None:
            self._reg_values[pp_addr] = self._paso_pinza
        if ms_addr is not None:
            self._reg_values[ms_addr] = 1 if (self._paso_alambre or self._paso_pinza) else 0

    # ------------------------------------------------------------------
    # Alarmas y estado
    # ------------------------------------------------------------------
    def toggle_h3(self):
        with self._lock:
            self._alarm_h3_override = not self._alarm_h3_override if self._alarm_h3_override else True

    def toggle_h8(self):
        with self._lock:
            self._alarm_h8_override = not self._alarm_h8_override if self._alarm_h8_override else True

    def toggle_estop(self):
        with self._lock:
            estop = self._sensor_addrs.get("S1_EMERGENCY_STOP")
            if estop is not None:
                self._discrete[estop] = not self._discrete.get(estop, True)

    def get_estop(self) -> bool:
        with self._lock:
            return self._sensor("S1_EMERGENCY_STOP")

    def get_status(self) -> str:
        with self._lock:
            activos = [k for k, v in self._phys.items() if v]
            sensores = ", ".join(
                f"{s}({a})" for s, a in sorted(self._sensor_addrs.items(), key=lambda x: x[1])
                if self._discrete.get(a)
            )
            return "\n".join([
                f"  Pasos: Alambre={self._paso_alambre} Pinza={self._paso_pinza}",
                f"  Modo: {'MANUAL' if self._coil_by_addr(5) else 'AUTO'}"
                f"{' + PASO' if self._coil_by_addr(6) else ''}"
                f"{' + CONTINUO' if self._coil_by_addr(8) else ''}",
                f"  E-Stop: {'LIBRE' if self._sensor('S1_EMERGENCY_STOP') else 'PULSADO'}",
                f"  Activos: {', '.join(activos) if activos else 'ninguno'}",
                f"  Timers: {', '.join(f'{k}:{v:.1f}s' for k, v in self._active_timers.items()) or 'ninguno'}",
                f"  Y9 pos: {self._y9_position} (0=abajo, 1=int, 2=arriba)",
                f"  Sensores ON: {sensores or 'ninguno'}",
                f"  Alarmas: H3={'ON' if self._alarm_h3_override else 'AUTO'} H8={'ON' if self._alarm_h8_override else 'AUTO'}",
            ])

    # ------------------------------------------------------------------
    # Callback de Modbus (lecturas y escrituras de la HMI)
    # ------------------------------------------------------------------
    async def plc_action_callback(self, fc: int, start_addr: int, addr: int,
                                  count: int, registers: list, set_values):
        if fc == 2:  # Read Discrete Inputs
            with self._lock:
                self._update_di(start_addr, addr, count, registers)
        elif fc == 1:  # Read Coils
            with self._lock:
                self._update_coils(start_addr, addr, count, registers)
        elif fc == 3:  # Read Holding Registers
            with self._lock:
                self._update_hr(start_addr, addr, count, registers)
        elif fc in (5, 15):  # Write single/multiple coils
            with self._lock:
                if set_values is None:  # confirmacion de pymodbus (no escribir)
                    return None
                values = set_values if isinstance(set_values, list) else [set_values]
                if fc == 5:
                    self._coil_written[addr] = bool(values[0])
                else:
                    for i, v in enumerate(values):
                        self._coil_written[addr + i] = bool(v)
        elif fc in (6, 16):  # Write single/multiple registers
            with self._lock:
                if set_values is None:  # confirmacion de pymodbus (no escribir)
                    return None
                values = set_values if isinstance(set_values, list) else [set_values]
                if fc == 6:
                    self._reg_written[addr] = values[0]
                else:
                    for i, v in enumerate(values):
                        self._reg_written[addr + i] = v
        return None

    @staticmethod
    def _set_bit(registers: list, address: int, start_addr: int, value: bool):
        reg_idx = (address - start_addr) // 16
        bit_idx = address % 16
        if 0 <= reg_idx < len(registers):
            if value:
                registers[reg_idx] |= (1 << bit_idx)
            else:
                registers[reg_idx] &= ~(1 << bit_idx)

    def _update_di(self, start_addr: int, addr: int, count: int, registers: list):
        s8_addr = self._sensor_addrs.get("S8")
        s23_addr = self._sensor_addrs.get("S23")
        h3_addr = self._sensor_addrs.get("H3")
        h8_addr = self._sensor_addrs.get("H8")

        for sensor_addr, value in self._discrete.items():
            self._set_bit(registers, sensor_addr, start_addr, value)

        if h3_addr is not None:
            if self._alarm_h3_override is not None:
                value = self._alarm_h3_override
            else:
                value = bool(s8_addr and self._discrete.get(s8_addr, False))
            self._set_bit(registers, h3_addr, start_addr, value)

        if h8_addr is not None:
            if self._alarm_h8_override is not None:
                value = self._alarm_h8_override
            else:
                value = bool(s23_addr and not self._discrete.get(s23_addr, False))
            self._set_bit(registers, h8_addr, start_addr, value)

    def _update_coils(self, start_addr: int, addr: int, count: int, registers: list):
        for coil_addr, value in self._coil_values.items():
            self._set_bit(registers, coil_addr, start_addr, value)

    def _update_hr(self, start_addr: int, addr: int, count: int, registers: list):
        range_end = addr + count
        for reg_addr, value in self._reg_values.items():
            if addr <= reg_addr < range_end:
                registers[reg_addr - start_addr] = value


def load_tags(profile_name: str) -> dict:
    return _load_tags(profile_name)


# =============================================================================
# Interfaz interactiva
# =============================================================================
def _stdin_loop(plc: SimulatedPLC):
    for line in sys.stdin:
        cmd = line.strip().lower()
        if cmd == "h3":
            plc.toggle_h3()
        elif cmd == "h8":
            plc.toggle_h8()
        elif cmd == "e":
            plc.toggle_estop()
            print(f"  E-Stop: {'LIBRE' if plc.get_estop() else 'PULSADO'}")
        elif cmd == "s":
            print(plc.get_status())
        elif cmd == "q":
            print("\nDeteniendo...")
            plc.stop()
            os._exit(0)


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

    thread = threading.Thread(target=_stdin_loop, args=(plc,), daemon=True)
    thread.start()

    print(f"Servidor Modbus TCP simulado en {ip}:{port} (perfil: {profile_name})")
    print("Simula la rutina de plc/generic_main.st (AUTO, paso a paso, manual).")
    print("Ejecuta el HMI en otra terminal. Presiona Ctrl+C o 'q' para detener.")
    print("Comandos: e=estop, h3=toggle H3, h8=toggle H8, s=status, q=quit")

    try:
        StartTcpServer(context=device, address=(ip, port))
    except KeyboardInterrupt:
        print("\nDeteniendo...")
    finally:
        plc.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())