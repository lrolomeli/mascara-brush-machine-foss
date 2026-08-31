"""HMI Industrial - Punto de entrada.

Inicializa QApplication con tema oscuro industrial, crea el ModbusWorker
y la MainWindow. Ejecutar con: python -m hmi.main
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #0f0f23;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Noto Sans', sans-serif;
}
QLabel {
    color: #e0e0e0;
}
QMessageBox {
    background-color: #1a1a2e;
}
QMessageBox QLabel {
    color: #ffffff;
}
QMessageBox QPushButton {
    background-color: #e94560;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 80px;
}
QScrollBar:vertical {
    background-color: #0f0f23;
    width: 12px;
}
QScrollBar::handle:vertical {
    background-color: #333333;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def load_app_config() -> dict:
    config_path = CONFIG_DIR / "app_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "plc": {"ip": "192.168.1.10", "port": 502, "unit_id": 1,
                "active_profile": "delta_dvp"},
        "polling": {"interval_ms": 100},
    }


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)

    config = load_app_config()
    plc_cfg = config.get("plc", {})
    poll_cfg = config.get("polling", {})

    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    app.setFont(QFont("Segoe UI", 11))

    from hmi.comms.plc_adapter import ModbusTCPAdapter, PLCProfile
    from hmi.comms.modbus_worker import ModbusWorker
    from hmi.ui.main_window import MainWindow

    active_profile_name = plc_cfg.get("active_profile", "delta_dvp")
    profile_path = CONFIG_DIR / "plc_profiles" / f"{active_profile_name}.json"
    if not profile_path.exists():
        profiles = list((CONFIG_DIR / "plc_profiles").glob("*.json"))
        if profiles:
            profile_path = profiles[0]
        else:
            logger.error("No se encontro ningun perfil de PLC en %s", CONFIG_DIR / "plc_profiles")
            return 1

    profile = PLCProfile.from_json(profile_path)
    logger.info("Perfil activo: %s (%s)", profile.name, profile_path.name)

    adapter = ModbusTCPAdapter(
        profile=profile,
        host=plc_cfg.get("ip", "192.168.1.10"),
        port=plc_cfg.get("port", 502),
        unit_id=plc_cfg.get("unit_id", 1),
        timeout=plc_cfg.get("timeout_ms", 3000) / 1000.0,
    )

    worker = ModbusWorker(
        adapter=adapter,
        poll_interval_ms=poll_cfg.get("interval_ms", 100),
    )

    window = MainWindow(worker)
    window.showFullScreen()

    worker.start()

    exit_code = app.exec()

    worker.stop()
    adapter.disconnect()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
