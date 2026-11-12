"""
Widget de Gráficos de Temperatura 24h, Demanda Térmica y Radiación Solar.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from typing import List, Dict


class ChartsWidget(QWidget):
    """Visualizador de curvas horarias de temperatura y climatización."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.fig = Figure(facecolor="#181820", tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.ax_temp = self.fig.add_subplot(211)
        self.ax_power = self.fig.add_subplot(212)

        self._apply_dark_style(self.ax_temp)
        self._apply_dark_style(self.ax_power)

    def _apply_dark_style(self, ax):
        ax.set_facecolor("#22222b")
        ax.tick_params(colors="#aaaaaa", labelsize=9)
        ax.grid(True, linestyle="--", alpha=0.3, color="#555566")
        for spine in ax.spines.values():
            spine.set_color("#444455")

    def update_charts(self, results: List[Dict]):
        if not results:
            return

        self.ax_temp.clear()
        self.ax_power.clear()
        self._apply_dark_style(self.ax_temp)
        self._apply_dark_style(self.ax_power)

        hours = [r["hour"] for r in results]
        t_ext = [r["t_ext"] for r in results]
        t_l1 = [r["t_int_level_1"] for r in results]
        t_l2 = [r["t_int_level_2"] for r in results]
        t_app1 = [r["t_apparent_level_1"] for r in results]
        ac_btu_1 = [r["ac_btu_h_1"] for r in results]
        ac_btu_2 = [r["ac_btu_h_2"] for r in results]

        # 1. Gráfico Superior: Temperaturas (°C)
        self.ax_temp.plot(hours, t_ext, label="T. Exterior (°C)", color="#ff9800", linestyle="--", linewidth=1.8)
        self.ax_temp.plot(hours, t_l1, label="Nivel 1 Interior", color="#2196f3", linewidth=2.2)
        self.ax_temp.plot(hours, t_l2, label="Nivel 2 Interior (Expuesto)", color="#f44336", linewidth=2.2)
        self.ax_temp.plot(hours, t_app1, label="Sensación Confort (Ventilador)", color="#4caf50", linestyle=":", linewidth=2.0)

        # Banda de confort térmico humano (21°C - 26°C)
        self.ax_temp.axhspan(21.0, 26.0, color="#4caf50", alpha=0.12, label="Zona Confort (21-26°C)")

        self.ax_temp.set_ylabel("Temperatura (°C)", color="#ffffff", fontsize=10)
        self.ax_temp.set_title("Comportamiento Térmico Horario (24 Horas)", color="#ffffff", fontsize=11, fontweight="bold")
        self.ax_temp.set_xlim(0, 23)
        self.ax_temp.legend(loc="upper left", facecolor="#2a2a35", edgecolor="#444455", labelcolor="#ffffff", fontsize=8)

        # 2. Gráfico Inferior: Demanda de A/C (BTU/h) o Radiación Solar
        if any(b > 0 for b in ac_btu_1) or any(b > 0 for b in ac_btu_2):
            self.ax_power.plot(hours, ac_btu_1, label="A/C Nivel 1 (BTU/h)", color="#00bcd4", linewidth=2.0)
            self.ax_power.plot(hours, ac_btu_2, label="A/C Nivel 2 (BTU/h)", color="#e91e63", linewidth=2.0)
            self.ax_power.set_ylabel("Demanda A/C (BTU/h)", color="#ffffff", fontsize=10)
        else:
            rad = [r["solar_radiation"] for r in results]
            self.ax_power.fill_between(hours, rad, color="#ffd700", alpha=0.35, label="Radiación Solar Global")
            self.ax_power.plot(hours, rad, color="#ffd700", linewidth=1.5)
            self.ax_power.set_ylabel("Radiación (W/m²)", color="#ffffff", fontsize=10)

        self.ax_power.set_xlabel("Hora del Día (00:00 - 23:00)", color="#ffffff", fontsize=10)
        self.ax_power.set_xlim(0, 23)
        self.ax_power.legend(loc="upper right", facecolor="#2a2a35", edgecolor="#444455", labelcolor="#ffffff", fontsize=8)

        self.fig.tight_layout()
        self.canvas.draw_idle()
