"""PLC Adapter - Abstraccion de hardware PLC.

Patron Adaptador: traduce nombres simbolicos de variables a direcciones Modbus
fisicas segun el perfil de PLC activo (Delta, Kinco, Schneider, etc.).

Cambio de PLC = cargar otro JSON. Cero modificaciones al codigo HMI.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TAG_TYPES = {
    "coil": "coils",
    "discrete_input": "discrete_inputs",
    "holding_register": "holding_registers",
    "input_register": "input_registers",
}

COIL_TYPES = {"coil", "discrete_input"}
REGISTER_TYPES = {"holding_register", "input_register"}


@dataclass
class TagInfo:
    name: str
    modbus_type: str  # coil, discrete_input, holding_register, input_register
    address: int
    description: str = ""

    @property
    def pymodbus_group(self) -> str:
        return TAG_TYPES[self.modbus_type]

    @property
    def is_coil(self) -> bool:
        return self.modbus_type in COIL_TYPES

    @property
    def is_register(self) -> bool:
        return self.modbus_type in REGISTER_TYPES


@dataclass
class PLCProfile:
    name: str
    description: str
    notes: str
    tags: dict[str, TagInfo] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> PLCProfile:
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        tags = {}
        for tag_name, tag_def in raw.get("tags", {}).items():
            tags[tag_name] = TagInfo(
                name=tag_name,
                modbus_type=tag_def["type"],
                address=tag_def["address"],
                description=tag_def.get("description", ""),
            )

        return cls(
            name=raw.get("name", path.stem),
            description=raw.get("description", ""),
            notes=raw.get("notes", ""),
            tags=tags,
        )

    def get_tag(self, name: str) -> TagInfo:
        if name not in self.tags:
            raise KeyError(f"Tag '{name}' no existe en perfil '{self.name}'. "
                           f"Tags disponibles: {list(self.tags.keys())}")
        return self.tags[name]


class PLCAdapter(ABC):
    """Interfaz abstracta para comunicacion con PLC."""

    def __init__(self, profile: PLCProfile):
        self._profile = profile

    @property
    def profile(self) -> PLCProfile:
        return self._profile

    def load_profile(self, path: str | Path) -> None:
        self._profile = PLCProfile.from_json(path)
        logger.info("Perfil PLC cargado: %s", self._profile.name)

    def get_tag_info(self, name: str) -> TagInfo:
        return self._profile.get_tag(name)

    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...

    @abstractmethod
    def read_coils(self, names: list[str]) -> dict[str, bool]:
        ...

    @abstractmethod
    def read_discrete_inputs(self, names: list[str]) -> dict[str, bool]:
        ...

    @abstractmethod
    def read_holding_registers(self, names: list[str]) -> dict[str, int]:
        ...

    @abstractmethod
    def read_input_registers(self, names: list[str]) -> dict[str, int]:
        ...

    @abstractmethod
    def write_coil(self, name: str, value: bool) -> bool:
        ...

    @abstractmethod
    def write_register(self, name: str, value: int) -> bool:
        ...

    def read_tag(self, name: str) -> bool | int:
        tag = self._profile.get_tag(name)
        if tag.is_coil:
            result = self.read_coils([name])
            return result.get(name, False)
        else:
            result = self.read_holding_registers([name]) if tag.modbus_type == "holding_register" \
                else self.read_input_registers([name])
            return result.get(name, 0)

    def write_tag(self, name: str, value: bool | int) -> bool:
        tag = self._profile.get_tag(name)
        if tag.is_coil:
            return self.write_coil(name, bool(value))
        else:
            return self.write_register(name, int(value))

    def read_all_inputs(self) -> dict[str, bool | int]:
        """Lee todos los inputs del PLC en un solo ciclo (optimizado)."""
        data: dict[str, bool | int] = {}

        coils = [n for n, t in self._profile.tags.items() if t.modbus_type == "coil"]
        data.update(self.read_coils(coils))

        di = [n for n, t in self._profile.tags.items() if t.modbus_type == "discrete_input"]
        data.update(self.read_discrete_inputs(di))

        hr = [n for n, t in self._profile.tags.items() if t.modbus_type == "holding_register"]
        data.update(self.read_holding_registers(hr))

        ir = [n for n, t in self._profile.tags.items() if t.modbus_type == "input_register"]
        data.update(self.read_input_registers(ir))

        return data


class ModbusTCPAdapter(PLCAdapter):
    """Implementacion concreta: Modbus TCP via pymodbus."""

    def __init__(self, profile: PLCProfile, host: str = "127.0.0.1",
                 port: int = 502, unit_id: int = 1, timeout: float = 3.0):
        super().__init__(profile)
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._timeout = timeout
        self._client = None
        self._connected = False

    def _make_client(self):
        from pymodbus.client import ModbusTcpClient
        return ModbusTcpClient(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        )

    def connect(self) -> bool:
        try:
            self._client = self._make_client()
            self._connected = self._client.connect()
            if self._connected:
                logger.info("Conectado a PLC %s:%d", self._host, self._port)
            else:
                logger.warning("No se pudo conectar a %s:%d", self._host, self._port)
        except Exception as e:
            logger.error("Error de conexion: %s", e)
            self._connected = False
        return self._connected

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._connected = False
            logger.info("Desconectado del PLC")

    def is_connected(self) -> bool:
        return self._connected

    def _group_by_address(self, names: list[str]) -> dict[str, list[tuple[str, int]]]:
        groups: dict[str, list[tuple[str, int]]] = {}
        for name in names:
            tag = self._profile.get_tag(name)
            groups.setdefault(tag.modbus_type, []).append((name, tag.address))
        return groups

    def _merge_ranges(self, addresses: list[int]) -> list[tuple[int, int]]:
        if not addresses:
            return []
        sorted_addrs = sorted(set(addresses))
        ranges = []
        start = sorted_addrs[0]
        end = start
        for addr in sorted_addrs[1:]:
            if addr == end + 1:
                end = addr
            else:
                ranges.append((start, end))
                start = addr
                end = addr
        ranges.append((start, end))
        return ranges

    def read_coils(self, names: list[str]) -> dict[str, bool]:
        result = {}
        if not names or not self._connected:
            return result
        try:
            addresses = [(n, self._profile.get_tag(n).address) for n in names]
            for start, end in self._merge_ranges([a for _, a in addresses]):
                count = end - start + 1
                resp = self._client.read_coils(start, count=count, device_id=self._unit_id)
                if not resp.isError():
                    for n, addr in addresses:
                        if start <= addr <= end:
                            result[n] = bool(resp.bits[addr - start])
        except Exception as e:
            logger.error("Error leyendo coils: %s", e)
        return result

    def read_discrete_inputs(self, names: list[str]) -> dict[str, bool]:
        result = {}
        if not names or not self._connected:
            return result
        try:
            addresses = [(n, self._profile.get_tag(n).address) for n in names]
            for start, end in self._merge_ranges([a for _, a in addresses]):
                count = end - start + 1
                resp = self._client.read_discrete_inputs(start, count=count, device_id=self._unit_id)
                if not resp.isError():
                    for n, addr in addresses:
                        if start <= addr <= end:
                            result[n] = bool(resp.bits[addr - start])
        except Exception as e:
            logger.error("Error leyendo discrete inputs: %s", e)
        return result

    def read_holding_registers(self, names: list[str]) -> dict[str, int]:
        result = {}
        if not names or not self._connected:
            return result
        try:
            addresses = [(n, self._profile.get_tag(n).address) for n in names]
            for start, end in self._merge_ranges([a for _, a in addresses]):
                count = end - start + 1
                resp = self._client.read_holding_registers(start, count=count, device_id=self._unit_id)
                if not resp.isError():
                    for n, addr in addresses:
                        if start <= addr <= end:
                            result[n] = resp.registers[addr - start]
        except Exception as e:
            logger.error("Error leyendo holding registers: %s", e)
        return result

    def read_input_registers(self, names: list[str]) -> dict[str, int]:
        result = {}
        if not names or not self._connected:
            return result
        try:
            addresses = [(n, self._profile.get_tag(n).address) for n in names]
            for start, end in self._merge_ranges([a for _, a in addresses]):
                count = end - start + 1
                resp = self._client.read_input_registers(start, count=count, device_id=self._unit_id)
                if not resp.isError():
                    for n, addr in addresses:
                        if start <= addr <= end:
                            result[n] = resp.registers[addr - start]
        except Exception as e:
            logger.error("Error leyendo input registers: %s", e)
        return result

    def write_coil(self, name: str, value: bool) -> bool:
        if not self._connected:
            return False
        try:
            tag = self._profile.get_tag(name)
            resp = self._client.write_coil(tag.address, value, device_id=self._unit_id)
            return not resp.isError()
        except Exception as e:
            logger.error("Error escribiendo coil %s: %s", name, e)
            return False

    def write_register(self, name: str, value: int) -> bool:
        if not self._connected:
            return False
        try:
            tag = self._profile.get_tag(name)
            resp = self._client.write_register(tag.address, value, device_id=self._unit_id)
            return not resp.isError()
        except Exception as e:
            logger.error("Error escribiendo register %s: %s", name, e)
            return False

    def set_connection(self, host: str, port: int, unit_id: int = 1) -> None:
        self._host = host
        self._port = port
        self._unit_id = unit_id
        if self._connected:
            self.disconnect()
