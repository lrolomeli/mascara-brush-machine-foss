"""Widgets industriales reutilizables para HMI tactil.

Botones gigantes, LEDs de estado, toggles de valvula y displays numricos
con tema oscuro de alto contraste para pantallas industriales.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class StatusLED(QWidget):
    """Indicador LED circular con label."""

    def __init__(self, label: str = "", color_off: str = "#555555",
                 color_on: str = "#00e676", size: int = 24, parent=None):
        super().__init__(parent)
        self._on = False
        self._color_off = QColor(color_off)
        self._color_on = QColor(color_on)
        self._size = size
        self._label_text = label

        self.setFixedSize(size + 10, size + 30 if label else size)

    def set_on(self, on: bool) -> None:
        self._on = on
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self._color_on if self._on else self._color_off
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(QBrush(color))
        y_offset = 28 if self._label_text else 0
        painter.drawEllipse(5, 2, self._size, self._size)
        painter.end()

        if self._label_text:
            painter2 = QPainter(self)
            painter2.setPen(QPen(QColor("#cccccc")))
            font = QFont("Segoe UI", 8)
            painter2.setFont(font)
            painter2.drawText(0, self._size + 4, self.width(), 20,
                              Qt.AlignmentFlag.AlignHCenter, self._label_text)
            painter2.end()


class IndustrialButton(QPushButton):
    """Boton tactil industrial grande con estados de color."""

    STYLES = {
        "start": ("#1b5e20", "#2e7d32", "#4caf50"),
        "stop": ("#b71c1c", "#c62828", "#ef5350"),
        "emergency": ("#880e0e", "#b71c1c", "#ff1744"),
        "pause": ("#e65100", "#ef6c00", "#ff9800"),
        "cycle_stop": ("#f57f17", "#f9a825", "#fdd835"),
        "neutral": ("#263238", "#37474f", "#546e7a"),
    }

    def __init__(self, label: str, style: str = "neutral",
                 min_width: int = 160, min_height: int = 80, parent=None):
        super().__init__(label, parent)
        self._style_name = style
        self.setMinimumSize(min_width, min_height)
        self.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self._apply_style(False)

    def _apply_style(self, checked: bool) -> None:
        dark, mid, light = self.STYLES.get(self._style_name, self.STYLES["neutral"])
        bg = light if checked else mid
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #ffffff;
                border: 2px solid {light};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {light};
                border-color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {dark};
            }}
            QPushButton:checked {{
                background-color: {light};
                border-color: #ffffff;
            }}
        """)

    def _setup_emergency(self) -> None:
        self.setMinimumSize(200, 100)
        self.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))


class ValveToggle(QWidget):
    """Toggle de valvula neumatica con LED + boton grande."""

    toggled_signal = Signal(int, bool)

    def __init__(self, valve_number: int, label: str | None = None, parent=None):
        super().__init__(parent)
        self._number = valve_number
        self._active = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        self._led = StatusLED(size=20)
        layout.addWidget(self._led, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._btn = IndustrialButton(f"V{valve_number}", "neutral", 100, 70)
        self._btn.setCheckable(True)
        self._btn.toggled.connect(self._on_toggled)
        layout.addWidget(self._btn)

        self._lbl = QLabel(label or f"Salida {valve_number}")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._lbl.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        layout.addWidget(self._lbl)

    def set_label_text(self, text: str) -> None:
        self._lbl.setText(text)

    def set_button_text(self, text: str) -> None:
        self._btn.setText(text)

    def _on_toggled(self, checked: bool) -> None:
        self._active = checked
        self._led.set_on(checked)
        self.toggled_signal.emit(self._number, checked)

    def set_state(self, active: bool) -> None:
        self._active = active
        self._btn.setChecked(active)
        self._led.set_on(active)


class ServoPositionDisplay(QWidget):
    """Display numerico grande tipo HMI industrial para posicion servo."""

    def __init__(self, label: str = "Posicion", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(label)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("color: #aaaaaa; font-size: 12px; font-weight: bold;")
        layout.addWidget(title)

        self._value_label = QLabel("0")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        self._value_label.setStyleSheet("""
            QLabel {
                color: #00e676;
                background-color: #0d1117;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 10px;
                min-width: 160px;
            }
        """)
        layout.addWidget(self._value_label)

    def set_value(self, value: int | float) -> None:
        self._value_label.setText(str(value))


class SectionFrame(QFrame):
    """Frame con titulo para agrupar controles en vistas."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._layout = QVBoxLayout(self)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #e94560; border: none; padding: 4px;")
        self._layout.addWidget(header)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout
