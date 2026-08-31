"""Servidor Modbus TCP simulado para pruebas sin PLC fisico.

Uso: .venv/bin/python tests/run_simulator.py [ip] [puerto]
Por defecto: 0.0.0.0:5020
"""
from __future__ import annotations

import sys
import time

from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)


def make_block(val=0, n=600):
    return ModbusSequentialDataBlock(1, [val] * n)


def main() -> int:
    ip = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5020

    co = [0] * 600
    di = [0] * 600
    hr = [0] * 600
    ir = [0] * 600

    # Simular sensores ON para demostracion
    di[0] = 1  # SENSOR_1
    di[1] = 1  # SENSOR_2
    hr[0] = 1500  # SERVO_SPEED actual
    ir[0] = 2400  # SERVO_POS_ACTUAL
    ir[1] = 500   # SERVO_ACTUAL_SPEED
    ir[2] = 12    # SERVO_TORQUE

    co_block = ModbusSequentialDataBlock(1, co)
    di_block = ModbusSequentialDataBlock(1, di)
    hr_block = ModbusSequentialDataBlock(1, hr)
    ir_block = ModbusSequentialDataBlock(1, ir)

    store = ModbusDeviceContext(di=di_block, co=co_block, hr=hr_block, ir=ir_block)
    ctx = ModbusServerContext(devices={1: store})

    print(f"Servidor Modbus TCP simulado en {ip}:{port}")
    print("Tags de ejemplo: CMD_START, VALVE_1..10, SERVO_SPEED, SENSOR_1/2")
    print("Presiona Ctrl+C para detener.")
    try:
        StartTcpServer(ctx, address=(ip, port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
