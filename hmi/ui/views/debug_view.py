"""Vista de Depuracion por Secciones.

Lectura/escritura directa de tags con selector + log de operaciones.
"""

from __future__ import annotations

import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import IndustrialButton, SectionFrame


class DebugView(QWidget):
    """Vista de depuracion: lectura/escritura directa de tags."""

    read_tag_request = Signal(str)
    write_tag_request = Signal(str, str)

    def __init__(self, tag_names: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._tag_names = tag_names or []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("DEPURACION POR SECCIONES")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 10px;")
        root.addWidget(title)

        rw_frame = SectionFrame("Lectura / Escritura de Tag")
        rwl = rw_frame.content_layout

        tag_row = QHBoxLayout()
        tag_lbl = QLabel("Tag:")
        tag_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        tag_row.addWidget(tag_lbl)
        self._tag_combo = QComboBox()
        self._tag_combo.addItems(self._tag_names)
        self._tag_combo.setMinimumWidth(250)
        self._tag_combo.setStyleSheet("""
            QComboBox {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: #ffffff;
                selection-background-color: #e94560;
            }
        """)
        tag_row.addWidget(self._tag_combo, stretch=1)

        self._btn_read = IndustrialButton("READ", "neutral", 100, 50)
        self._btn_read.clicked.connect(self._on_read)
        tag_row.addWidget(self._btn_read)
        rwl.addLayout(tag_row)

        write_row = QHBoxLayout()
        val_lbl = QLabel("Valor:")
        val_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        write_row.addWidget(val_lbl)
        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText("0 / 1 / True / False")
        self._value_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        write_row.addWidget(self._value_input, stretch=1)

        self._btn_write = IndustrialButton("WRITE", "stop", 100, 50)
        self._btn_write.clicked.connect(self._on_write)
        write_row.addWidget(self._btn_write)
        rwl.addLayout(write_row)
        root.addWidget(rw_frame)

        log_frame = SectionFrame("Log de Operaciones")
        ll = log_frame.content_layout
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(200)
        self._log.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1117;
                color: #00e676;
                border: 1px solid #333333;
                border-radius: 4px;
                font-family: Consolas;
                font-size: 12px;
                padding: 8px;
            }
        """)
        ll.addWidget(self._log)
        root.addWidget(log_frame)

        root.addStretch()

    def _on_read(self) -> None:
        tag = self._tag_combo.currentText()
        if tag:
            self._log_msg(f"READ -> {tag}")
            self.read_tag_request.emit(tag)

    def _on_write(self) -> None:
        tag = self._tag_combo.currentText()
        value = self._value_input.text().strip()
        if tag and value:
            self._log_msg(f"WRITE -> {tag} = {value}")
            self.write_tag_request.emit(tag, value)
            self._value_input.clear()

    def _log_msg(self, msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{ts}] {msg}")

    def set_tag_names(self, names: list[str]) -> None:
        self._tag_names = names
        self._tag_combo.clear()
        self._tag_combo.addItems(names)

    def log_response(self, tag: str, value: object) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{ts}] <- {tag} = {value}")

    def log_error(self, msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{ts}] ERROR: {msg}")
