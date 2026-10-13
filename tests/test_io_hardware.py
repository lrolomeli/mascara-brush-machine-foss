#!/usr/bin/env python3
"""Prueba minima de I/O fisica contra un PLC Kinco real (Modbus TCP).

Usa el mismo `ModbusTCPAdapter` que el HMI, de modo que valida tambien la pila
de comunicacion del HMI. Pensado para el programa `plc/test_io.il`:
  %Q0.0 = coil 0 (boton virtual HMI)  ->  %Q0.1 = coil 1 (espejo)
  %I0.0 = discrete 0 (boton fisico)   ->  %Q0.2 = coil 2 (espejo)

Ejemplos:
  python tests/test_io_hardware.py --ip 192.168.0.252 --hmi-to-plc
  python tests/test_io_hardware.py --ip 192.168.0.252 --plc-to-hmi --watch 15
  python tests/test_io_hardware.py --ip 192.168.0.252 --scan
  python tests/test_io_hardware.py --ip 192.168.0.252            # ambas pruebas
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from hmi.comms.plc_adapter import ModbusTCPAdapter, PLCProfile, TagInfo  # noqa: E402


def make_profile() -> PLCProfile:
    tags = {
        "HMI_BOTON": TagInfo("HMI_BOTON", "coil", 0, "Boton virtual HMI (coil 0)"),
        "LED_ESPEJO": TagInfo("LED_ESPEJO", "coil", 1, "Espejo de %Q0.0 (coil 1)"),
        "BOTON_FISICO": TagInfo("BOTON_FISICO", "discrete_input", 0, "Boton fisico %I0.0"),
        "LED_FISICO": TagInfo("LED_FISICO", "coil", 2, "Espejo de %I0.0 (coil 2)"),
    }
    return PLCProfile("Test I/O", "Prueba fisica minima", "", tags)


def read_bits(ad: ModbusTCPAdapter, fc: str, start: int, count: int) -> list[bool]:
    client = ad._client
    if fc == "coils":
        resp = client.read_coils(start, count=count, device_id=ad._unit_id)
    else:
        resp = client.read_discrete_inputs(start, count=count, device_id=ad._unit_id)
    if resp.isError():
        return []
    return [bool(b) for b in resp.bits[:count]]


def read_regs(ad: ModbusTCPAdapter, fc: str, start: int, count: int) -> list[int]:
    client = ad._client
    if fc == "hr":
        resp = client.read_holding_registers(start, count=count, device_id=ad._unit_id)
    else:
        resp = client.read_input_registers(start, count=count, device_id=ad._unit_id)
    if resp.isError():
        return []
    return list(resp.registers[:count])


def fmt_bits(bits: list[bool], start: int) -> str:
    on = [str(start + i) for i, v in enumerate(bits) if v]
    return ", ".join(on) if on else "(ninguno)"


def test_hmi_to_plc(ad: ModbusTCPAdapter) -> bool:
    print("--- Prueba HMI -> PLC -> programa ---")
    ok = True

    ad.write_tag("HMI_BOTON", True)
    time.sleep(0.4)
    led = ad.read_tag("LED_ESPEJO")
    print(f"  coil 0 (HMI) = ON  ->  coil 1 (espejo) = {'ON' if led else 'OFF'}")
    if not led:
        print("  [FALLO] el espejo coil 1 no se activo.")
        print("          -> Revisar mapeo (correr --scan) y que el IL este descargado.")
        ok = False
    else:
        print("  [OK] HMI -> PLC -> programa")

    ad.write_tag("HMI_BOTON", False)
    time.sleep(0.4)
    led = ad.read_tag("LED_ESPEJO")
    if led:
        print("  [FALLO] coil 1 no se apago al liberar coil 0.")
        ok = False
    else:
        print("  [OK] coil 1 volvio a OFF")
    return ok


def test_plc_to_hmi(ad: ModbusTCPAdapter, watch: float) -> bool:
    print("--- Prueba boton fisico -> PLC -> HMI ---")
    print("  Pulsa el boton fisico conectado a %I0.0 (Ctrl+C para terminar).")
    end = time.monotonic() + watch if watch > 0 else None
    prev = None
    saw_press = False
    while True:
        boton = ad.read_tag("BOTON_FISICO")
        led = ad.read_tag("LED_FISICO")
        state = (bool(boton), bool(led))
        if state != prev:
            print(f"  %I0.0 = {'ON ' if boton else 'OFF'}  ->  coil 2 = "
                  f"{'ON ' if led else 'OFF'}")
            prev = state
        if boton and led:
            saw_press = True
        if end is None or time.monotonic() >= end:
            break
        time.sleep(0.1)
    if saw_press:
        print("  [OK] boton fisico -> PLC -> HMI")
        return True
    print("  [AVISO] no se observo el boton pulsado con el espejo activo.")
    print("          -> Revisar cableado de %I0.0 y el mapeo (--scan).")
    return False


def test_scan(ad: ModbusTCPAdapter) -> None:
    print("--- Escaneo de mapeo Modbus ---")
    coils = read_bits(ad, "coils", 0, 64)
    print(f"  Coils 0..63 ON:            {fmt_bits(coils, 0)}")
    di = read_bits(ad, "di", 0, 64)
    print(f"  Discrete inputs 0..63 ON:  {fmt_bits(di, 0)}")
    hr = read_regs(ad, "hr", 0, 16)
    print(f"  Holding regs 0..15:        {hr}")
    ir = read_regs(ad, "ir", 0, 16)
    print(f"  Input regs 0..15:          {ir}")

    print("  Escribiendo coil 0 = ON y observando coils 0..63...")
    ad.write_tag("HMI_BOTON", True)
    time.sleep(0.5)
    coils2 = read_bits(ad, "coils", 0, 64)
    changed = [i for i in range(64) if i < len(coils2) and coils2[i]]
    print(f"  Coils ON tras escribir coil 0: {changed}")
    ad.write_tag("HMI_BOTON", False)
    print("  (coil 0 liberado)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prueba de I/O fisica Kinco (Modbus TCP)")
    ap.add_argument("--ip", default="192.168.0.252")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--hmi-to-plc", action="store_true")
    ap.add_argument("--plc-to-hmi", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--watch", type=float, default=15.0,
                    help="segundos a observar el boton fisico (0 = hasta Ctrl+C)")
    args = ap.parse_args()

    ad = ModbusTCPAdapter(make_profile(), host=args.ip, port=args.port,
                          unit_id=args.unit, timeout=args.timeout)
    print(f"Conectando a {args.ip}:{args.port} (unit {args.unit})...")
    if not ad.connect():
        print("[FALLO] no se pudo conectar. Revisa IP/subred, Modbus TCP Server "
              "habilitado y firewall.")
        return 1
    print("[OK] conexion establecida\n")

    run_all = not (args.hmi_to_plc or args.plc_to_hmi or args.scan)
    results = []

    if args.scan:
        test_scan(ad)
        print()
    if run_all or args.hmi_to_plc:
        results.append(test_hmi_to_plc(ad))
        print()
    if run_all or args.plc_to_hmi:
        results.append(test_plc_to_hmi(ad, args.watch))
        print()

    ad.disconnect()

    if results and all(results):
        print("PRUEBA I/O FISICA PASADA CORRECTAMENTE")
        return 0
    if results:
        print("PRUEBA I/O FISICA CON FALLOS (ver arriba)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
