#!/usr/bin/env python3
"""Prueba del servo (pulsos + direccion + enable) contra un Kinco real.

Usa el perfil `config/plc_profiles/test_kinco.json` (programa `plc/test_servo.il`).

Ejemplos:
  # Descubrir mapeo Modbus de Q/M/V (usando los marcadores del programa)
  python tests/test_servo_hardware.py --ip 192.168.0.252 --scan

  # Estado actual (entradas, posicion, salidas)
  python tests/test_servo_hardware.py --ip 192.168.0.252 --status

  # Secuencia: enable -> home -> mover a 20000 pulsos
  python tests/test_servo_hardware.py --ip 192.168.0.252 --enable on
  python tests/test_servo_hardware.py --ip 192.168.0.252 --home
  python tests/test_servo_hardware.py --ip 192.168.0.252 --move 20000

  # Jog (mantener) y parar
  python tests/test_servo_hardware.py --ip 192.168.0.252 --jog fwd --watch 3
  python tests/test_servo_hardware.py --ip 192.168.0.252 --stop
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from hmi.comms.plc_adapter import ModbusTCPAdapter, PLCProfile  # noqa: E402

PROFILE = PROJECT_ROOT / "config" / "plc_profiles" / "test_kinco.json"

# Marcadores puestos por plc/test_servo.il
M_PATTERN = [0, 2, 4]      # bits %M1.0/%M1.2/%M1.4 = 1
V_MARKER = 4660            # %VW200 = 0x1234


def split_dint(value: int) -> tuple[int, int]:
    v = value & 0xFFFFFFFF
    return v & 0xFFFF, (v >> 16) & 0xFFFF


def join_dint(lo: int, hi: int) -> int:
    v = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return v - 0x100000000 if v & 0x80000000 else v


def read_coils(ad: ModbusTCPAdapter, start: int, count: int) -> list[bool]:
    try:
        r = ad._client.read_coils(start, count=count, device_id=ad._unit_id)
        return [bool(b) for b in r.bits[:count]] if not r.isError() else []
    except Exception as e:
        print(f"  [AVISO] lectura de coils fallo: {e}")
        return []


def read_discrete(ad: ModbusTCPAdapter, start: int, count: int) -> list[bool]:
    try:
        r = ad._client.read_discrete_inputs(start, count=count, device_id=ad._unit_id)
        return [bool(b) for b in r.bits[:count]] if not r.isError() else []
    except Exception as e:
        print(f"  [AVISO] lectura de discrete fallo: {e}")
        return []


def read_holding(ad: ModbusTCPAdapter, start: int, count: int) -> list[int]:
    out: list[int] = []
    try:
        while len(out) < count:
            n = min(125, count - len(out))
            r = ad._client.read_holding_registers(start + len(out), count=n,
                                                  device_id=ad._unit_id)
            if r.isError():
                break
            out.extend(r.registers[:n])
    except Exception as e:
        print(f"  [AVISO] lectura de holding fallo: {e}")
    return out


def find_m_base(coils: list[bool]) -> int | None:
    n = len(coils)
    for base in range(n - max(M_PATTERN)):
        if all(coils[base + o] for o in M_PATTERN) and not coils[base + 1]:
            return base
    return None


def scan(ad: ModbusTCPAdapter) -> None:
    print("--- Escaneo de mapeo Modbus (test_servo) ---")
    coils = read_coils(ad, 0, 512)
    on = [i for i, v in enumerate(coils) if v]
    print(f"  Coils ON (0..511): {on}")

    m_base = find_m_base(coils)
    if m_base is not None:
        print(f"  Offset area M detectado: M0.0 -> coil {m_base} "
              f"(patron {[m_base + o for o in M_PATTERN]})")
    else:
        print("  [AVISO] no se detecto el patron de M (revisar que el IL este cargado)")

    di = read_discrete(ad, 0, 64)
    print(f"  Discrete ON (0..63): {[i for i, v in enumerate(di) if v]}")

    hr = read_holding(ad, 0, 256)
    v_base = None
    for i, v in enumerate(hr):
        if v == V_MARKER:
            v_base = i - 100
            print(f"  Offset area V detectado: VW0 -> holding {v_base} "
                  f"(marcador 0x1234 en holding {i})")
            break
    if v_base is None:
        print("  [AVISO] no se encontro el marcador V (0x1234)")
    print(f"  Holding 140..170: {hr[140:170]}")


def status(ad: ModbusTCPAdapter) -> None:
    inpos = ad.read_tag("IN_POSITION")
    home = ad.read_tag("HOME_SENSOR")
    d = ad.read_tag("SERVO_DIR")
    en = ad.read_tag("SERVO_ENABLE")
    lo = ad.read_tag("SERVO_POSACT_LO")
    hi = ad.read_tag("SERVO_POSACT_HI")
    print(f"  IN_POSITION (I0.0): {'ON' if inpos else 'OFF'}")
    print(f"  HOME        (I0.1): {'ON' if home else 'OFF'}")
    print(f"  DIR         (Q0.2): {'ON' if d else 'OFF'}")
    print(f"  ENABLE      (Q0.3): {'ON' if en else 'OFF'}")
    print(f"  POS_ACT: {join_dint(int(lo), int(hi))} pulsos")


def pulse(ad: ModbusTCPAdapter, tag: str) -> None:
    ad.write_tag(tag, True)
    time.sleep(0.2)
    ad.write_tag(tag, False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Prueba de servo Kinco (Modbus TCP)")
    ap.add_argument("--ip", default="192.168.0.252")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--enable", choices=["on", "off"])
    ap.add_argument("--home", action="store_true")
    ap.add_argument("--move", type=int, metavar="PULSOS")
    ap.add_argument("--jog", choices=["fwd", "rev", "stop"])
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--watch", type=float, default=0.0,
                    help="segundos manteniendo el jog")
    args = ap.parse_args()

    ad = ModbusTCPAdapter(PLCProfile.from_json(PROFILE), host=args.ip,
                          port=args.port, unit_id=args.unit, timeout=args.timeout)
    print(f"Conectando a {args.ip}:{args.port} (unit {args.unit})...")
    if not ad.connect():
        print("[FALLO] no se pudo conectar (IP/subred, Modbus TCP Server, firewall).")
        return 1
    print("[OK] conexion establecida\n")

    if args.scan:
        scan(ad)
        print()
    if args.status:
        status(ad)
        print()
    if args.enable:
        ad.write_tag("CMD_ENABLE", args.enable == "on")
        time.sleep(0.3)
        print(f"[OK] ENABLE = {args.enable}")
        status(ad)
    if args.home:
        print("[..] HOME...")
        pulse(ad, "CMD_HOME")
        time.sleep(0.5)
        status(ad)
    if args.move is not None:
        lo, hi = split_dint(args.move)
        ad.write_tag("SERVO_POS_LO", lo)
        ad.write_tag("SERVO_POS_HI", hi)
        time.sleep(0.2)
        print(f"[..] MOVE a {args.move} pulsos...")
        pulse(ad, "CMD_MOVE")
        time.sleep(0.5)
        status(ad)
    if args.jog:
        if args.jog == "stop":
            pulse(ad, "CMD_STOP")
            print("[OK] STOP")
        else:
            tag = "CMD_JOG_FWD" if args.jog == "fwd" else "CMD_JOG_REV"
            ad.write_tag(tag, True)
            print(f"[..] JOG {args.jog} durante {args.watch or 0.5}s")
            time.sleep(args.watch or 0.5)
            ad.write_tag(tag, False)
            pulse(ad, "CMD_STOP")
            print("[OK] JOG detenido")
    if args.stop:
        pulse(ad, "CMD_STOP")
        print("[OK] STOP")

    ad.disconnect()
    print("\nPRUEBA SERVO FINALIZADA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
