#!/usr/bin/env python3
"""Barrido de frecuencia del servo (pulsos + direccion + enable).

Replica la secuencia validada en hardware pero subiendo MAXF de forma
progresiva para encontrar el limite donde la frecuencia deja de ser fiable.

Usa el perfil `config/plc_profiles/test_kinco.json` (programa `plc/test_servo.il`).

Secuencia por frecuencia:
    configurar MAXF -> JOG adelante (t) -> leer pos -> JOG atras (t) -> leer pos

Criterio de fiabilidad (orientativo; ademas hay que mirar el motor):
    delta ~= MAXF * tiempo_jog. Si |delta| / esperado < umbral => posible
    perdida de pulsos (se marca REVISAR).

Por defecto barre fino de 30 kHz a 40 kHz (paso 500 Hz) para localizar donde
el motor deja de responder.

Ejemplos:
  # Barrido por defecto (30 kHz .. 40 kHz, paso 500 Hz)
  python tests/test_servo_sweep.py --ip 192.168.0.252

  # Generar la secuencia con --from/--to/--step
  python tests/test_servo_sweep.py --ip 192.168.0.252 \\
      --from 30000 --to 40000 --step 500

  # Lista explicita o tiempos personalizados
  python tests/test_servo_sweep.py --ip 192.168.0.252 \\
      --freqs "5000,10000,20000,40000,80000,160000,200000" --jog-time 0.5
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

FREQS_DEFAULT = list(range(30000, 40001, 500))


def split_dint(value: int) -> tuple[int, int]:
    v = value & 0xFFFFFFFF
    return v & 0xFFFF, (v >> 16) & 0xFFFF


def join_dint(lo: int, hi: int) -> int:
    v = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return v - 0x100000000 if v & 0x80000000 else v


def read_pos(ad: ModbusTCPAdapter) -> int:
    lo = ad.read_tag("SERVO_POSACT_LO")
    hi = ad.read_tag("SERVO_POSACT_HI")
    return join_dint(int(lo), int(hi))


def write_maxf(ad: ModbusTCPAdapter, hz: int) -> None:
    lo, hi = split_dint(hz)
    ad.write_tag("SERVO_MAXF_LO", lo)
    ad.write_tag("SERVO_MAXF_HI", hi)


def pulse_jog(ad: ModbusTCPAdapter, tag: str, seconds: float) -> None:
    ad.write_tag(tag, True)
    time.sleep(seconds)
    ad.write_tag(tag, False)


def setup(ad: ModbusTCPAdapter, minf: int, mode: int, dirc: int,
          settle: float) -> None:
    ad.write_tag("SERVO_MINF", minf)
    ad.write_tag("SERVO_MODE", mode)
    ad.write_tag("SERVO_DIRC", dirc)
    ad.write_tag("CMD_ENABLE", True)
    time.sleep(settle)


def sweep(ad: ModbusTCPAdapter, freqs: list[int], jog_time: float,
          settle: float, threshold: float) -> None:
    print(f"{'MAXF(Hz)':>9} | {'POS ini':>10} | {'dFWD':>10} | "
          f"{'dREV':>10} | {'retorno':>10} | {'|dFWD|/esp':>10} | estado")
    print("-" * 92)

    unreliable: list[int] = []
    for f in freqs:
        write_maxf(ad, f)
        time.sleep(0.2)

        pos0 = read_pos(ad)

        pulse_jog(ad, "CMD_JOG_FWD", jog_time)
        time.sleep(settle)
        pos1 = read_pos(ad)

        pulse_jog(ad, "CMD_JOG_REV", jog_time)
        time.sleep(settle)
        pos2 = read_pos(ad)

        d_fwd = pos1 - pos0
        d_rev = pos2 - pos1
        retorno = abs(pos2 - pos0)

        esperado = f * jog_time
        ratio = abs(d_fwd) / esperado if esperado else 0.0

        estado = "OK"
        if ratio < threshold:
            estado = "REVISAR"
            unreliable.append(f)

        print(f"{f:>9} | {pos0:>10} | {d_fwd:>10} | {d_rev:>10} | "
              f"{retorno:>10} | {ratio:>10.2f} | {estado}")

    print("-" * 92)
    if unreliable:
        print("Frecuencias a revisar (posible perdida de pulsos): "
              + ", ".join(str(x) for x in unreliable))
    else:
        print("Todas las frecuencias dentro del umbral.")


def build_freqs(args) -> list[int]:
    """Construye la secuencia de frecuencias: --freqs > --from/--to/--step > default."""
    if args.freqs:
        return [int(x) for x in args.freqs.split(",") if x.strip()]
    if args.from_hz is not None or args.to_hz is not None or args.step_hz is not None:
        start = args.from_hz if args.from_hz is not None else 30000
        end = args.to_hz if args.to_hz is not None else 40000
        step = args.step_hz if args.step_hz is not None else 500
        if step <= 0:
            raise ValueError("--step debe ser > 0")
        if end < start:
            raise ValueError("--to debe ser >= --from")
        return list(range(start, end + 1, step))
    return list(FREQS_DEFAULT)


def main() -> int:
    ap = argparse.ArgumentParser(description="Barrido de frecuencia del servo Kinco")
    ap.add_argument("--ip", default="192.168.0.252")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--freqs", default=None,
                    help="lista separada por comas (Hz); tiene prioridad sobre --from/--to/--step")
    ap.add_argument("--from", dest="from_hz", type=int, default=None,
                    help="frecuencia inicial (Hz) para generar el barrido (def. 30000)")
    ap.add_argument("--to", dest="to_hz", type=int, default=None,
                    help="frecuencia final (Hz) para generar el barrido (def. 40000)")
    ap.add_argument("--step", dest="step_hz", type=int, default=None,
                    help="paso (Hz) para generar el barrido (def. 500)")
    ap.add_argument("--jog-time", type=float, default=1.2,
                    help="segundos de cada JOG +/- (def. 1.2)")
    ap.add_argument("--settle", type=float, default=0.3,
                    help="segundos de asentamiento tras cada JOG (def. 0.3)")
    ap.add_argument("--minf", type=int, default=125)
    ap.add_argument("--mode", type=int, default=1)
    ap.add_argument("--dirc", type=int, default=0)
    ap.add_argument("--threshold", type=float, default=0.85,
                    help="ratio minimo |dFWD|/esperado para marcar OK (def. 0.85)")
    ap.add_argument("--no-disable", action="store_true",
                    help="no deshabilitar el servo al terminar")
    args = ap.parse_args()

    try:
        freqs = build_freqs(args)
    except ValueError as e:
        ap.error(str(e))

    if not freqs:
        ap.error("la secuencia de frecuencias esta vacia")

    bad = [f for f in freqs if f < 125 or f > 200000]
    if bad:
        print(f"[AVISO] MAXF fuera de rango 125..200000 Hz: {bad}")

    ad = ModbusTCPAdapter(PLCProfile.from_json(PROFILE), host=args.ip,
                          port=args.port, unit_id=args.unit, timeout=args.timeout)
    print(f"Conectando a {args.ip}:{args.port} (unit {args.unit})...")
    if not ad.connect():
        print("[FALLO] no se pudo conectar (IP/subred, Modbus TCP Server, firewall).")
        return 1
    print("[OK] conexion establecida\n")

    try:
        setup(ad, args.minf, args.mode, args.dirc, args.settle)
        print(f"Configurado: MINF={args.minf} MODE={args.mode} DIRC={args.dirc} "
              f"jog={args.jog_time}s settle={args.settle}s\n")
        print("=== MAXF", freqs[0], "..", freqs[-1], "Hz (mira el motor) ===")
        sweep(ad, freqs, args.jog_time, args.settle, args.threshold)
    except KeyboardInterrupt:
        print("\n[!] Interrumpido por el usuario.")
    finally:
        try:
            ad.write_tag("CMD_STOP", True)
            time.sleep(0.2)
            ad.write_tag("CMD_STOP", False)
            if not args.no_disable:
                ad.write_tag("CMD_ENABLE", False)
        except Exception:
            pass
        ad.disconnect()

    print("\nBARRIDO DE FRECUENCIA FINALIZADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
