"""Modbus Worker - Hilo de comunicacion no bloqueante.

QThread que ejecuta el ciclo de polling Modbus TCP y emite signal Qt
con el diccionario de datos simbolicos completo en cada ciclo.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QThread, Signal, Slot

from hmi.comms.plc_adapter import ModbusTCPAdapter, PLCProfile

logger = logging.getLogger(__name__)


class ModbusWorker(QThread):
    """Hilo dedicado a leer/escribir el PLC via Modbus TCP."""

    data_ready = Signal(dict)
    connection_status = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, adapter: ModbusTCPAdapter, poll_interval_ms: int = 100,
                 parent=None):
        super().__init__(parent)
        self._adapter = adapter
        self._poll_interval_ms = poll_interval_ms
        self._running = False
        self._write_queue: list[tuple[str, Any]] = []

    @property
    def adapter(self) -> ModbusTCPAdapter:
        return self._adapter

    def configure(self, host: str, port: int, unit_id: int,
                  poll_interval_ms: int = 100) -> None:
        self._adapter.set_connection(host, port, unit_id)
        self._poll_interval_ms = poll_interval_ms

    def load_new_profile(self, profile_path: str) -> None:
        self._adapter.load_profile(profile_path)

    def enqueue_write(self, tag_name: str, value: Any) -> None:
        self._write_queue.append((tag_name, value))

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def run(self) -> None:
        self._running = True
        logger.info("ModbusWorker iniciado (poll=%dms)", self._poll_interval_ms)

        if not self._adapter.is_connected():
            connected = self._adapter.connect()
            self.connection_status.emit(connected)
            if not connected:
                logger.warning("No se pudo conectar. Reintentando en el loop...")

        while self._running:
            if not self._adapter.is_connected():
                connected = self._adapter.connect()
                self.connection_status.emit(connected)
                if not connected:
                    self.msleep(self._adapter._timeout * 1000 + 1000)
                    continue

            while self._write_queue:
                tag_name, value = self._write_queue.pop(0)
                ok = self._adapter.write_tag(tag_name, value)
                if not ok:
                    self.error_occurred.emit(f"Error escribiendo {tag_name}")

            try:
                data = self._adapter.read_all_inputs()
                self.data_ready.emit(data)
            except Exception as e:
                logger.error("Error en ciclo de lectura: %s", e)
                self.error_occurred.emit(str(e))
                self._adapter.disconnect()
                self.connection_status.emit(False)

            self.msleep(self._poll_interval_ms)

        self._adapter.disconnect()
        self.connection_status.emit(False)
        logger.info("ModbusWorker detenido")
