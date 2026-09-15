"""Test de integracion del SimulatedPLC contra su servidor Modbus TCP real.

Regresion del camino completo escritura->scan->lectura via pymodbus.
Cubre el caso en que pymodbus 3.x invoca el action del SimDevice dos veces
por escritura (una con values y otra con values=None): la segunda llamada
NO debe sobrescribir el estado escrito.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pymodbus.server import StartTcpServer  # noqa: E402
from pymodbus.simulator import SimData, SimDevice, DataType  # noqa: E402

from hmi.comms.plc_adapter import ModbusTCPAdapter, PLCProfile  # noqa: E402
from tests.run_simulator import SimulatedPLC, load_tags  # noqa: E402

PORT = 15024


def make_server(plc: SimulatedPLC):
    simdata = (
        [SimData(address=0, count=2000, values=False, datatype=DataType.BITS)],
        [SimData(address=0, count=2000, values=False, datatype=DataType.BITS)],
        [SimData(address=0, count=2000, values=0, datatype=DataType.REGISTERS)],
        [SimData(address=0, count=2000, values=0, datatype=DataType.REGISTERS)],
    )
    device = SimDevice(id=1, simdata=simdata, action=plc.plc_action_callback)
    StartTcpServer(context=device, address=("127.0.0.1", PORT))


def main() -> int:
    plc = SimulatedPLC(load_tags("generic_kinco"))
    plc.start()

    threading.Thread(target=make_server, args=(plc,), daemon=True).start()
    time.sleep(1.2)

    profile_path = PROJECT_ROOT / "config" / "plc_profiles" / "generic_kinco.json"
    ad = ModbusTCPAdapter(PLCProfile.from_json(profile_path),
                          host="127.0.0.1", port=PORT, unit_id=1, timeout=2)
    assert ad.connect(), "No se pudo conectar"
    print("[OK] Conexion establecida con SimulatedPLC")

    # 1) Escritura de modo manual debe persistir (regresion del doble call)
    assert ad.write_tag("MODE_MANUAL", True), "write MODE_MANUAL fallo"
    time.sleep(0.4)
    assert ad.read_tag("MODE_MANUAL") is True, "MODE_MANUAL no persiste (double-call)"
    print("[OK] MODE_MANUAL=True persiste en lectura")

    # 2) Forzado manual de una valvula fisica y reaccion de sensores
    assert ad.read_tag("S11") is True, "S11 debe estar ON en reposo (Y6 home)"
    assert ad.write_tag("CMD_Y6", True), "write CMD_Y6 fallo"
    time.sleep(0.6)
    assert ad.read_tag("S11") is False, "S11 debe pasar OFF al forzar CMD_Y6"
    print("[OK] Forzado CMD_Y6 activa la planta y apaga S11")

    # 2b) E-stop (DI 24, ultimo del rango mergado 8..24) se lee correctamente
    data = ad.read_all_inputs()
    assert data.get("S1_EMERGENCY_STOP") is True, "E-Stop debe leerse como ON (NC libre)"
    print("[OK] E-Stop (DI 24) se lee correctamente")

    # 3) Escritura de registros persiste (p.ej. parametro de servo)
    assert ad.write_tag("SERVO_POS_TARGET", 1234), "write SERVO_POS_TARGET fallo"
    time.sleep(0.4)
    assert ad.read_tag("SERVO_POS_TARGET") == 1234, "registro no persiste (double-call)"
    print("[OK] SERVO_POS_TARGET=1234 persiste en lectura")

    # 3b) Lectura de coils mas alla de la primera palabra del rango.
    # Forzamos Y18 (fisico en 1017, fuera de la ventana de 16 bits desde 1000);
    # el estado fisico debe leerse correctamente via el rango mergado 1000..1023.
    assert ad.write_tag("CMD_Y18", True), "write CMD_Y18 fallo"
    time.sleep(0.7)
    assert ad.read_tag("Y18") is True, "Y18 (coil 1017) debe leerse ON forzado"
    raw = ad._client.read_coils(1000, count=24, device_id=1)
    assert raw.bits[17] is True, "coil 1017 (Y18) no se lee en el rango mergado"
    assert ad.write_tag("CMD_Y18", False), "write CMD_Y18 fallo"
    print("[OK] Coil 1017 (Y18, fuera de la primera palabra) se lee correctamente")

    # 4) Ciclo AUTO arranca con INICIO via Modbus (saliendo de modo manual)
    assert ad.write_tag("MODE_MANUAL", False), "write MODE_MANUAL fallo"
    time.sleep(0.6)
    assert ad.write_tag("CMD_START", True), "write CMD_START fallo"
    time.sleep(1.5)
    pa = ad.read_tag("Paso_Alambre")
    pp = ad.read_tag("Paso_Pinza")
    assert (pa, pp) != (0, 0), f"el ciclo no arranco (pasos {pa}/{pp})"
    print(f"[OK] Ciclo AUTO arrancado: Paso_Alambre={pa} Paso_Pinza={pp}")

    ad.disconnect()
    print("TEST SIM SERVER PASADO CORRECTAMENTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())