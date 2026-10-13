"""Vista de prueba del servomotor (pulsos + direccion + enable).

Pensada para el programa `plc/test_servo.il`:
  - Entradas: IN_POSITION (I0.0), HOME_SENSOR (I0.1).
  - Salidas:  SERVO_PULSE (Q0.0), SERVO_DIR (Q0.2), SERVO_ENABLE (Q0.3).
  - Comandos: CMD_ENABLE/HOME/MOVE/JOG_FWD/JOG_REV/STOP (memorias %M).
  - Parametros: SERVO_MINF/MAXF/TIME/POS/DIRC/MODE (holding registers).

Esta vista NO toca las salidas fisicas: solo escribe comandos y parametros.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import (
    IndustrialButton,
    SectionFrame,
    ServoPositionDisplay,
    SimpleLED,
)


def split_dint(value: int) -> tuple[int, int]:
    """Divide un entero de 32 bits con signo en (word_bajo, word_alto)."""
    v = value & 0xFFFFFFFF
    return v & 0xFFFF, (v >> 16) & 0xFFFF


def join_dint(lo: int, hi: int) -> int:
    """Recombina dos words en un entero de 32 bits con signo."""
    v = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    if v & 0x80000000:
        v -= 0x100000000
    return v


class ServoTestView(QWidget):
    """Vista de prueba de servo (comandos + parametros + estado)."""

    write_tag = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Construccion de UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("TEST SERVO (PULSO + DIRECCION + ENABLE)")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 8px;")
        root.addWidget(title)

        top_row = QHBoxLayout()
        top_row.setSpacing(15)
        top_row.addWidget(self._build_inputs_frame(), stretch=1)
        top_row.addWidget(self._build_outputs_frame(), stretch=1)
        root.addLayout(top_row)

        root.addWidget(self._build_control_frame())
        root.addWidget(self._build_params_frame())
        root.addStretch()

    def _build_inputs_frame(self) -> SectionFrame:
        frame = SectionFrame("Entradas")
        layout = frame.content_layout

        row = QHBoxLayout()
        row.setSpacing(25)
        self._led_inpos = SimpleLED(18)
        row.addWidget(self._led_inpos)
        row.addWidget(self._label("IN POSITION READY (I0.0)"))

        self._led_home = SimpleLED(18)
        row.addWidget(self._led_home)
        row.addWidget(self._label("HOME / PROXIMIDAD (I0.1)"))
        row.addStretch()
        layout.addLayout(row)
        return frame

    def _build_outputs_frame(self) -> SectionFrame:
        frame = SectionFrame("Estado de salidas")
        layout = frame.content_layout

        row = QHBoxLayout()
        row.setSpacing(25)
        self._led_dir = SimpleLED(18)
        row.addWidget(self._led_dir)
        row.addWidget(self._label("DIRECCION (Q0.2)"))

        self._led_enable = SimpleLED(18)
        row.addWidget(self._led_enable)
        row.addWidget(self._label("ENABLE (Q0.3)"))
        row.addStretch()
        layout.addLayout(row)
        return frame

    def _build_control_frame(self) -> SectionFrame:
        frame = SectionFrame("Control")
        layout = frame.content_layout

        row = QHBoxLayout()
        row.setSpacing(12)

        self._btn_enable = IndustrialButton("ENABLE", "start", 140, 70)
        self._btn_enable.toggled.connect(
            lambda checked: self.write_tag.emit("CMD_ENABLE", checked))
        row.addWidget(self._btn_enable)

        self._btn_home = IndustrialButton("HOME", "neutral", 140, 70)
        self._btn_home.setCheckable(False)
        self._btn_home.clicked.connect(lambda: self._pulse("CMD_HOME"))
        row.addWidget(self._btn_home)

        self._btn_move = IndustrialButton("MOVER", "neutral", 140, 70)
        self._btn_move.setCheckable(False)
        self._btn_move.clicked.connect(lambda: self._pulse("CMD_MOVE"))
        row.addWidget(self._btn_move)

        self._btn_jog_fwd = IndustrialButton("JOG +", "start", 140, 70)
        self._btn_jog_fwd.setCheckable(False)
        self._btn_jog_fwd.pressed.connect(
            lambda: self.write_tag.emit("CMD_JOG_FWD", True))
        self._btn_jog_fwd.released.connect(
            lambda: self.write_tag.emit("CMD_JOG_FWD", False))
        row.addWidget(self._btn_jog_fwd)

        self._btn_jog_rev = IndustrialButton("JOG -", "pause", 140, 70)
        self._btn_jog_rev.setCheckable(False)
        self._btn_jog_rev.pressed.connect(
            lambda: self.write_tag.emit("CMD_JOG_REV", True))
        self._btn_jog_rev.released.connect(
            lambda: self.write_tag.emit("CMD_JOG_REV", False))
        row.addWidget(self._btn_jog_rev)

        self._btn_stop = IndustrialButton("STOP", "red_stop", 140, 70)
        self._btn_stop.setCheckable(False)
        self._btn_stop.clicked.connect(lambda: self._pulse("CMD_STOP"))
        row.addWidget(self._btn_stop)

        layout.addLayout(row)
        return frame

    def _build_params_frame(self) -> SectionFrame:
        frame = SectionFrame("Parametros (holding registers)")
        layout = frame.content_layout

        grid = QGridLayout()
        grid.setSpacing(10)

        self._sp_minf = self._spin(125, 65535, 500)
        self._sp_maxf = self._spin(125, 200000, 5000)
        self._sp_time = self._spin(1, 60000, 200)
        self._sp_pos = self._spin(-1000000, 1000000, 0)
        self._sp_dirc = self._spin(0, 1, 0)
        self._sp_mode = self._spin(0, 1, 1)

        self._add_param(grid, 0, 0, "MINF (Hz)", self._sp_minf)
        self._add_param(grid, 0, 1, "MAXF (Hz)", self._sp_maxf)
        self._add_param(grid, 0, 2, "TIME (ms)", self._sp_time)
        self._add_param(grid, 1, 0, "POS (pulsos)", self._sp_pos)
        self._add_param(grid, 1, 1, "DIRC (home)", self._sp_dirc)
        self._add_param(grid, 1, 2, "MODE (home)", self._sp_mode)
        layout.addLayout(grid)

        apply_row = QHBoxLayout()
        self._btn_apply = IndustrialButton("APLICAR PARAMETROS", "neutral", 280, 60)
        self._btn_apply.setCheckable(False)
        self._btn_apply.clicked.connect(self._on_apply_params)
        apply_row.addWidget(self._btn_apply)

        self._display_pos = ServoPositionDisplay("Posicion actual (pulsos)")
        apply_row.addStretch()
        apply_row.addWidget(self._display_pos)
        layout.addLayout(apply_row)
        return frame

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #cccccc; font-size: 13px;")
        return lbl

    def _spin(self, lo: int, hi: int, default: int) -> QSpinBox:
        sp = QSpinBox()
        sp.setRange(lo, hi)
        sp.setValue(default)
        sp.setMinimumWidth(110)
        sp.setStyleSheet("""
            QSpinBox {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 14px;
            }
        """)
        return sp

    def _add_param(self, grid: QGridLayout, row: int, col: int,
                   text: str, widget: QSpinBox) -> None:
        cell = QVBoxLayout()
        cell.addWidget(self._label(text))
        cell.addWidget(widget)
        grid.addLayout(cell, row, col)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _pulse(self, tag: str) -> None:
        self.write_tag.emit(tag, True)
        self.write_tag.emit(tag, False)

    def _on_apply_params(self) -> None:
        self.write_tag.emit("SERVO_MINF", self._sp_minf.value())
        self.write_tag.emit("SERVO_TIME", self._sp_time.value())
        lo, hi = split_dint(self._sp_maxf.value())
        self.write_tag.emit("SERVO_MAXF_LO", lo)
        self.write_tag.emit("SERVO_MAXF_HI", hi)
        lo, hi = split_dint(self._sp_pos.value())
        self.write_tag.emit("SERVO_POS_LO", lo)
        self.write_tag.emit("SERVO_POS_HI", hi)
        self.write_tag.emit("SERVO_DIRC", self._sp_dirc.value())
        self.write_tag.emit("SERVO_MODE", self._sp_mode.value())

    # ------------------------------------------------------------------
    # Actualizacion de estado (datos del PLC)
    # ------------------------------------------------------------------
    def update_data(self, data: dict) -> None:
        self._led_inpos.set_on(bool(data.get("IN_POSITION", False)))
        self._led_home.set_on(bool(data.get("HOME_SENSOR", False)))
        self._led_dir.set_on(bool(data.get("SERVO_DIR", False)))
        self._led_enable.set_on(bool(data.get("SERVO_ENABLE", False)))

        lo = data.get("SERVO_POSACT_LO", 0)
        hi = data.get("SERVO_POSACT_HI", 0)
        if lo is not None and hi is not None:
            self._display_pos.set_value(join_dint(int(lo), int(hi)))
