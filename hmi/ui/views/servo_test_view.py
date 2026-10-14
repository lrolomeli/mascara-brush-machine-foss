"""Vista de prueba del servomotor (pulsos + direccion + enable).

Pensada para el programa `plc/test_servo.il`:
  - Entradas: IN_POSITION (I0.0), HOME_SENSOR (I0.1).
  - Salidas:  SERVO_PULSE (Q0.0), SERVO_DIR (Q0.2), SERVO_ENABLE (Q0.3).
  - Comandos: CMD_ENABLE/HOME/MOVE/JOG_FWD/JOG_REV/STOP (memorias %M / %V).
  - Parametros: SERVO_MINF/MAXF/TIME/POS/DIRC/MODE (holding registers).

Esta vista NO toca las salidas fisicas: solo escribe comandos y parametros.

Secciones navegables: Estado, Control, Parametros, Barrido.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import (
    IndustrialButton,
    SectionFrame,
    ServoPositionDisplay,
    SimpleLED,
    join_dint,
    split_dint,
)


class ServoTestView(QWidget):
    """Vista de prueba de servo (comandos + parametros + estado + barrido)."""

    write_tag = Signal(str, object)

    FREQS_DEFAULT = ("5000, 7500, 10000, 15000, 20000, 30000, 40000, "
                     "50000, 70000, 100000, 150000, 200000")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_section = 0
        self._sections: list[QWidget] = []
        self._latest_pos = 0
        self._sweep_timer = QTimer(self)
        self._sweep_timer.setSingleShot(True)
        self._sweep_timer.timeout.connect(self._sweep_step)
        self._sweep_freqs: list[int] = []
        self._sweep_idx = 0
        self._sweep_state = ""
        self._sweep_pos0 = 0
        self._sweep_pos1 = 0
        self._sweep_running = False
        self._build_ui()

    # ------------------------------------------------------------------
    # Construccion de UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 10, 20, 10)

        title = QLabel("TEST SERVO (PULSO + DIRECCION + ENABLE)")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 8px;")
        root.addWidget(title)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(20)

        self._btn_up = self._nav_button("▲")
        self._btn_up.clicked.connect(self._on_nav_up)
        nav_layout.addWidget(self._btn_up)

        self._section_title = QLabel("ESTADO")
        self._section_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._section_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._section_title.setStyleSheet("color: #ffffff; padding: 8px;")
        nav_layout.addWidget(self._section_title, stretch=1)

        self._btn_down = self._nav_button("▼")
        self._btn_down.clicked.connect(self._on_nav_down)
        nav_layout.addWidget(self._btn_down)

        root.addLayout(nav_layout)

        self._container = QVBoxLayout()
        self._container.setSpacing(15)
        root.addLayout(self._container, stretch=1)

        self._build_status_section()
        self._build_control_section()
        self._build_params_section()
        self._build_sweep_section()

        self._show_section(0)
        root.addStretch()

    def _nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(60, 40)
        btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #e94560;
                border: 2px solid #e94560;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e94560;
                color: #ffffff;
            }
        """)
        return btn

    def _build_status_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)

        top_row = QHBoxLayout()
        top_row.setSpacing(15)
        top_row.addWidget(self._build_inputs_frame(), stretch=1)
        top_row.addWidget(self._build_outputs_frame(), stretch=1)
        layout.addLayout(top_row)

        pos_row = QHBoxLayout()
        self._display_pos = ServoPositionDisplay("Posicion actual (pulsos)")
        pos_row.addWidget(self._display_pos)
        pos_row.addStretch()
        layout.addLayout(pos_row)

        self._sections.append(section)
        self._container.addWidget(section)

    def _build_control_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        layout.addWidget(self._build_control_frame())
        self._sections.append(section)
        self._container.addWidget(section)

    def _build_params_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        layout.addWidget(self._build_params_frame())
        self._sections.append(section)
        self._container.addWidget(section)

    def _build_sweep_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        layout.addWidget(self._build_sweep_frame())
        self._sections.append(section)
        self._container.addWidget(section)

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
        layout.setSpacing(20)

        row = QHBoxLayout()
        row.setSpacing(12)

        self._btn_enable = IndustrialButton("ENABLE", "start", 180, 90)
        self._btn_enable.toggled.connect(
            lambda checked: self.write_tag.emit("CMD_ENABLE", checked))
        row.addWidget(self._btn_enable)

        self._btn_home = IndustrialButton("HOME", "neutral", 180, 90)
        self._btn_home.setCheckable(False)
        self._btn_home.clicked.connect(lambda: self._pulse("CMD_HOME"))
        row.addWidget(self._btn_home)

        self._btn_move = IndustrialButton("MOVER", "neutral", 180, 90)
        self._btn_move.setCheckable(False)
        self._btn_move.clicked.connect(lambda: self._pulse("CMD_MOVE"))
        row.addWidget(self._btn_move)

        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(12)

        self._btn_jog_fwd = IndustrialButton("JOG +", "start", 180, 90)
        self._btn_jog_fwd.setCheckable(False)
        self._btn_jog_fwd.pressed.connect(
            lambda: self.write_tag.emit("CMD_JOG_FWD", True))
        self._btn_jog_fwd.released.connect(
            lambda: self.write_tag.emit("CMD_JOG_FWD", False))
        row2.addWidget(self._btn_jog_fwd)

        self._btn_jog_rev = IndustrialButton("JOG -", "pause", 180, 90)
        self._btn_jog_rev.setCheckable(False)
        self._btn_jog_rev.pressed.connect(
            lambda: self.write_tag.emit("CMD_JOG_REV", True))
        self._btn_jog_rev.released.connect(
            lambda: self.write_tag.emit("CMD_JOG_REV", False))
        row2.addWidget(self._btn_jog_rev)

        self._btn_stop = IndustrialButton("STOP", "red_stop", 180, 90)
        self._btn_stop.setCheckable(False)
        self._btn_stop.clicked.connect(lambda: self._pulse("CMD_STOP"))
        row2.addWidget(self._btn_stop)

        layout.addLayout(row2)
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
        self._btn_apply = IndustrialButton("APLICAR PARAMETROS", "neutral", 320, 70)
        self._btn_apply.setCheckable(False)
        self._btn_apply.clicked.connect(self._on_apply_params)
        apply_row.addWidget(self._btn_apply)
        apply_row.addStretch()
        layout.addLayout(apply_row)
        return frame

    def _build_sweep_frame(self) -> SectionFrame:
        frame = SectionFrame("Barrido de frecuencia (buscar limite fiable)")
        layout = frame.content_layout
        layout.setSpacing(15)

        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(15)
        cfg_row.addWidget(self._label("Frecuencias (Hz, separadas por coma)"))

        self._sweep_freqs_edit = QLineEdit(self.FREQS_DEFAULT)
        self._sweep_freqs_edit.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
            }
        """)
        cfg_row.addWidget(self._sweep_freqs_edit, stretch=1)
        layout.addLayout(cfg_row)

        time_row = QHBoxLayout()
        time_row.setSpacing(15)
        time_row.addWidget(self._label("Tiempo por JOG (ms)"))
        self._sweep_jog_ms = self._spin(100, 10000, 1200)
        time_row.addWidget(self._sweep_jog_ms)
        time_row.addWidget(self._label("Asentamiento (ms)"))
        self._sweep_settle_ms = self._spin(50, 5000, 300)
        time_row.addWidget(self._sweep_settle_ms)
        time_row.addStretch()
        layout.addLayout(time_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(15)
        self._btn_sweep_start = IndustrialButton("INICIAR BARRIDO", "start", 260, 70)
        self._btn_sweep_start.setCheckable(False)
        self._btn_sweep_start.clicked.connect(self._on_sweep_start)
        btn_row.addWidget(self._btn_sweep_start)

        self._btn_sweep_cancel = IndustrialButton("CANCELAR", "red_stop", 200, 70)
        self._btn_sweep_cancel.setCheckable(False)
        self._btn_sweep_cancel.setEnabled(False)
        self._btn_sweep_cancel.clicked.connect(self._on_sweep_cancel)
        btn_row.addWidget(self._btn_sweep_cancel)

        self._sweep_status = self._label("Listo.")
        btn_row.addWidget(self._sweep_status, stretch=1)
        layout.addLayout(btn_row)

        self._sweep_table = QTableWidget(0, 7)
        self._sweep_table.setHorizontalHeaderLabels(
            ["MAXF (Hz)", "POS ini", "dFWD", "dREV", "retorno",
             "|dFWD|/esp", "estado"])
        self._sweep_table.verticalHeader().setVisible(False)
        self._sweep_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sweep_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._sweep_table.setMinimumHeight(220)
        self._sweep_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                color: #ffffff;
                gridline-color: #333333;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #16213e;
                color: #e94560;
                font-weight: bold;
                border: 1px solid #333333;
                padding: 4px;
            }
        """)
        layout.addWidget(self._sweep_table)
        return frame

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #cccccc; font-size: 13px;")
        return lbl

    def _spin(self, lo: int, hi: int, default: int) -> QSpinBox:
        sp = QSpinBox()
        sp.setRange(lo, hi)
        sp.setValue(default)
        sp.setMinimumWidth(120)
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
    # Navegacion por secciones
    # ------------------------------------------------------------------
    def _show_section(self, index: int) -> None:
        for i, section in enumerate(self._sections):
            section.setVisible(i == index)

        titles = ["ESTADO", "CONTROL", "PARAMETROS", "BARRIDO"]
        self._section_title.setText(titles[index])
        self._current_section = index

    def _on_nav_up(self) -> None:
        new_index = (self._current_section - 1) % len(self._sections)
        self._show_section(new_index)

    def _on_nav_down(self) -> None:
        new_index = (self._current_section + 1) % len(self._sections)
        self._show_section(new_index)

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
    # Barrido de frecuencia (maquina de estados con QTimer)
    # ------------------------------------------------------------------
    def _on_sweep_start(self) -> None:
        try:
            freqs = [int(x) for x in self._sweep_freqs_edit.text().split(",")
                     if x.strip()]
        except ValueError:
            self._sweep_status.setText("Lista de frecuencias invalida.")
            return
        if not freqs:
            self._sweep_status.setText("Introduce al menos una frecuencia.")
            return

        self._sweep_freqs = freqs
        self._sweep_idx = 0
        self._sweep_table.setRowCount(0)
        self._sweep_running = True
        self._btn_sweep_start.setEnabled(False)
        self._btn_sweep_cancel.setEnabled(True)
        self._sweep_status.setText("Configurando...")
        self._sweep_advance("CONFIG", 0)

    def _on_sweep_cancel(self) -> None:
        self._sweep_timer.stop()
        self._sweep_running = False
        self._safe_stop()
        self._btn_sweep_start.setEnabled(True)
        self._btn_sweep_cancel.setEnabled(False)
        self._sweep_status.setText("Cancelado.")

    def _safe_stop(self) -> None:
        self.write_tag.emit("CMD_JOG_FWD", False)
        self.write_tag.emit("CMD_JOG_REV", False)
        self.write_tag.emit("CMD_STOP", True)
        self.write_tag.emit("CMD_STOP", False)

    def _sweep_advance(self, state: str, delay_ms: int) -> None:
        self._sweep_state = state
        self._sweep_timer.start(delay_ms)

    def _sweep_step(self) -> None:
        if not self._sweep_running:
            return
        state = self._sweep_state
        jog_ms = self._sweep_jog_ms.value()
        settle_ms = self._sweep_settle_ms.value()

        if state == "CONFIG":
            self.write_tag.emit("CMD_ENABLE", True)
            self.write_tag.emit("SERVO_MODE", 1)
            self.write_tag.emit("SERVO_DIRC", 0)
            self._sweep_advance("SET_FREQ", 400)
        elif state == "SET_FREQ":
            f = self._sweep_freqs[self._sweep_idx]
            lo, hi = split_dint(f)
            self.write_tag.emit("SERVO_MAXF_LO", lo)
            self.write_tag.emit("SERVO_MAXF_HI", hi)
            self._sweep_status.setText(
                f"MAXF={f} Hz  (paso {self._sweep_idx + 1}/{len(self._sweep_freqs)})")
            self._sweep_advance("READ0", 300)
        elif state == "READ0":
            self._sweep_pos0 = self._latest_pos
            self.write_tag.emit("CMD_JOG_FWD", True)
            self._sweep_advance("FWD_OFF", jog_ms)
        elif state == "FWD_OFF":
            self.write_tag.emit("CMD_JOG_FWD", False)
            self._sweep_advance("READ1", settle_ms)
        elif state == "READ1":
            self._sweep_pos1 = self._latest_pos
            self.write_tag.emit("CMD_JOG_REV", True)
            self._sweep_advance("REV_OFF", jog_ms)
        elif state == "REV_OFF":
            self.write_tag.emit("CMD_JOG_REV", False)
            self._sweep_advance("READ2", settle_ms)
        elif state == "READ2":
            self._record_sweep_row(self._latest_pos)
            self._sweep_idx += 1
            if self._sweep_idx < len(self._sweep_freqs):
                self._sweep_advance("SET_FREQ", 0)
            else:
                self._sweep_advance("DONE", 0)
        elif state == "DONE":
            self._sweep_finish("Barrido finalizado.")

    def _record_sweep_row(self, pos2: int) -> None:
        f = self._sweep_freqs[self._sweep_idx]
        jog_s = self._sweep_jog_ms.value() / 1000.0
        d_fwd = self._sweep_pos1 - self._sweep_pos0
        d_rev = pos2 - self._sweep_pos1
        retorno = abs(pos2 - self._sweep_pos0)
        esperado = f * jog_s
        ratio = abs(d_fwd) / esperado if esperado else 0.0
        revisar = ratio < 0.85
        estado = "REVISAR" if revisar else "OK"

        row = self._sweep_table.rowCount()
        self._sweep_table.insertRow(row)
        valores = [f, self._sweep_pos0, d_fwd, d_rev, retorno,
                   f"{ratio:.2f}", estado]
        for col, val in enumerate(valores):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if revisar:
                item.setForeground(QBrush(QColor("#ff5252")))
            self._sweep_table.setItem(row, col, item)
        self._sweep_table.scrollToBottom()

    def _sweep_finish(self, msg: str) -> None:
        self._sweep_running = False
        self._safe_stop()
        self._btn_sweep_start.setEnabled(True)
        self._btn_sweep_cancel.setEnabled(False)
        self._sweep_status.setText(msg)

    # ------------------------------------------------------------------
    # Actualizacion de estado (datos del PLC)
    # ------------------------------------------------------------------
    def update_data(self, data: dict) -> None:
        self._led_inpos.set_on(bool(data.get("IN_POSITION", False)))
        self._led_home.set_on(bool(data.get("HOME_SENSOR", False)))
        self._led_dir.set_on(bool(data.get("SERVO_DIR", False)))
        self._led_enable.set_on(bool(data.get("SERVO_ENABLE", False)))

        lo = data.get("SERVO_POSACT_LO")
        hi = data.get("SERVO_POSACT_HI")
        if lo is not None and hi is not None:
            self._latest_pos = join_dint(int(lo), int(hi))
        else:
            self._latest_pos = int(data.get("SERVO_POS_ACTUAL", 0))
        self._display_pos.set_value(self._latest_pos)
