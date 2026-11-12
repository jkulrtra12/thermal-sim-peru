"""
Ventana Principal de la Aplicación de Simulación Térmica y Bioclimática (Windows).
"""

import os
import math
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPushButton, QGroupBox, QFormLayout, QFileDialog, QSplitter,
    QFrame, QMessageBox, QStatusBar, QSlider, QDialog, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from core import (
    PERU_CITIES,
    PREDEFINED_ROOFS,
    PREDEFINED_CEILINGS,
    PREDEFINED_WALLS,
    PREDEFINED_WINDOWS,
    RoofCeilingAssembly,
    ThermalZoneConfig,
    NeighborObstacle,
    WindTurbineVentilator,
    MechanicalVentilation,
    CeilingComfortFan,
    AirConditioningSystem,
    MultiLevelThermalSimulator,
    EM110Evaluator,
    ThermalReportGenerator,
    CalculationMemoryGenerator,
)
from geometry.building_model import BuildingGeometry3D, Surface3D
from geometry.sketchup_loader import SketchUpLoader
from ui.viewer_3d import Viewer3DWidget
from ui.floor_plan_widget import FloorPlanWidget
from ui.charts_widget import ChartsWidget
from ui.material_dialog import MaterialSelectionDialog
from ui.calculation_memory_widget import CalculationMemoryWidget


class AddWindowDialog(QDialog):
    """Diálogo interactivo para insertar ventanas en vanos de fachada."""
    def __init__(self, house_bounds: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insertar Ventana en Fachada")
        self.resize(380, 290)
        self.hb = house_bounds
        self.created_surface = None

        layout = QFormLayout(self)
        self.combo_facade = QComboBox()
        self.combo_facade.addItems([
            "Fachada Sur (Frontal)",
            "Fachada Norte (Posterior)",
            "Fachada Lateral Este",
            "Fachada Lateral Oeste"
        ])
        layout.addRow("Fachada de Montaje:", self.combo_facade)

        self.combo_level = QComboBox()
        self.combo_level.addItems(["Nivel 1 (Planta Baja)", "Nivel 2 (Planta Alta)"])
        layout.addRow("Nivel de Piso:", self.combo_level)

        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(0.4, 10.0)
        self.spin_width.setValue(1.80)
        self.spin_width.setSuffix(" m")
        layout.addRow("Ancho de Ventana:", self.spin_width)

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.4, 4.0)
        self.spin_height.setValue(1.20)
        self.spin_height.setSuffix(" m")
        layout.addRow("Altura de Ventana:", self.spin_height)

        self.spin_sill = QDoubleSpinBox()
        self.spin_sill.setRange(0.0, 3.0)
        self.spin_sill.setValue(1.00)
        self.spin_sill.setSuffix(" m")
        layout.addRow("Altura de Alféizar:", self.spin_sill)

        self.slider_pos = QSlider(Qt.Orientation.Horizontal)
        self.slider_pos.setRange(10, 90)
        self.slider_pos.setValue(50)
        layout.addRow("Posición en Fachada:", self.slider_pos)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("Insertar Ventana")
        btn_ok.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 6px;")
        btn_ok.clicked.connect(self._create_window)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

    def _create_window(self):
        facade = self.combo_facade.currentText()
        is_level_2 = ("Nivel 2" in self.combo_level.currentText())
        level = 2 if is_level_2 else 1
        w = self.spin_width.value()
        h = self.spin_height.value()
        sill = self.spin_sill.value()
        pct = self.slider_pos.value() / 100.0

        xmin, xmax = self.hb["xmin"], self.hb["xmax"]
        ymin, ymax = self.hb["ymin"], self.hb["ymax"]
        zmin = self.hb["zmin"]
        lx = self.hb["len_x"]
        ly = self.hb["len_y"]

        z_base = zmin + (2.85 if is_level_2 else 0.0)
        z0 = z_base + sill
        z1 = z0 + h

        if "Sur" in facade:
            x_mid = xmin + pct * lx
            x0 = max(xmin + 0.1, x_mid - w / 2.0)
            x1 = min(xmax - 0.1, x0 + w)
            y = ymin - 0.02
            verts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
            orient = "Sur"
        elif "Norte" in facade:
            x_mid = xmin + pct * lx
            x0 = max(xmin + 0.1, x_mid - w / 2.0)
            x1 = min(xmax - 0.1, x0 + w)
            y = ymax + 0.02
            verts = [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)]
            orient = "Norte"
        elif "Oeste" in facade:
            y_mid = ymin + pct * ly
            y0 = max(ymin + 0.1, y_mid - w / 2.0)
            y1 = min(ymax - 0.1, y0 + w)
            x = xmin - 0.02
            verts = [(x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1)]
            orient = "Oeste"
        else:  # Este
            y_mid = ymin + pct * ly
            y0 = max(ymin + 0.1, y_mid - w / 2.0)
            y1 = min(ymax - 0.1, y0 + w)
            x = xmax + 0.02
            verts = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
            orient = "Este"

        self.created_surface = Surface3D(
            name=f"Ventana_{orient}_N{level}",
            surface_type="window",
            level=level,
            vertices=verts,
            orientation=orient,
            material_name="Vidrio Simple Claro 4 mm",
            thickness_m=0.004
        )
        self.accept()


class _DummyQtyWidget:
    def __init__(self, v=1): self._v = v
    def value(self): return self._v
    def setEnabled(self, *a, **k): pass
    def setVisible(self, *a, **k): pass
    def blockSignals(self, *a, **k): pass
    def setValue(self, v): self._v = v


class MainWindow(QMainWindow):
    """Ventana principal del software de análisis térmico."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador Térmico Bioclimático 3D (Perú) - Para SketchUp")
        self.resize(1280, 850)

        # Estado del modelo y simulación
        self.current_city = PERU_CITIES["Piura (Costa Norte - Cálido Extremo)"]
        self.selected_roof = PREDEFINED_ROOFS["UPVC 2.5 mm"]
        self.selected_slab = PREDEFINED_ROOFS["Losa Aligerada Concreto (20 cm)"]
        self.selected_ceiling = PREDEFINED_CEILINGS["Fibra Mineral (15 mm / 5/8\")"]
        self.selected_wall = PREDEFINED_WALLS["Ladrillo King Kong 18 huecos (Tarrajeado 15 cm)"]
        self.selected_window = PREDEFINED_WINDOWS["Vidrio Simple Claro 4 mm"]

        self.last_results = []

        # Unidades individuales de equipamiento (Soporte multi-punto dinámico EM.110)
        self.exhaust_units = [
            {"name": "Extractor #1", "level": 1, "wall": "📍 Pared Norte (Posterior)", "offset_pct": 50, "flow": 1200.0, "x": 4.0, "y": 4.85, "z": 2.4, "enabled": True}
        ]
        self.supply_units = [
            {"name": "Inyector #1", "level": 1, "wall": "📍 Pared Sur (Frontal)", "offset_pct": 50, "flow": 1200.0, "x": 4.0, "y": 0.15, "z": 2.0, "enabled": True}
        ]
        self.fan_units = [
            {"name": "Ventilador #1", "level": 1, "mount": "techo", "preset": "📍 Centro Habitación", "offset_x": 50, "offset_y": 50, "speed": "Media (1.0 m/s - Confort Típico)", "air_speed_m_s": 1.0, "power_w": 75.0, "airflow_m3_h": 4500.0, "x": 4.0, "y": 2.5, "z": 2.6, "enabled": True}
        ]
        self.ac_units = [
            {"name": "A/C Split #1", "level": 1, "wall": "📍 Pared Sur (Frontal)", "offset_pct": 50, "height_m": 2.3, "setpoint": 24.0, "cap_mode": "24,000 BTU/h (2.0 TR - Comercial Típico)", "nominal_btu_h": 24000.0, "cop": 3.2, "is_auto": False, "x": 2.0, "y": 0.15, "z": 2.3, "enabled": True}
        ]
        self.eolic_units = [
            {"name": "Turbina Eólica #1", "preset": "📍 Cumbrera Central (Punto más alto)", "offset_pct": 35, "dia": "24 pulgadas (60 cm)", "x": 2.8, "y": 2.5, "z": 5.6, "enabled": True},
            {"name": "Turbina Eólica #2", "preset": "📍 Cumbrera Central (Punto más alto)", "offset_pct": 65, "dia": "24 pulgadas (60 cm)", "x": 5.2, "y": 2.5, "z": 5.6, "enabled": True}
        ]

        self._init_ui()
        self._apply_dark_theme()
        self._populate_inspector()
        self._apply_ac_preset()
        self._apply_fan_preset()
        self._apply_eolic_preset()
        self._apply_exhaust_preset()
        self._apply_supply_preset()
        self.run_simulation()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Divisor Horizontal Principal (Permite al usuario arrastrar y redimensionar el ancho de las pestañas sin colapso)
        self.main_hsplitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_hsplitter.setChildrenCollapsible(False)
        main_layout.addWidget(self.main_hsplitter)

        # ---------------------------------------------------------------------
        # PANEL LATERAL IZQUIERDO: CONFIGURACIONES EN PESTAÑAS (REDIMENSIONABLE)
        # ---------------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setMinimumWidth(420)
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(4, 4, 4, 4)

        # Botones de barra lateral superior
        btn_top_box = QHBoxLayout()
        self.btn_import_skp = QPushButton("📂 Cargar SketchUp...")
        self.btn_import_skp.setFixedHeight(36)
        self.btn_import_skp.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_import_skp.clicked.connect(self._import_sketchup_file)

        self.btn_export_report = QPushButton("📑 Informe...")
        self.btn_export_report.setFixedHeight(36)
        self.btn_export_report.setFixedWidth(100)
        self.btn_export_report.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_export_report.setToolTip("Generar Informe Técnico Completo y Cumplimiento de Norma EM.110")
        self.btn_export_report.clicked.connect(self._export_technical_report)

        btn_top_box.addWidget(self.btn_import_skp)
        btn_top_box.addWidget(self.btn_export_report)
        side_layout.addLayout(btn_top_box)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(False)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 8px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        side_layout.addWidget(self.tabs)

        # Pestañas
        self._build_tab_climate()
        self._build_tab_occupancy()
        self._build_tab_geometry()
        self._build_tab_inspector()
        self._build_tab_roof_ceiling()
        self._build_tab_walls()
        self._build_tab_hvac()

        self.main_hsplitter.addWidget(sidebar)

        # ---------------------------------------------------------------------
        # ÁREA CENTRAL: TARJETAS KPI + VISOR 3D / PLANTA 2D + GRÁFICOS 24H
        # ---------------------------------------------------------------------
        content_widget = QWidget()
        content_widget.setMinimumWidth(550)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(4, 4, 4, 4)

        # 1. Tarjetas KPI superiores
        self.kpi_layout = QHBoxLayout()
        self.card_l1 = self._create_kpi_card("T. Máxima Nivel 1", "-- °C", "#2196f3")
        self.card_l2 = self._create_kpi_card("T. Máxima Nivel 2", "-- °C", "#f44336")
        self.card_shade = self._create_kpi_card("Alivio por Sombra Vecina", "-- °C", "#ff9800")
        self.card_ac = self._create_kpi_card("Potencia A/C Requerida", "-- BTU/h", "#00bcd4")
        self.card_cmp = self._create_kpi_card("Confort CMP (EM.110)", "--", "#4caf50")

        self.kpi_layout.addWidget(self.card_l1)
        self.kpi_layout.addWidget(self.card_l2)
        self.kpi_layout.addWidget(self.card_shade)
        self.kpi_layout.addWidget(self.card_ac)
        self.kpi_layout.addWidget(self.card_cmp)
        content_layout.addLayout(self.kpi_layout)

        # 2. Splitter con Visores Centrales (3D y Corte Planta 2D por Alturas) y Gráficos
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.center_tabs = QTabWidget()
        self.center_tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }
        """)

        self.viewer_3d = Viewer3DWidget()
        self.viewer_3d.hour_changed.connect(self._on_hour_slider_changed)
        self.center_tabs.addTab(self.viewer_3d, "🧊 Visor 3D Interactivo")

        self.floor_plan_widget = FloorPlanWidget()
        self.floor_plan_widget.equipment_moved.connect(self._on_floor_plan_equipment_moved)
        self.center_tabs.addTab(self.floor_plan_widget, "🗺️ Mapa de Calor por Planta (Corte 2D / Alturas)")

        self.calc_memory_widget = CalculationMemoryWidget()
        self.calc_memory_widget.request_refresh.connect(self.run_simulation)
        self.center_tabs.addTab(self.calc_memory_widget, "📑 Memoria de Cálculo (RNE EM.110)")

        splitter.addWidget(self.center_tabs)

        self.charts_widget = ChartsWidget()
        splitter.addWidget(self.charts_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        content_layout.addWidget(splitter)
        self.main_hsplitter.addWidget(content_widget)

        # Establecer anchos iniciales del divisor: 520px para el panel de pestañas, resto para 3D
        self.main_hsplitter.setSizes([520, 880])
        self.main_hsplitter.setStretchFactor(0, 0)
        self.main_hsplitter.setStretchFactor(1, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Listo - Simulación actualizada en tiempo real.")

    def _create_kpi_card(self, title: str, default_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(f"background-color: #242430; border: 1px solid #3d3d4d; border-radius: 6px; padding: 4px;")
        ly = QVBoxLayout(card)
        ly.setContentsMargins(6, 4, 6, 4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet(f"color: {color_hex}; font-size: 18px; font-weight: bold;")
        v_lbl.setObjectName("val_lbl")
        ly.addWidget(t_lbl)
        ly.addWidget(v_lbl)
        return card

    def _create_stepper(self, spin_widget):
        """Envuelve un QSpinBox o QDoubleSpinBox en un contenedor con botones táctiles grandes [－] y [＋]."""
        container = QWidget()
        box = QHBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        btn_minus = QPushButton("－")
        btn_minus.setFixedSize(30, 28)
        btn_minus.setToolTip("Decrementar valor")
        btn_minus.setStyleSheet("""
            QPushButton {
                font-size: 15px;
                font-weight: bold;
                background-color: #3b3b52;
                color: #ffffff;
                border: 1px solid #5a5a7d;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #505072;
                border-color: #0288d1;
            }
            QPushButton:pressed {
                background-color: #0288d1;
            }
        """)
        btn_minus.clicked.connect(lambda: spin_widget.stepDown())
        btn_plus = QPushButton("＋")
        btn_plus.setFixedSize(30, 28)
        btn_plus.setToolTip("Incrementar valor")
        btn_plus.setStyleSheet("""
            QPushButton {
                font-size: 15px;
                font-weight: bold;
                background-color: #3b3b52;
                color: #ffffff;
                border: 1px solid #5a5a7d;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #505072;
                border-color: #0288d1;
            }
            QPushButton:pressed {
                background-color: #0288d1;
            }
        """)
        btn_plus.clicked.connect(lambda: spin_widget.stepUp())
        box.addWidget(spin_widget)
        box.addWidget(btn_minus)
        box.addWidget(btn_plus)
        return container

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DE PESTAÑAS DE CONFIGURACIÓN
    # -------------------------------------------------------------------------
    def _build_tab_climate(self):
        w = QWidget()
        form = QFormLayout(w)

        self.combo_city = QComboBox()
        for city_name in PERU_CITIES.keys():
            self.combo_city.addItem(city_name)
        self.combo_city.setCurrentText("Piura (Costa Norte - Cálido Extremo)")
        self.combo_city.currentIndexChanged.connect(self._on_city_changed)
        form.addRow("Ciudad del Perú:", self.combo_city)

        self.combo_season = QComboBox()
        self.combo_season.addItems(["Verano (Crítico calor)", "Invierno"])
        self.combo_season.currentIndexChanged.connect(self.run_simulation)
        form.addRow("Estación:", self.combo_season)

        self.spin_north = QSpinBox()
        self.spin_north.setRange(0, 360)
        self.spin_north.setValue(0)
        self.spin_north.setSuffix(" °")
        self.spin_north.valueChanged.connect(self.run_simulation)
        form.addRow("Orientación Norte:", self.spin_north)

        self.lbl_city_desc = QLabel(self.current_city.description)
        self.lbl_city_desc.setWordWrap(True)
        self.lbl_city_desc.setStyleSheet("color: #88c0d0; font-style: italic; font-size: 11px;")
        form.addRow("Descripción:", self.lbl_city_desc)

        # Grupo 1: Temperatura Ambiental Exterior Inicial y Rango Diario
        box_temp = QGroupBox("Temperatura Ambiental Exterior")
        f_temp = QFormLayout(box_temp)

        self.lbl_t_ext_now = QLabel("T. Exterior Inicial (14:00): 36.3 °C")
        self.lbl_t_ext_now.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 12px;")
        f_temp.addRow("Condición Actual:", self.lbl_t_ext_now)

        self.lbl_t_ext_range = QLabel(f"Rango Diario Verano: Mín {self.current_city.summer_t_min:.1f} °C / Máx {self.current_city.summer_t_max:.1f} °C")
        self.lbl_t_ext_range.setStyleSheet("color: #90a4ae; font-size: 10.5px;")
        f_temp.addRow("Rango Térmico:", self.lbl_t_ext_range)

        self.chk_custom_temp = QCheckBox("Personalizar Temperatura Ambiente Manual")
        self.chk_custom_temp.toggled.connect(self._on_custom_temp_toggled)
        f_temp.addRow(self.chk_custom_temp)

        self.spin_custom_temp = QDoubleSpinBox()
        self.spin_custom_temp.setRange(5.0, 55.0)
        self.spin_custom_temp.setValue(self.current_city.summer_t_max)
        self.spin_custom_temp.setSuffix(" °C")
        self.spin_custom_temp.setEnabled(False)
        self.spin_custom_temp.valueChanged.connect(self.run_simulation)
        f_temp.addRow("T. Ambiente Base:", self.spin_custom_temp)

        form.addRow(box_temp)

        self.tabs.addTab(w, "☀️ Clima")

    def _on_custom_temp_toggled(self, checked: bool):
        self.spin_custom_temp.setEnabled(checked)
        self.run_simulation()

    def _on_eolic_toggled(self, checked: bool):
        if hasattr(self, "spin_wind_turbines"):
            pass
        if hasattr(self, "combo_wind_dia"):
            self.combo_wind_dia.setEnabled(checked)
        if hasattr(self, "combo_eolic_preset"):
            self.combo_eolic_preset.setEnabled(checked)
        if hasattr(self, "slider_eolic_pos"):
            self.slider_eolic_pos.setEnabled(checked)
        if hasattr(self, "spin_eolic_x"):
            self.spin_eolic_x.setEnabled(checked)
            self.spin_eolic_y.setEnabled(checked)
            self.spin_eolic_z.setEnabled(checked)
        self._on_equipment_pos_changed()
        self.run_simulation()

    def _build_tab_occupancy(self):
        w = QWidget()
        form = QFormLayout(w)

        lbl_desc = QLabel("Cálculo de Carga Térmica Interna y Ganancia por Ocupación (Norma EM.110 / ASHRAE 55):")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #90a4ae; font-size: 10.5px; margin-bottom: 6px;")
        form.addRow(lbl_desc)

        box_occ = QGroupBox("Ocupación Humana")
        f_occ = QFormLayout(box_occ)

        self.spin_occ_l1 = QSpinBox()
        self.spin_occ_l1.setRange(0, 500)
        self.spin_occ_l1.setValue(15)
        self.spin_occ_l1.valueChanged.connect(self.run_simulation)
        f_occ.addRow("Personas Nivel 1 (Platea):", self._create_stepper(self.spin_occ_l1))

        self.spin_occ_l2 = QSpinBox()
        self.spin_occ_l2.setRange(0, 500)
        self.spin_occ_l2.setValue(15)
        self.spin_occ_l2.valueChanged.connect(self.run_simulation)
        f_occ.addRow("Personas Nivel 2 (Mezzanine):", self._create_stepper(self.spin_occ_l2))

        self.combo_occ_activity = QComboBox()
        self.combo_occ_activity.addItems([
            "🎭 Auditorio / Espectadores sentados (100 W / persona)",
            "🎤 Auditorio / Evento de pie o dinámico (140 W / persona)",
            "🛋️ Reposo / Vivienda (75 W / persona)",
            "💼 Oficina / Trabajo ligero (100 W / persona)",
            "🏋️ Actividad moderada / Comercio (130 W / persona)",
            "🏃 Gimnasio / Intensa (180 W / persona)"
        ])
        self.combo_occ_activity.setCurrentIndex(0)
        self.combo_occ_activity.currentIndexChanged.connect(self.run_simulation)
        f_occ.addRow("Nivel de Actividad:", self.combo_occ_activity)
        form.addRow(box_occ)

        box_equip = QGroupBox("Iluminación y Equipamiento Eléctrico")
        f_eq = QFormLayout(box_equip)

        self.spin_equip_w = QDoubleSpinBox()
        self.spin_equip_w.setRange(0.0, 10000.0)
        self.spin_equip_w.setValue(200.0)
        self.spin_equip_w.setSingleStep(50.0)
        self.spin_equip_w.setSuffix(" W")
        self.spin_equip_w.valueChanged.connect(self.run_simulation)
        f_eq.addRow("Potencia Artefactos / Ilum.:", self._create_stepper(self.spin_equip_w))
        form.addRow(box_equip)

        # Resumen de Carga Interna
        box_res = QGroupBox("Impacto Térmico por Ocupación")
        f_res = QFormLayout(box_res)
        self.lbl_occ_power = QLabel("Calor Humano Total: 400 W")
        self.lbl_occ_power.setStyleSheet("color: #ffb74d; font-weight: bold; font-size: 11px;")
        f_res.addRow(self.lbl_occ_power)

        self.lbl_occ_dt = QLabel("Incremento Térmico Estimado: +0.6 °C")
        self.lbl_occ_dt.setStyleSheet("color: #ff5252; font-weight: bold; font-size: 12px;")
        f_res.addRow(self.lbl_occ_dt)
        form.addRow(box_res)

        self.tabs.addTab(w, "👥 Ocupación")

    def _build_tab_geometry(self):
        w = QWidget()
        form = QFormLayout(w)

        self.spin_floors = QSpinBox()
        self.spin_floors.setRange(1, 2)
        self.spin_floors.setValue(2)
        self.spin_floors.valueChanged.connect(self._on_geometry_changed)
        form.addRow("Número de Pisos:", self.spin_floors)

        self.spin_length = QDoubleSpinBox()
        self.spin_length.setRange(2.0, 50.0)
        self.spin_length.setValue(8.0)
        self.spin_length.setSuffix(" m")
        self.spin_length.valueChanged.connect(self._on_geometry_changed)
        form.addRow("Largo:", self.spin_length)

        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(2.0, 50.0)
        self.spin_width.setValue(5.0)
        self.spin_width.setSuffix(" m")
        self.spin_width.valueChanged.connect(self._on_geometry_changed)
        form.addRow("Ancho:", self.spin_width)

        self.spin_height_piso = QDoubleSpinBox()
        self.spin_height_piso.setRange(2.0, 6.0)
        self.spin_height_piso.setValue(2.8)
        self.spin_height_piso.setSuffix(" m")
        self.spin_height_piso.valueChanged.connect(self._on_geometry_changed)
        form.addRow("Altura por Piso:", self.spin_height_piso)

        # Muros vecinos colindantes (sombras)
        box_obs = QGroupBox("Muros / Edificaciones Vecinas (Sombra)")
        obs_form = QFormLayout(box_obs)

        self.spin_obs_east = QDoubleSpinBox()
        self.spin_obs_east.setRange(0.0, 20.0)
        self.spin_obs_east.setValue(6.0)
        self.spin_obs_east.setSuffix(" m")
        self.spin_obs_east.valueChanged.connect(self._on_geometry_changed)
        obs_form.addRow("Altura Muro Vecino Este:", self.spin_obs_east)

        self.spin_obs_west = QDoubleSpinBox()
        self.spin_obs_west.setRange(0.0, 20.0)
        self.spin_obs_west.setValue(5.0)
        self.spin_obs_west.setSuffix(" m")
        self.spin_obs_west.valueChanged.connect(self._on_geometry_changed)
        obs_form.addRow("Altura Muro Vecino Oeste:", self.spin_obs_west)

        form.addRow(box_obs)
        self.tabs.addTab(w, "🌐 Entorno")

    def _build_tab_inspector(self):
        w = QWidget()
        ly = QVBoxLayout(w)

        lbl_info = QLabel("Inspector de Planos: selecciona un componente para resaltarlo en el 3D, asignarle su material y definir su espesor:")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        ly.addWidget(lbl_info)

        # 1. Selector de componentes / caras
        self.combo_components = QComboBox()
        self.combo_components.currentIndexChanged.connect(self._on_component_combo_changed)
        ly.addWidget(self.combo_components)

        # Botones de asignación rápida de rol
        btn_role_layout = QHBoxLayout()
        btn_make_n1 = QPushButton("🟦 Muro N1")
        btn_make_n1.setToolTip("Marcar como muro de la Casa en Nivel 1")
        btn_make_n1.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; padding: 4px;")
        btn_make_n1.clicked.connect(lambda: self._quick_set_role("wall", 1))

        btn_make_n2 = QPushButton("🟥 Muro N2")
        btn_make_n2.setToolTip("Marcar como muro de la Casa en Nivel 2")
        btn_make_n2.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 4px;")
        btn_make_n2.clicked.connect(lambda: self._quick_set_role("wall", 2))

        btn_make_window = QPushButton("🪟 Ventana")
        btn_make_window.setToolTip("Marcar la superficie seleccionada como Ventana acristalada")
        btn_make_window.setStyleSheet("background-color: #00838f; color: white; font-weight: bold; padding: 4px;")
        btn_make_window.clicked.connect(lambda: self._quick_set_role("window", 1))

        btn_make_neighbor = QPushButton("⬜ Vecino")
        btn_make_neighbor.setToolTip("Marcar como Obstáculo Vecino (solo proyecta sombra)")
        btn_make_neighbor.setStyleSheet("background-color: #455a64; color: white; font-weight: bold; padding: 4px;")
        btn_make_neighbor.clicked.connect(lambda: self._quick_set_role("neighbor_wall", 0))

        btn_role_layout.addWidget(btn_make_n1)
        btn_role_layout.addWidget(btn_make_n2)
        btn_role_layout.addWidget(btn_make_window)
        btn_role_layout.addWidget(btn_make_neighbor)
        ly.addLayout(btn_role_layout)

        # Botón para insertar ventana en vano si vino vacía de SketchUp
        btn_insert_win = QPushButton("➕ Insertar Ventana en Vano de Fachada...")
        btn_insert_win.setStyleSheet("background-color: #0097a7; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        btn_insert_win.setToolTip("Inserta un paño de ventana con vidrio y marco en cualquier vano o fachada del modelo")
        btn_insert_win.clicked.connect(self._open_insert_window_dialog)
        ly.addWidget(btn_insert_win)

        # 2. Grupo de propiedades de la cara seleccionada
        box_prop = QGroupBox("Propiedades del Componente")
        f = QFormLayout(box_prop)

        self.lbl_comp_area = QLabel("-- m²")
        self.lbl_comp_area.setStyleSheet("font-weight: bold; color: #ffffff;")
        f.addRow("Área Calculada:", self.lbl_comp_area)

        self.lbl_comp_orient = QLabel("--")
        self.lbl_comp_orient.setStyleSheet("font-weight: bold; color: #88c0d0;")
        f.addRow("Orientación Solar:", self.lbl_comp_orient)

        # Rol de la superficie
        self.combo_comp_type = QComboBox()
        self.combo_comp_type.addItems(["Muro Nivel 1", "Muro Nivel 2", "Techo / Cubierta", "Ventana", "Edificio Vecino (Sombra)"])
        self.combo_comp_type.currentIndexChanged.connect(self._on_comp_type_changed)
        f.addRow("Función Térmica:", self.combo_comp_type)

        # Material asignado
        self.combo_comp_mat = QComboBox()
        self._populate_material_combo()
        self.combo_comp_mat.currentIndexChanged.connect(self._on_comp_mat_changed)
        f.addRow("Material:", self.combo_comp_mat)

        # Espesor asignado en cm
        self.spin_comp_thickness = QDoubleSpinBox()
        self.spin_comp_thickness.setRange(0.1, 100.0)
        self.spin_comp_thickness.setValue(15.0)
        self.spin_comp_thickness.setSuffix(" cm")
        self.spin_comp_thickness.valueChanged.connect(self._on_comp_thickness_changed)
        f.addRow("Espesor:", self.spin_comp_thickness)

        self.lbl_comp_u = QLabel("U = -- W/m²K")
        self.lbl_comp_u.setStyleSheet("color: #ffd700; font-weight: bold;")
        f.addRow("Transmitancia U:", self.lbl_comp_u)

        # Botón para aplicar a todas las caras similares
        self.btn_apply_all_similar = QPushButton("⚡ Aplicar este Material y Espesor a Todos los Muros/Techos")
        self.btn_apply_all_similar.setStyleSheet("background-color: #388e3c; color: white; font-weight: bold; padding: 6px;")
        self.btn_apply_all_similar.clicked.connect(self._apply_material_to_all_similar)
        f.addRow(self.btn_apply_all_similar)

        # Acciones rápidas de Edificio Vecino vs Principal
        box_role = QHBoxLayout()
        btn_mark_neighbor = QPushButton("🏢 Marcar como Edificio Vecino (Sombra)")
        btn_mark_neighbor.setStyleSheet("background-color: #455a64; color: white; font-weight: bold; padding: 5px;")
        btn_mark_neighbor.setToolTip("Convierte la superficie o volumen seleccionado en edificio colindante que solo arroja sombra")
        btn_mark_neighbor.clicked.connect(lambda: self._quick_set_role("neighbor_wall", 0))

        btn_mark_main = QPushButton("🏠 Marcar como Edificación Principal")
        btn_mark_main.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; padding: 5px;")
        btn_mark_main.setToolTip("Devuelve la superficie a la edificación de estudio")
        btn_mark_main.clicked.connect(lambda: self._quick_set_role("wall", 1))

        box_role.addWidget(btn_mark_neighbor)
        box_role.addWidget(btn_mark_main)
        f.addRow("Reclasificación Rápida:", box_role)

        ly.addWidget(box_prop)
        ly.addStretch()

        self.tabs.addTab(w, "📐 Planos")

    def _quick_set_role(self, stype: str, level: int):
        idx = self.combo_components.currentIndex()
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        if idx < 0 or idx >= len(all_surfs):
            return
        surf = all_surfs[idx]

        # Mover entre listas si cambia entre vecino y casa
        if stype == "neighbor_wall" and surf in self.viewer_3d.building_model.surfaces:
            self.viewer_3d.building_model.surfaces.remove(surf)
            self.viewer_3d.building_model.neighbor_obstacles.append(surf)
        elif stype != "neighbor_wall" and surf in self.viewer_3d.building_model.neighbor_obstacles:
            self.viewer_3d.building_model.neighbor_obstacles.remove(surf)
            self.viewer_3d.building_model.surfaces.append(surf)

        surf.surface_type = stype
        surf.level = level
        if stype == "window" and not surf.material_name:
            surf.material_name = "Vidrio Simple Claro 4 mm"
            surf.thickness_m = 0.004

        self._populate_inspector()
        self.combo_components.setCurrentIndex(min(idx, self.combo_components.count() - 1))
        self.viewer_3d.render_scene()
        self.run_simulation()
        self.statusBar().showMessage(f"Superficie '{surf.name}' reasignada a {stype} (Nivel {level})", 4000)

    def _open_insert_window_dialog(self):
        """Abre el diálogo para insertar un paño de ventana con vidrio en cualquier fachada."""
        hb = self.viewer_3d.get_house_bounds()
        dlg = AddWindowDialog(hb, self)
        if dlg.exec():
            if dlg.created_surface:
                self.viewer_3d.building_model.add_surface(dlg.created_surface)
                self._populate_inspector()
                self.viewer_3d.render_scene()
                self.run_simulation()
                self.statusBar().showMessage(f"Ventana '{dlg.created_surface.name}' ({dlg.created_surface.area_m2:.2f} m²) insertada exitosamente.", 5000)

    def _populate_material_combo(self):
        self.combo_comp_mat.clear()
        # Agregar techos
        self.combo_comp_mat.addItem("--- Techos ---")
        for k in PREDEFINED_ROOFS.keys():
            self.combo_comp_mat.addItem(f"Techo: {k}")
        # Agregar muros
        self.combo_comp_mat.addItem("--- Muros ---")
        for k in PREDEFINED_WALLS.keys():
            self.combo_comp_mat.addItem(f"Muro: {k}")
        # Agregar ventanas
        self.combo_comp_mat.addItem("--- Ventanas ---")
        for k in PREDEFINED_WINDOWS.keys():
            self.combo_comp_mat.addItem(f"Ventana: {k}")

    def _populate_inspector(self):
        self.combo_components.blockSignals(True)
        self.combo_components.clear()
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        for s in all_surfs:
            prefix = "[Vecino]" if s.surface_type == "neighbor_wall" else f"[{s.surface_type.capitalize()}]"
            self.combo_components.addItem(f"{prefix} {s.name} ({s.area_m2:.1f} m²)")
        self.combo_components.blockSignals(False)
        if all_surfs:
            self._on_component_combo_changed(0)

    def _on_component_combo_changed(self, idx: int):
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        if idx < 0 or idx >= len(all_surfs):
            return
        surf = all_surfs[idx]

        # Resaltar en 3D
        self.viewer_3d.select_surface(surf.name)

        # Actualizar formulario
        self.lbl_comp_area.setText(f"{surf.area_m2:.2f} m²")
        self.lbl_comp_orient.setText(f"{surf.orientation} (Normal: {surf.normal[0]:.2f}, {surf.normal[1]:.2f}, {surf.normal[2]:.2f})")

        self.combo_comp_type.blockSignals(True)
        if surf.surface_type == "neighbor_wall":
            self.combo_comp_type.setCurrentText("Edificio Vecino (Sombra)")
        elif surf.surface_type == "roof":
            self.combo_comp_type.setCurrentText("Techo / Cubierta")
        elif surf.surface_type == "window":
            self.combo_comp_type.setCurrentText("Ventana")
        else:
            self.combo_comp_type.setCurrentText(f"Muro Nivel {surf.level}")
        self.combo_comp_type.blockSignals(False)

        # Actualizar espesor
        self.spin_comp_thickness.blockSignals(True)
        if not getattr(surf, "material_name", ""):
            if surf.surface_type == "roof":
                surf.material_name = self.selected_roof.name
                surf.thickness_m = self.selected_roof.thickness
            elif surf.surface_type == "window":
                surf.material_name = self.selected_window.name
                surf.thickness_m = self.selected_window.thickness
            elif surf.surface_type == "floor":
                surf.material_name = self.selected_slab.name
                surf.thickness_m = self.selected_slab.thickness
            else:
                surf.material_name = self.selected_wall.name
                surf.thickness_m = self.selected_wall.thickness

        self.combo_comp_mat.blockSignals(True)
        found_idx = -1
        for i in range(self.combo_comp_mat.count()):
            txt = self.combo_comp_mat.itemText(i)
            if surf.material_name and (surf.material_name in txt or txt.endswith(surf.material_name)):
                found_idx = i
                break
        if found_idx >= 0:
            self.combo_comp_mat.setCurrentIndex(found_idx)
        self.combo_comp_mat.blockSignals(False)

        self.spin_comp_thickness.setValue(surf.thickness_m * 100.0)  # m a cm
        self.spin_comp_thickness.blockSignals(False)
        self._update_comp_u_display(surf)

    def _on_comp_type_changed(self):
        idx = self.combo_components.currentIndex()
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        if idx < 0 or idx >= len(all_surfs):
            return
        surf = all_surfs[idx]
        txt = self.combo_comp_type.currentText()
        if "Vecino" in txt:
            surf.surface_type = "neighbor_wall"
            surf.level = 0
        elif "Techo" in txt:
            surf.surface_type = "roof"
            surf.level = 2
        elif "Ventana" in txt:
            surf.surface_type = "window"
        elif "Nivel 1" in txt:
            surf.surface_type = "wall"
            surf.level = 1
        elif "Nivel 2" in txt:
            surf.surface_type = "wall"
            surf.level = 2

        self.viewer_3d.render_scene()
        self.run_simulation()

    def _on_comp_mat_changed(self):
        mat_text = self.combo_comp_mat.currentText()
        if not mat_text or mat_text.startswith("---"):
            return

        idx = self.combo_components.currentIndex()
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        if idx < 0 or idx >= len(all_surfs):
            return
        surf = all_surfs[idx]

        # Extraer nombre limpio quitando prefijos 'Techo: ', 'Muro: ', 'Ventana: '
        clean_name = mat_text.replace("Techo: ", "").replace("Muro: ", "").replace("Ventana: ", "").strip()

        # Asignar espesor típico inicial por material si aún no fue personalizado
        self.spin_comp_thickness.blockSignals(True)
        if "UPVC 2.0" in clean_name:
            self.spin_comp_thickness.setValue(0.2)   # 2 mm
        elif "UPVC 2.5" in clean_name:
            self.spin_comp_thickness.setValue(0.25)  # 2.5 mm
        elif "UPVC 3.0" in clean_name:
            self.spin_comp_thickness.setValue(0.3)   # 3 mm
        elif "Termotecho 5" in clean_name or "Termomuro 5" in clean_name:
            self.spin_comp_thickness.setValue(5.0)   # 5 cm
        elif "Termotecho 10" in clean_name or "Termomuro 10" in clean_name:
            self.spin_comp_thickness.setValue(10.0)  # 10 cm
        elif "Aluzinc" in clean_name:
            self.spin_comp_thickness.setValue(0.05)
        elif "Bloques de Concreto" in clean_name:
            self.spin_comp_thickness.setValue(14.0)  # 14 cm
        elif "King Kong" in clean_name:
            self.spin_comp_thickness.setValue(15.0)  # 15 cm
        elif "Pandereta" in clean_name:
            self.spin_comp_thickness.setValue(12.0)  # 12 cm
        self.spin_comp_thickness.blockSignals(False)

        surf.thickness_m = self.spin_comp_thickness.value() / 100.0
        surf.material_name = clean_name

        # Sincronizar con el modelo térmico global de la edificación
        self._sync_surf_material_to_global(surf)
        self._update_comp_u_display(surf)
        self.run_simulation()

    def _on_comp_thickness_changed(self):
        idx = self.combo_components.currentIndex()
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        if idx < 0 or idx >= len(all_surfs):
            return
        surf = all_surfs[idx]
        surf.thickness_m = self.spin_comp_thickness.value() / 100.0  # cm a m

        self._sync_surf_material_to_global(surf)
        self._update_comp_u_display(surf)
        self.run_simulation()

    def _sync_surf_material_to_global(self, surf):
        """Asegura que el material y espesor seleccionados en el Inspector impacten la simulación."""
        mat_name = surf.material_name
        thickness_m = surf.thickness_m

        if surf.surface_type == "roof":
            # Buscar en catálogo de techos o clonar con el nuevo espesor
            base_mat = PREDEFINED_ROOFS.get(mat_name, self.selected_roof)
            self.selected_roof = base_mat.with_thickness(thickness_m)
            self.lbl_current_roof.setText(self.selected_roof.name)
            if hasattr(self, "viewer_3d") and self.viewer_3d.building_model:
                for s in self.viewer_3d.building_model.surfaces:
                    if s.surface_type == "roof":
                        s.material_name = self.selected_roof.name
                        s.thickness_m = self.selected_roof.thickness
            self._populate_inspector()
        elif surf.surface_type == "wall":
            # Buscar en catálogo de muros o clonar con el nuevo espesor
            base_mat = PREDEFINED_WALLS.get(mat_name, self.selected_wall)
            self.selected_wall = base_mat.with_thickness(thickness_m)
            self.lbl_current_wall.setText(self.selected_wall.name)
            if hasattr(self, "viewer_3d") and self.viewer_3d.building_model:
                for s in self.viewer_3d.building_model.surfaces:
                    if s.surface_type == "wall":
                        s.material_name = self.selected_wall.name
                        s.thickness_m = self.selected_wall.thickness
            self._populate_inspector()
        elif surf.surface_type == "window":
            base_mat = PREDEFINED_WINDOWS.get(mat_name, self.selected_window)
            self.selected_window = base_mat.with_thickness(thickness_m)
            self.lbl_current_win.setText(self.selected_window.name)
            if hasattr(self, "viewer_3d") and self.viewer_3d.building_model:
                for s in self.viewer_3d.building_model.surfaces:
                    if s.surface_type == "window":
                        s.material_name = self.selected_window.name
                        s.thickness_m = self.selected_window.thickness
            self._populate_inspector()

    def _apply_material_to_all_similar(self):
        """Aplica el material y espesor actual a todas las caras de la misma categoría."""
        idx = self.combo_components.currentIndex()
        all_surfs = self.viewer_3d.building_model.surfaces + self.viewer_3d.building_model.neighbor_obstacles
        if idx < 0 or idx >= len(all_surfs):
            return
        current_surf = all_surfs[idx]
        target_type = current_surf.surface_type
        target_mat = current_surf.material_name
        target_thickness = current_surf.thickness_m

        count = 0
        for s in all_surfs:
            if s.surface_type == target_type:
                s.material_name = target_mat
                s.thickness_m = target_thickness
                count += 1

        self._sync_surf_material_to_global(current_surf)
        self.run_simulation()
        self.statusBar().showMessage(f"Material '{target_mat}' ({target_thickness*100:.1f} cm) aplicado a {count} superficies de tipo '{target_type}'.", 5000)

    def _update_comp_u_display(self, surf):
        # Calcular U directo con física real (EM.110)
        t_m = max(0.0005, surf.thickness_m)
        mat_name = surf.material_name or self.combo_comp_mat.currentText()
        clean_mat = mat_name.replace("Techo: ", "").replace("Muro: ", "").replace("Ventana: ", "").strip()

        from core.materials import ALL_MATERIALS
        base_mat = None
        for k, v in ALL_MATERIALS.items():
            if k in clean_mat or clean_mat in k:
                base_mat = v
                break

        if base_mat and base_mat.conductivity > 0:
            lam = base_mat.conductivity
        elif "Termotecho" in clean_mat or "Termomuro" in clean_mat:
            lam = 0.022
        elif "UPVC" in clean_mat:
            lam = 0.17
        elif "Fibra Mineral" in clean_mat:
            lam = 0.052
        elif "Aluzinc" in clean_mat or "Calamina" in clean_mat:
            lam = 50.0
        elif "Vidrio" in clean_mat:
            lam = 1.05
        elif "Pandereta" in clean_mat:
            lam = 0.75
        elif "King Kong" in clean_mat:
            lam = 0.85
        elif "Concreto" in clean_mat or "Losa" in clean_mat:
            lam = 1.63
        else:
            lam = 0.70

        r_mat = t_m / lam
        r_si = 0.10 if surf.surface_type == "roof" else 0.13
        r_se = 0.04
        r_tot = r_si + r_mat + r_se
        u_val = 1.0 / r_tot
        self.lbl_comp_u.setText(f"U = {u_val:.2f} W/m²K  |  R = {r_tot:.2f} m²K/W  |  λ = {lam:.3f} W/m·K")

    def _build_tab_roof_ceiling(self):
        w = QWidget()
        ly = QVBoxLayout(w)

        # 1. Cubierta Superior (Nivel 2 o Techo expuesto)
        box_roof = QGroupBox("1. Cubierta Superior (Nivel 2 - Expuesta al Sol)")
        f_roof = QFormLayout(box_roof)
        self.lbl_current_roof = QLabel(self.selected_roof.name)
        self.lbl_current_roof.setStyleSheet("font-weight: bold; color: #ffb74d;")
        f_roof.addRow("Material Techo:", self.lbl_current_roof)

        self.btn_select_roof = QPushButton("Cambiar / Personalizar Techo...")
        self.btn_select_roof.clicked.connect(self._choose_roof_material)
        f_roof.addRow(self.btn_select_roof)
        ly.addWidget(box_roof)

        # 2. Losa de Entrepiso (Techo del Nivel 1)
        box_slab = QGroupBox("2. Losa de Entrepiso (Techo del Nivel 1)")
        f_slab = QFormLayout(box_slab)
        self.lbl_current_slab = QLabel(self.selected_slab.name)
        self.lbl_current_slab.setStyleSheet("font-weight: bold; color: #90caf9;")
        f_slab.addRow("Material Losa:", self.lbl_current_slab)

        self.btn_select_slab = QPushButton("Cambiar / Personalizar Losa...")
        self.btn_select_slab.clicked.connect(self._choose_slab_material)
        f_slab.addRow(self.btn_select_slab)
        ly.addWidget(box_slab)

        # 3. Cielo Raso
        box_ceiling = QGroupBox("3. Cielo Raso (Falso Techo)")
        f_ceil = QFormLayout(box_ceiling)
        ceil_name = self.selected_ceiling.name if self.selected_ceiling else "Sin Cielo Raso"
        self.lbl_current_ceiling = QLabel(ceil_name)
        self.lbl_current_ceiling.setStyleSheet("font-weight: bold; color: #81c784;")
        f_ceil.addRow("Seleccionado:", self.lbl_current_ceiling)

        self.btn_select_ceiling = QPushButton("Cambiar / Personalizar Cielo Raso...")
        self.btn_select_ceiling.clicked.connect(self._choose_ceiling_material)
        f_ceil.addRow(self.btn_select_ceiling)

        self.chk_cavity_vent = QCheckBox("Cámara de aire ventilada (Extractores)")
        self.chk_cavity_vent.setChecked(True)
        self.chk_cavity_vent.toggled.connect(self.run_simulation)
        f_ceil.addRow(self.chk_cavity_vent)
        ly.addWidget(box_ceiling)

        # Resumen U compuesto
        self.lbl_u_roof_total = QLabel("Transmitancia Ensamble: -- W/m²K")
        self.lbl_u_roof_total.setStyleSheet("color: #ffffff; font-weight: bold; padding: 4px; background: #333344; border-radius: 4px;")
        ly.addWidget(self.lbl_u_roof_total)
        ly.addStretch()

        self.tabs.addTab(w, "🏠 Techo")

    def _build_tab_walls(self):
        w = QWidget()
        ly = QVBoxLayout(w)

        # Muros
        box_wall = QGroupBox("Material de Muros Perimetrales")
        f_wall = QFormLayout(box_wall)
        self.lbl_current_wall = QLabel(self.selected_wall.name)
        self.lbl_current_wall.setStyleSheet("font-weight: bold; color: #64b5f6;")
        f_wall.addRow("Muro Actual:", self.lbl_current_wall)

        self.btn_select_wall = QPushButton("Cambiar / Personalizar Muro...")
        self.btn_select_wall.clicked.connect(self._choose_wall_material)
        f_wall.addRow(self.btn_select_wall)
        ly.addWidget(box_wall)

        # Ventanas
        box_win = QGroupBox("Acristalamiento de Ventanas")
        f_win = QFormLayout(box_win)
        self.lbl_current_win = QLabel(self.selected_window.name)
        self.lbl_current_win.setStyleSheet("font-weight: bold; color: #4dd0e1;")
        f_win.addRow("Vidrio Actual:", self.lbl_current_win)

        self.btn_select_win = QPushButton("Cambiar / Personalizar Vidrio...")
        self.btn_select_win.clicked.connect(self._choose_window_material)
        f_win.addRow(self.btn_select_win)

        # Botón directo para insertar ventana en vano
        btn_add_win_fachada = QPushButton("➕ Insertar Paño de Ventana con Vidrio en Fachada...")
        btn_add_win_fachada.setFixedHeight(34)
        btn_add_win_fachada.setStyleSheet("background-color: #00838f; color: white; font-weight: bold; border-radius: 4px;")
        btn_add_win_fachada.setToolTip("Insertar un paño de vidrio (ventana corrediza/fija) en cualquier vano o muro")
        btn_add_win_fachada.clicked.connect(self._open_insert_window_dialog)
        f_win.addRow("", btn_add_win_fachada)

        ly.addWidget(box_win)

        # 3. Ventilación Natural: Apertura de Ventanas y Puertas (0 a 50%)
        box_open = QGroupBox("Ventilación Natural: Apertura de Ventanas y Puertas")
        f_open = QFormLayout(box_open)

        self.lbl_open_val = QLabel("0% (Completamente Cerradas)")
        self.lbl_open_val.setStyleSheet("font-weight: bold; color: #ffeb3b; font-size: 12px;")
        f_open.addRow("Área Útil Abierta:", self.lbl_open_val)

        self.slider_window_open = QSlider(Qt.Orientation.Horizontal)
        self.slider_window_open.setRange(0, 50)
        self.slider_window_open.setValue(0)
        self.slider_window_open.setTickInterval(10)
        self.slider_window_open.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_window_open.valueChanged.connect(self._on_window_open_changed)
        f_open.addRow(self.slider_window_open)

        lbl_open_hint = QLabel("Rango: 0% a 50% de área útil libre (ventanas corredizas, abatibles, mamparas y puertas).")
        lbl_open_hint.setStyleSheet("color: #888899; font-size: 10px;")
        lbl_open_hint.setWordWrap(True)
        f_open.addRow(lbl_open_hint)
        ly.addWidget(box_open)

        ly.addStretch()
        self.tabs.addTab(w, "🧱 Fachadas")

    def _build_tab_hvac(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_hvac = scroll

        w = QWidget()
        ly = QVBoxLayout(w)

        # -------------------------------------------------------------
        # 1. EXTRACTORES EÓLICOS EN TECHO (TURBINAS GIRATORIAS)
        # -------------------------------------------------------------
        box_wind = QGroupBox("1. Extractores Eólicos en Techo (Turbinas Giratorias)")
        f_wind = QFormLayout(box_wind)

        self.chk_eolic = QCheckBox("Activar Extractores Eólicos en Techo")
        self.chk_eolic.setChecked(True)
        self.chk_eolic.toggled.connect(self._on_eolic_toggled)
        self.chk_eolic.toggled.connect(self.run_simulation)
        f_wind.addRow(self.chk_eolic)

        # Barra de selección y gestión individual de turbinas
        bar_eolic = QHBoxLayout()
        self.combo_eolic_select = QComboBox()
        self.combo_eolic_select.currentIndexChanged.connect(self._on_eolic_selected)
        btn_add_eolic = QPushButton("＋ Añadir")
        btn_add_eolic.setToolTip("Añadir otra turbina eólica en el techo")
        btn_add_eolic.setStyleSheet("QPushButton { background-color: #1b5e20; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #2e7d32; }")
        btn_add_eolic.clicked.connect(self._add_eolic_unit)
        btn_del_eolic = QPushButton("🗑️ Retirar")
        btn_del_eolic.setToolTip("Eliminar la turbina seleccionada")
        btn_del_eolic.setStyleSheet("QPushButton { background-color: #7f0000; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #b71c1c; }")
        btn_del_eolic.clicked.connect(self._remove_eolic_unit)
        bar_eolic.addWidget(self.combo_eolic_select, stretch=3)
        bar_eolic.addWidget(btn_add_eolic, stretch=1)
        bar_eolic.addWidget(btn_del_eolic, stretch=1)
        f_wind.addRow("Unidad Eólica:", bar_eolic)

        self.chk_curr_eolic = QCheckBox("Activar esta turbina seleccionada")
        self.chk_curr_eolic.setChecked(True)
        self.chk_curr_eolic.toggled.connect(self._on_curr_eolic_param_changed)
        f_wind.addRow(self.chk_curr_eolic)

        self.combo_wind_dia = QComboBox()
        self.combo_wind_dia.addItems(["14 pulgadas (35 cm)", "20 pulgadas (50 cm)", "24 pulgadas (60 cm)", "30 pulgadas (75 cm)"])
        self.combo_wind_dia.setCurrentText("24 pulgadas (60 cm)")
        self.combo_wind_dia.currentIndexChanged.connect(self._on_curr_eolic_param_changed)
        f_wind.addRow("Diámetro de Garganta:", self.combo_wind_dia)

        self.combo_eolic_preset = QComboBox()
        self.combo_eolic_preset.addItems([
            "📍 Cumbrera Central (Punto más alto)",
            "📍 Faldón Frontal (Hacia frontis Sur)",
            "📍 Faldón Posterior (Hacia patio Norte)",
            "📍 Lado Lateral Este (Faldón Este)",
            "📍 Lado Lateral Oeste (Faldón Oeste)",
            "⚙️ Personalizado (Coordenadas libres)"
        ])
        self.combo_eolic_preset.currentIndexChanged.connect(self._apply_eolic_preset)
        f_wind.addRow("Ubicación Rápida:", self.combo_eolic_preset)

        self.slider_eolic_pos = QSlider(Qt.Orientation.Horizontal)
        self.slider_eolic_pos.setRange(10, 90)
        self.slider_eolic_pos.setValue(50)
        self.slider_eolic_pos.valueChanged.connect(self._apply_eolic_preset)
        self.lbl_eolic_pos = QLabel("50% a lo largo del techo")
        self.lbl_eolic_pos.setStyleSheet("color: #ffb74d; font-size: 10px;")
        f_wind.addRow("Desplazamiento Techo:", self.slider_eolic_pos)
        f_wind.addRow("", self.lbl_eolic_pos)

        eolic_pos_box = QHBoxLayout()
        self.spin_eolic_x = QDoubleSpinBox()
        self.spin_eolic_x.setRange(-50, 100)
        self.spin_eolic_x.setValue(4.0)
        self.spin_eolic_x.setPrefix("X: ")
        self.spin_eolic_x.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_eolic_y = QDoubleSpinBox()
        self.spin_eolic_y.setRange(-50, 100)
        self.spin_eolic_y.setValue(2.5)
        self.spin_eolic_y.setPrefix("Y: ")
        self.spin_eolic_y.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_eolic_z = QDoubleSpinBox()
        self.spin_eolic_z.setRange(0, 30)
        self.spin_eolic_z.setValue(5.6)
        self.spin_eolic_z.setPrefix("Z: ")
        self.spin_eolic_z.valueChanged.connect(self._on_equipment_pos_changed)
        eolic_pos_box.addWidget(self.spin_eolic_x)
        eolic_pos_box.addWidget(self.spin_eolic_y)
        eolic_pos_box.addWidget(self.spin_eolic_z)
        f_wind.addRow("Ajuste Fino 3D (m):", eolic_pos_box)

        ly.addWidget(box_wind)

        # -------------------------------------------------------------
        # 2. VENTILACIÓN MECÁNICA FORZADA (EXTRACTORES E INYECTORES)
        # -------------------------------------------------------------
        box_mech = QGroupBox("2. Ventilación Mecánica Forzada (Inyección y Extracción)")
        f_mech = QFormLayout(box_mech)

        # SUB-SECCIÓN: EXTRACTOR MECÁNICO
        self.chk_exhaust = QCheckBox("Activar Extracción Mecánica (Campanas / Ductos)")
        self.chk_exhaust.setChecked(True)
        self.chk_exhaust.toggled.connect(self._on_equipment_pos_changed)
        self.chk_exhaust.toggled.connect(self.run_simulation)
        f_mech.addRow(self.chk_exhaust)

        bar_exh = QHBoxLayout()
        self.combo_exhaust_select = QComboBox()
        self.combo_exhaust_select.currentIndexChanged.connect(self._on_exhaust_selected)
        btn_add_exh = QPushButton("＋ Añadir")
        btn_add_exh.setToolTip("Añadir otro punto de extracción individual")
        btn_add_exh.setStyleSheet("QPushButton { background-color: #1b5e20; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #2e7d32; }")
        btn_add_exh.clicked.connect(self._add_exhaust_unit)
        btn_del_exh = QPushButton("🗑️ Retirar")
        btn_del_exh.setToolTip("Eliminar el extractor seleccionado")
        btn_del_exh.setStyleSheet("QPushButton { background-color: #7f0000; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #b71c1c; }")
        btn_del_exh.clicked.connect(self._remove_exhaust_unit)
        bar_exh.addWidget(self.combo_exhaust_select, stretch=3)
        bar_exh.addWidget(btn_add_exh, stretch=1)
        bar_exh.addWidget(btn_del_exh, stretch=1)
        f_mech.addRow("Punto Extractor:", bar_exh)

        self.chk_curr_exhaust = QCheckBox("Activar este extractor seleccionado")
        self.chk_curr_exhaust.setChecked(True)
        self.chk_curr_exhaust.toggled.connect(self._on_curr_exhaust_param_changed)
        f_mech.addRow(self.chk_curr_exhaust)

        self.combo_curr_exhaust_level = QComboBox()
        self.combo_curr_exhaust_level.addItems(["Nivel 1 (Platea / Sala)", "Nivel 2 (Mezzanine / Planta Alta)"])
        self.combo_curr_exhaust_level.currentIndexChanged.connect(self._apply_exhaust_preset)
        self.combo_curr_exhaust_level.currentIndexChanged.connect(self.run_simulation)
        f_mech.addRow("Nivel de Extracción:", self.combo_curr_exhaust_level)

        self.combo_exhaust_preset = QComboBox()
        self.combo_exhaust_preset.addItems([
            "📍 Pared Norte (Posterior)",
            "📍 Pared Sur (Frontal)",
            "📍 Pared Lateral Este",
            "📍 Pared Lateral Oeste",
            "📍 Techo / Salida Superior",
            "⚙️ Personalizado (Coordenadas libres)"
        ])
        self.combo_exhaust_preset.currentIndexChanged.connect(self._apply_exhaust_preset)
        f_mech.addRow("Pared / Ubicación:", self.combo_exhaust_preset)

        self.slider_exhaust_pos = QSlider(Qt.Orientation.Horizontal)
        self.slider_exhaust_pos.setRange(10, 90)
        self.slider_exhaust_pos.setValue(50)
        self.slider_exhaust_pos.valueChanged.connect(self._apply_exhaust_preset)
        self.lbl_exhaust_pos = QLabel("50% a lo largo de la pared")
        self.lbl_exhaust_pos.setStyleSheet("color: #ff9800; font-size: 10px;")
        f_mech.addRow("Posición en Pared:", self.slider_exhaust_pos)
        f_mech.addRow("", self.lbl_exhaust_pos)

        self.spin_exhaust_flow = QDoubleSpinBox()
        self.spin_exhaust_flow.setRange(100.0, 15000.0)
        self.spin_exhaust_flow.setValue(1200.0)
        self.spin_exhaust_flow.setSingleStep(100.0)
        self.spin_exhaust_flow.setSuffix(" m³/h")
        self.spin_exhaust_flow.valueChanged.connect(self._on_curr_exhaust_param_changed)
        f_mech.addRow("Caudal Extractor:", self._create_stepper(self.spin_exhaust_flow))

        exh_pos_box = QHBoxLayout()
        self.spin_exhaust_x = QDoubleSpinBox()
        self.spin_exhaust_x.setRange(-50, 100)
        self.spin_exhaust_x.setValue(4.0)
        self.spin_exhaust_x.setPrefix("X: ")
        self.spin_exhaust_x.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_exhaust_y = QDoubleSpinBox()
        self.spin_exhaust_y.setRange(-50, 100)
        self.spin_exhaust_y.setValue(4.85)
        self.spin_exhaust_y.setPrefix("Y: ")
        self.spin_exhaust_y.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_exhaust_z = QDoubleSpinBox()
        self.spin_exhaust_z.setRange(0, 30)
        self.spin_exhaust_z.setValue(2.4)
        self.spin_exhaust_z.setPrefix("Z: ")
        self.spin_exhaust_z.valueChanged.connect(self._on_equipment_pos_changed)
        exh_pos_box.addWidget(self.spin_exhaust_x)
        exh_pos_box.addWidget(self.spin_exhaust_y)
        exh_pos_box.addWidget(self.spin_exhaust_z)
        f_mech.addRow("Ajuste Fino 3D (m):", exh_pos_box)

        # SUB-SECCIÓN: INYECTOR DE AIRE EXTERIOR
        f_mech.addRow(QLabel("──────────────────────────────────────"))
        self.chk_supply = QCheckBox("Activar Inyección de Aire Exterior (Presurización)")
        self.chk_supply.setChecked(True)
        self.chk_supply.toggled.connect(self._on_equipment_pos_changed)
        self.chk_supply.toggled.connect(self.run_simulation)
        f_mech.addRow(self.chk_supply)

        bar_sup = QHBoxLayout()
        self.combo_supply_select = QComboBox()
        self.combo_supply_select.currentIndexChanged.connect(self._on_supply_selected)
        btn_add_sup = QPushButton("＋ Añadir")
        btn_add_sup.setToolTip("Añadir otro punto de inyección exterior individual")
        btn_add_sup.setStyleSheet("QPushButton { background-color: #1b5e20; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #2e7d32; }")
        btn_add_sup.clicked.connect(self._add_supply_unit)
        btn_del_sup = QPushButton("🗑️ Retirar")
        btn_del_sup.setToolTip("Eliminar el inyector seleccionado")
        btn_del_sup.setStyleSheet("QPushButton { background-color: #7f0000; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #b71c1c; }")
        btn_del_sup.clicked.connect(self._remove_supply_unit)
        bar_sup.addWidget(self.combo_supply_select, stretch=3)
        bar_sup.addWidget(btn_add_sup, stretch=1)
        bar_sup.addWidget(btn_del_sup, stretch=1)
        f_mech.addRow("Punto Inyector:", bar_sup)

        self.chk_curr_supply = QCheckBox("Activar este inyector seleccionado")
        self.chk_curr_supply.setChecked(True)
        self.chk_curr_supply.toggled.connect(self._on_curr_supply_param_changed)
        f_mech.addRow(self.chk_curr_supply)

        self.combo_curr_supply_level = QComboBox()
        self.combo_curr_supply_level.addItems(["Nivel 1 (Platea / Sala)", "Nivel 2 (Mezzanine / Planta Alta)"])
        self.combo_curr_supply_level.currentIndexChanged.connect(self._apply_supply_preset)
        self.combo_curr_supply_level.currentIndexChanged.connect(self.run_simulation)
        f_mech.addRow("Nivel de Inyección:", self.combo_curr_supply_level)

        self.combo_supply_preset = QComboBox()
        self.combo_supply_preset.addItems([
            "📍 Pared Sur (Frontal)",
            "📍 Pared Norte (Posterior)",
            "📍 Pared Lateral Este",
            "📍 Pared Lateral Oeste",
            "⚙️ Personalizado (Coordenadas libres)"
        ])
        self.combo_supply_preset.currentIndexChanged.connect(self._apply_supply_preset)
        f_mech.addRow("Pared / Ubicación:", self.combo_supply_preset)

        self.slider_supply_pos = QSlider(Qt.Orientation.Horizontal)
        self.slider_supply_pos.setRange(10, 90)
        self.slider_supply_pos.setValue(50)
        self.slider_supply_pos.valueChanged.connect(self._apply_supply_preset)
        self.lbl_supply_pos = QLabel("50% a lo largo de la pared")
        self.lbl_supply_pos.setStyleSheet("color: #03a9f4; font-size: 10px;")
        f_mech.addRow("Posición en Pared:", self.slider_supply_pos)
        f_mech.addRow("", self.lbl_supply_pos)

        self.spin_supply_flow = QDoubleSpinBox()
        self.spin_supply_flow.setRange(100.0, 15000.0)
        self.spin_supply_flow.setValue(1200.0)
        self.spin_supply_flow.setSingleStep(100.0)
        self.spin_supply_flow.setSuffix(" m³/h")
        self.spin_supply_flow.valueChanged.connect(self._on_curr_supply_param_changed)
        f_mech.addRow("Caudal Inyector:", self._create_stepper(self.spin_supply_flow))
        self.combo_supply_source = QComboBox()
        self.combo_supply_source.addItems([
            "☀️ Calle / Fachada Soleada (T. Exterior)",
            "🌳 Patio Sombreado / Área Verde (-2.5 °C)",
            "🌿 Retiro Protegido / Sombra Fresca (-3.5 °C)",
            "❄️ Pozo Canadiense / Subterráneo (-5.0 °C)"
        ])
        self.combo_supply_source.currentIndexChanged.connect(self._on_curr_supply_param_changed)
        f_mech.addRow("Origen Aire Inyectado:", self.combo_supply_source)

        sup_pos_box = QHBoxLayout()
        self.spin_supply_x = QDoubleSpinBox()
        self.spin_supply_x.setRange(-50, 100)
        self.spin_supply_x.setValue(4.0)
        self.spin_supply_x.setPrefix("X: ")
        self.spin_supply_x.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_supply_y = QDoubleSpinBox()
        self.spin_supply_y.setRange(-50, 100)
        self.spin_supply_y.setValue(0.15)
        self.spin_supply_y.setPrefix("Y: ")
        self.spin_supply_y.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_supply_z = QDoubleSpinBox()
        self.spin_supply_z.setRange(0, 30)
        self.spin_supply_z.setValue(2.0)
        self.spin_supply_z.setPrefix("Z: ")
        self.spin_supply_z.valueChanged.connect(self._on_equipment_pos_changed)
        sup_pos_box.addWidget(self.spin_supply_x)
        sup_pos_box.addWidget(self.spin_supply_y)
        sup_pos_box.addWidget(self.spin_supply_z)
        f_mech.addRow("Ajuste Fino 3D (m):", sup_pos_box)

        ly.addWidget(box_mech)

        # -------------------------------------------------------------
        # 3. VENTILADORES DE CONFORT (SENSACIÓN DE BRISA ASHRAE 55)
        # -------------------------------------------------------------
        box_fan = QGroupBox("3. Ventilador Interior de Confort (Sensación de Brisa ASHRAE 55)")
        f_fan = QFormLayout(box_fan)

        self.chk_fan = QCheckBox("Activar Ventilador de Techo / Pedestal")
        self.chk_fan.setChecked(True)
        self.chk_fan.toggled.connect(self._on_equipment_pos_changed)
        self.chk_fan.toggled.connect(self.run_simulation)
        f_fan.addRow(self.chk_fan)

        bar_fan = QHBoxLayout()
        self.combo_fan_select = QComboBox()
        self.combo_fan_select.currentIndexChanged.connect(self._on_fan_selected)
        btn_add_fan = QPushButton("＋ Añadir")
        btn_add_fan.setToolTip("Añadir otro ventilador individual")
        btn_add_fan.setStyleSheet("QPushButton { background-color: #1b5e20; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #2e7d32; }")
        btn_add_fan.clicked.connect(self._add_fan_unit)
        btn_del_fan = QPushButton("🗑️ Retirar")
        btn_del_fan.setToolTip("Eliminar el ventilador seleccionado")
        btn_del_fan.setStyleSheet("QPushButton { background-color: #7f0000; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #b71c1c; }")
        btn_del_fan.clicked.connect(self._remove_fan_unit)
        bar_fan.addWidget(self.combo_fan_select, stretch=3)
        bar_fan.addWidget(btn_add_fan, stretch=1)
        bar_fan.addWidget(btn_del_fan, stretch=1)
        f_fan.addRow("Unidad Ventilador:", bar_fan)

        self.chk_curr_fan = QCheckBox("Activar este ventilador seleccionado")
        self.chk_curr_fan.setChecked(True)
        self.chk_curr_fan.toggled.connect(self._on_curr_fan_param_changed)
        f_fan.addRow(self.chk_curr_fan)

        self.combo_curr_fan_level = QComboBox()
        self.combo_curr_fan_level.addItems(["Nivel 1 (Platea / Sala)", "Nivel 2 (Mezzanine / Planta Alta)"])
        self.combo_curr_fan_level.currentIndexChanged.connect(self._apply_fan_preset)
        self.combo_curr_fan_level.currentIndexChanged.connect(self.run_simulation)
        f_fan.addRow("Nivel de Ubicación:", self.combo_curr_fan_level)

        self.combo_fan_mount = QComboBox()
        self.combo_fan_mount.addItems([
            "Techo (Cono descendente sobre ocupantes - 100% efectividad)",
            "Pared Alta / Mural (Chorro longitudinal a distancia - 88% efectividad)",
            "Pedestal / Suelo (Brisa horizontal directa - 95% efectividad)"
        ])
        self.combo_fan_mount.currentIndexChanged.connect(self._on_curr_fan_param_changed)
        f_fan.addRow("Tipo de Montaje:", self.combo_fan_mount)

        self.combo_fan_spd = QComboBox()
        self.combo_fan_spd.addItems([
            "Baja (0.5 m/s - Brisa Suave)",
            "Media (1.0 m/s - Confort Típico)",
            "Alta (1.8 m/s - Máximo Alivio)",
            "Industrial / HVLS (2.4 m/s)",
            "⚙️ Personalizado (Dato de Fabricante)"
        ])
        self.combo_fan_spd.setCurrentText("Media (1.0 m/s - Confort Típico)")
        self.combo_fan_spd.currentIndexChanged.connect(self._on_curr_fan_spd_preset_changed)
        f_fan.addRow("Régimen de Flujo:", self.combo_fan_spd)

        fan_data_box = QHBoxLayout()
        self.spin_fan_speed_custom = QDoubleSpinBox()
        self.spin_fan_speed_custom.setRange(0.1, 5.0)
        self.spin_fan_speed_custom.setValue(1.0)
        self.spin_fan_speed_custom.setSingleStep(0.1)
        self.spin_fan_speed_custom.setPrefix("Vel: ")
        self.spin_fan_speed_custom.setSuffix(" m/s")
        self.spin_fan_speed_custom.valueChanged.connect(self._on_curr_fan_param_changed)

        self.spin_fan_power_w = QDoubleSpinBox()
        self.spin_fan_power_w.setRange(10.0, 600.0)
        self.spin_fan_power_w.setValue(75.0)
        self.spin_fan_power_w.setSingleStep(5.0)
        self.spin_fan_power_w.setPrefix("Pot: ")
        self.spin_fan_power_w.setSuffix(" W")
        self.spin_fan_power_w.valueChanged.connect(self._on_curr_fan_param_changed)

        fan_data_box.addWidget(self.spin_fan_speed_custom)
        fan_data_box.addWidget(self.spin_fan_power_w)
        f_fan.addRow("Datos Fabricante:", fan_data_box)

        self.lbl_fan_relief = QLabel("❄️ Alivio Térmico ASHRAE 55: -1.9 °C aparente")
        self.lbl_fan_relief.setStyleSheet("color: #81c784; font-weight: bold; font-size: 11px;")
        f_fan.addRow("", self.lbl_fan_relief)

        self.combo_fan_preset = QComboBox()
        self.combo_fan_preset.addItems([
            "📍 Centro Habitación",
            "📍 Mitad Frontal (Ventanas)",
            "📍 Mitad Posterior (Patio)",
            "⚙️ Personalizado (Coordenadas libres)"
        ])
        self.combo_fan_preset.currentIndexChanged.connect(self._apply_fan_preset)
        f_fan.addRow("Ubicación Rápida:", self.combo_fan_preset)

        fan_slider_layout = QHBoxLayout()
        self.slider_fan_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_fan_x.setRange(10, 90)
        self.slider_fan_x.setValue(50)
        self.slider_fan_x.valueChanged.connect(self._apply_fan_preset)
        self.slider_fan_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_fan_y.setRange(10, 90)
        self.slider_fan_y.setValue(50)
        self.slider_fan_y.valueChanged.connect(self._apply_fan_preset)
        fan_slider_layout.addWidget(QLabel("X:"))
        fan_slider_layout.addWidget(self.slider_fan_x)
        fan_slider_layout.addWidget(QLabel("Y:"))
        fan_slider_layout.addWidget(self.slider_fan_y)
        f_fan.addRow("Posición en Planta:", fan_slider_layout)

        fan_pos_box = QHBoxLayout()
        self.spin_fan_x = QDoubleSpinBox()
        self.spin_fan_x.setRange(-50, 100)
        self.spin_fan_x.setValue(4.0)
        self.spin_fan_x.setPrefix("X: ")
        self.spin_fan_x.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_fan_y = QDoubleSpinBox()
        self.spin_fan_y.setRange(-50, 100)
        self.spin_fan_y.setValue(2.5)
        self.spin_fan_y.setPrefix("Y: ")
        self.spin_fan_y.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_fan_z = QDoubleSpinBox()
        self.spin_fan_z.setRange(0, 30)
        self.spin_fan_z.setValue(2.6)
        self.spin_fan_z.setPrefix("Z: ")
        self.spin_fan_z.valueChanged.connect(self._on_equipment_pos_changed)
        fan_pos_box.addWidget(self.spin_fan_x)
        fan_pos_box.addWidget(self.spin_fan_y)
        fan_pos_box.addWidget(self.spin_fan_z)
        f_fan.addRow("Ajuste Fino 3D (m):", fan_pos_box)

        ly.addWidget(box_fan)

        # -------------------------------------------------------------
        # 4. AIRE ACONDICIONADO SPLIT (CLIMATIZACIÓN ACTIVA)
        # -------------------------------------------------------------
        box_ac = QGroupBox("4. Aire Acondicionado Split (Climatización Activa)")
        f_ac = QFormLayout(box_ac)

        self.chk_ac = QCheckBox("Activar Climatización A/C Split")
        self.chk_ac.setChecked(False)
        self.chk_ac.toggled.connect(self._on_equipment_pos_changed)
        self.chk_ac.toggled.connect(self.run_simulation)
        f_ac.addRow(self.chk_ac)

        bar_ac = QHBoxLayout()
        self.combo_ac_select = QComboBox()
        self.combo_ac_select.currentIndexChanged.connect(self._on_ac_selected)
        btn_add_ac = QPushButton("＋ Añadir")
        btn_add_ac.setToolTip("Añadir otra unidad de A/C Split individual")
        btn_add_ac.setStyleSheet("QPushButton { background-color: #1b5e20; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #2e7d32; }")
        btn_add_ac.clicked.connect(self._add_ac_unit)
        btn_del_ac = QPushButton("🗑️ Retirar")
        btn_del_ac.setToolTip("Eliminar la unidad A/C seleccionada")
        btn_del_ac.setStyleSheet("QPushButton { background-color: #7f0000; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #b71c1c; }")
        btn_del_ac.clicked.connect(self._remove_ac_unit)
        bar_ac.addWidget(self.combo_ac_select, stretch=3)
        bar_ac.addWidget(btn_add_ac, stretch=1)
        bar_ac.addWidget(btn_del_ac, stretch=1)
        f_ac.addRow("Unidad Split:", bar_ac)

        self.chk_curr_ac = QCheckBox("Activar esta unidad A/C seleccionada")
        self.chk_curr_ac.setChecked(True)
        self.chk_curr_ac.toggled.connect(self._on_curr_ac_param_changed)
        f_ac.addRow(self.chk_curr_ac)

        self.combo_curr_ac_level = QComboBox()
        self.combo_curr_ac_level.addItems(["Nivel 1 (Platea / Sala)", "Nivel 2 (Mezzanine / Planta Alta)"])
        self.combo_curr_ac_level.currentIndexChanged.connect(self._apply_ac_preset)
        self.combo_curr_ac_level.currentIndexChanged.connect(self.run_simulation)
        f_ac.addRow("Nivel de Montaje:", self.combo_curr_ac_level)

        self.spin_ac_setpoint = QDoubleSpinBox()
        self.spin_ac_setpoint.setRange(16.0, 30.0)
        self.spin_ac_setpoint.setValue(24.0)
        self.spin_ac_setpoint.setSingleStep(0.5)
        self.spin_ac_setpoint.setSuffix(" °C")
        self.spin_ac_setpoint.valueChanged.connect(self._on_curr_ac_param_changed)
        f_ac.addRow("Temperatura Objetivo (Setpoint):", self._create_stepper(self.spin_ac_setpoint))

        self.combo_ac_cap = QComboBox()
        self.combo_ac_cap.addItems([
            "12,000 BTU/h (1.0 TR - Comercial)",
            "18,000 BTU/h (1.5 TR - Comercial)",
            "24,000 BTU/h (2.0 TR - Comercial Típico)",
            "36,000 BTU/h (3.0 TR - Comercial Grande)",
            "48,000 BTU/h (4.0 TR - Paquete / Techo)",
            "60,000 BTU/h (5.0 TR - Alta Capacidad)",
            "⚡ Auto-dimensionar (Cálculo Ideal sin límite)",
            "⚙️ Personalizado (Dato de Fabricante en BTU/h)"
        ])
        self.combo_ac_cap.setCurrentText("24,000 BTU/h (2.0 TR - Comercial Típico)")
        self.combo_ac_cap.currentIndexChanged.connect(self._on_curr_ac_cap_preset_changed)
        f_ac.addRow("Capacidad Frigorífica:", self.combo_ac_cap)

        ac_custom_box = QHBoxLayout()
        self.spin_ac_nominal_btu = QDoubleSpinBox()
        self.spin_ac_nominal_btu.setRange(3000.0, 500000.0)
        self.spin_ac_nominal_btu.setValue(24000.0)
        self.spin_ac_nominal_btu.setSingleStep(1000.0)
        self.spin_ac_nominal_btu.setPrefix("Cap: ")
        self.spin_ac_nominal_btu.setSuffix(" BTU/h")
        self.spin_ac_nominal_btu.valueChanged.connect(self._on_curr_ac_param_changed)

        self.combo_ac_cop = QComboBox()
        self.combo_ac_cop.addItems([
            "COP 3.2 (Inverter R410A)",
            "COP 2.8 (On/Off Convencional)",
            "COP 3.6 (Inverter A++)",
            "COP 4.0 (Ultra Inverter A+++)"
        ])
        self.combo_ac_cop.currentIndexChanged.connect(self._on_curr_ac_param_changed)
        ac_custom_box.addWidget(self.spin_ac_nominal_btu, stretch=2)
        ac_custom_box.addWidget(self.combo_ac_cop, stretch=2)
        f_ac.addRow("Potencia / Eficiencia:", ac_custom_box)

        self.lbl_ac_diag = QLabel("📊 Balance A/C: Capacidad nominal configurada")
        self.lbl_ac_diag.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 11px;")
        f_ac.addRow("", self.lbl_ac_diag)

        self.combo_ac_preset = QComboBox()
        self.combo_ac_preset.addItems([
            "📍 Pared Sur (Frontal)",
            "📍 Pared Norte (Posterior)",
            "📍 Pared Oeste (Lateral)",
            "📍 Pared Este (Lateral)",
            "📍 Centro del Ambiente",
            "⚙️ Personalizado (Coordenadas libres)"
        ])
        self.combo_ac_preset.currentIndexChanged.connect(self._apply_ac_preset)
        f_ac.addRow("Pared de Montaje:", self.combo_ac_preset)

        self.slider_ac_wall_pos = QSlider(Qt.Orientation.Horizontal)
        self.slider_ac_wall_pos.setRange(10, 90)
        self.slider_ac_wall_pos.setValue(50)
        self.slider_ac_wall_pos.valueChanged.connect(self._apply_ac_preset)
        self.lbl_ac_wall_pos = QLabel("50% a lo largo del muro")
        self.lbl_ac_wall_pos.setStyleSheet("color: #00e5ff; font-size: 10px;")
        f_ac.addRow("Posición en Muro:", self.slider_ac_wall_pos)
        f_ac.addRow("", self.lbl_ac_wall_pos)

        self.slider_ac_height = QSlider(Qt.Orientation.Horizontal)
        self.slider_ac_height.setRange(16, 28)
        self.slider_ac_height.setValue(23)
        self.slider_ac_height.valueChanged.connect(self._apply_ac_preset)
        self.lbl_ac_height = QLabel("2.3 m sobre nivel de piso terminado")
        self.lbl_ac_height.setStyleSheet("color: #00e5ff; font-size: 10px;")
        f_ac.addRow("Altura de Montaje:", self.slider_ac_height)
        f_ac.addRow("", self.lbl_ac_height)

        ac_pos_box = QHBoxLayout()
        self.spin_ac_x = QDoubleSpinBox()
        self.spin_ac_x.setRange(-50, 100)
        self.spin_ac_x.setValue(2.0)
        self.spin_ac_x.setPrefix("X: ")
        self.spin_ac_x.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_ac_y = QDoubleSpinBox()
        self.spin_ac_y.setRange(-50, 100)
        self.spin_ac_y.setValue(0.15)
        self.spin_ac_y.setPrefix("Y: ")
        self.spin_ac_y.valueChanged.connect(self._on_equipment_pos_changed)
        self.spin_ac_z = QDoubleSpinBox()
        self.spin_ac_z.setRange(0, 30)
        self.spin_ac_z.setValue(2.3)
        self.spin_ac_z.setPrefix("Z: ")
        self.spin_ac_z.valueChanged.connect(self._on_equipment_pos_changed)
        ac_pos_box.addWidget(self.spin_ac_x)
        ac_pos_box.addWidget(self.spin_ac_y)
        ac_pos_box.addWidget(self.spin_ac_z)
        f_ac.addRow("Ajuste Fino 3D (m):", ac_pos_box)

        ly.addWidget(box_ac)

        # Poblar selectores de unidades iniciales
        self._populate_eolic_combo()
        self._populate_exhaust_combo()
        self._populate_supply_combo()
        self._populate_fan_combo()
        self._populate_ac_combo()

        ly.addStretch()
        scroll.setWidget(w)
        self.tabs.addTab(scroll, "💨 Ventilación")

    # -------------------------------------------------------------------------
    # GESTIÓN DINÁMICA DE UNIDADES HVAC (AÑADIR / RETIRAR / SELECCIONAR)
    # -------------------------------------------------------------------------
    def _populate_eolic_combo(self):
        if not hasattr(self, "combo_eolic_select"): return
        self.combo_eolic_select.blockSignals(True)
        self.combo_eolic_select.clear()
        for u in self.eolic_units:
            status = "✓" if u.get("enabled", True) else "✗"
            self.combo_eolic_select.addItem(f"{status} {u['name']}")
        self.combo_eolic_select.blockSignals(False)

    def _on_eolic_selected(self, idx: int):
        if idx < 0 or idx >= len(self.eolic_units): return
        u = self.eolic_units[idx]
        self.chk_curr_eolic.blockSignals(True)
        self.chk_curr_eolic.setChecked(u.get("enabled", True))
        self.chk_curr_eolic.blockSignals(False)

        self.combo_wind_dia.blockSignals(True)
        self.combo_wind_dia.setCurrentText(u.get("dia", "24 pulgadas (60 cm)"))
        self.combo_wind_dia.blockSignals(False)

        self.combo_eolic_preset.blockSignals(True)
        self.combo_eolic_preset.setCurrentText(u.get("preset", "📍 Cumbrera Central (Punto más alto)"))
        self.combo_eolic_preset.blockSignals(False)

        self.slider_eolic_pos.blockSignals(True)
        self.slider_eolic_pos.setValue(u.get("offset_pct", 50))
        self.slider_eolic_pos.blockSignals(False)
        self.lbl_eolic_pos.setText(f"{u.get('offset_pct', 50)}% a lo largo del techo")

        self.spin_eolic_x.blockSignals(True)
        self.spin_eolic_y.blockSignals(True)
        self.spin_eolic_z.blockSignals(True)
        self.spin_eolic_x.setValue(u.get("x", 4.0))
        self.spin_eolic_y.setValue(u.get("y", 2.5))
        self.spin_eolic_z.setValue(u.get("z", 5.6))
        self.spin_eolic_x.blockSignals(False)
        self.spin_eolic_y.blockSignals(False)
        self.spin_eolic_z.blockSignals(False)

    def _add_eolic_unit(self):
        idx = len(self.eolic_units) + 1
        pct = 30 if idx % 2 == 1 else 70
        new_unit = {
            "name": f"Turbina Eólica #{idx}",
            "preset": "📍 Cumbrera Central (Punto más alto)",
            "offset_pct": pct,
            "dia": self.combo_wind_dia.currentText(),
            "x": 4.0, "y": 2.5, "z": 5.6,
            "enabled": True
        }
        self.eolic_units.append(new_unit)
        self._populate_eolic_combo()
        self.combo_eolic_select.setCurrentIndex(len(self.eolic_units) - 1)
        self._apply_eolic_preset()
        self.run_simulation()

    def _remove_eolic_unit(self):
        if len(self.eolic_units) <= 1:
            return
        idx = self.combo_eolic_select.currentIndex()
        if 0 <= idx < len(self.eolic_units):
            self.eolic_units.pop(idx)
            self._populate_eolic_combo()
            new_idx = max(0, idx - 1)
            self.combo_eolic_select.setCurrentIndex(new_idx)
            self._on_eolic_selected(new_idx)
            self._on_equipment_pos_changed()
            self.run_simulation()

    def _on_curr_eolic_param_changed(self):
        idx = self.combo_eolic_select.currentIndex()
        if 0 <= idx < len(self.eolic_units):
            self.eolic_units[idx]["enabled"] = self.chk_curr_eolic.isChecked()
            self.eolic_units[idx]["dia"] = self.combo_wind_dia.currentText()
            self._populate_eolic_combo()
            self.combo_eolic_select.blockSignals(True)
            self.combo_eolic_select.setCurrentIndex(idx)
            self.combo_eolic_select.blockSignals(False)
            self._on_equipment_pos_changed()
            self.run_simulation()

    # Extractores
    def _populate_exhaust_combo(self):
        if not hasattr(self, "combo_exhaust_select"): return
        self.combo_exhaust_select.blockSignals(True)
        self.combo_exhaust_select.clear()
        for u in self.exhaust_units:
            status = "✓" if u.get("enabled", True) else "✗"
            lvl = f"N{u.get('level', 1)}"
            self.combo_exhaust_select.addItem(f"{status} [{lvl}] {u['name']}")
        self.combo_exhaust_select.blockSignals(False)

    def _on_exhaust_selected(self, idx: int):
        if idx < 0 or idx >= len(self.exhaust_units): return
        u = self.exhaust_units[idx]
        self.chk_curr_exhaust.blockSignals(True)
        self.chk_curr_exhaust.setChecked(u.get("enabled", True))
        self.chk_curr_exhaust.blockSignals(False)

        self.combo_curr_exhaust_level.blockSignals(True)
        self.combo_curr_exhaust_level.setCurrentIndex(0 if u.get("level", 1) == 1 else 1)
        self.combo_curr_exhaust_level.blockSignals(False)

        self.combo_exhaust_preset.blockSignals(True)
        self.combo_exhaust_preset.setCurrentText(u.get("wall", "📍 Pared Norte (Posterior)"))
        self.combo_exhaust_preset.blockSignals(False)

        self.slider_exhaust_pos.blockSignals(True)
        self.slider_exhaust_pos.setValue(u.get("offset_pct", 50))
        self.slider_exhaust_pos.blockSignals(False)
        self.lbl_exhaust_pos.setText(f"{u.get('offset_pct', 50)}% a lo largo de la pared")

        self.spin_exhaust_flow.blockSignals(True)
        self.spin_exhaust_flow.setValue(u.get("flow", 1200.0))
        self.spin_exhaust_flow.blockSignals(False)

        self.spin_exhaust_x.blockSignals(True)
        self.spin_exhaust_y.blockSignals(True)
        self.spin_exhaust_z.blockSignals(True)
        self.spin_exhaust_x.setValue(u.get("x", 4.0))
        self.spin_exhaust_y.setValue(u.get("y", 4.85))
        self.spin_exhaust_z.setValue(u.get("z", 2.4))
        self.spin_exhaust_x.blockSignals(False)
        self.spin_exhaust_y.blockSignals(False)
        self.spin_exhaust_z.blockSignals(False)

    def _add_exhaust_unit(self):
        idx = len(self.exhaust_units) + 1
        pct = 30 if idx % 2 == 1 else 70
        new_unit = {
            "name": f"Extractor #{idx}",
            "level": 1 if self.combo_curr_exhaust_level.currentIndex() == 0 else 2,
            "wall": self.combo_exhaust_preset.currentText(),
            "offset_pct": pct,
            "flow": self.spin_exhaust_flow.value(),
            "x": 4.0, "y": 4.85, "z": 2.4,
            "enabled": True
        }
        self.exhaust_units.append(new_unit)
        self._populate_exhaust_combo()
        self.combo_exhaust_select.setCurrentIndex(len(self.exhaust_units) - 1)
        self._apply_exhaust_preset()
        self.run_simulation()

    def _remove_exhaust_unit(self):
        if len(self.exhaust_units) <= 1:
            return
        idx = self.combo_exhaust_select.currentIndex()
        if 0 <= idx < len(self.exhaust_units):
            self.exhaust_units.pop(idx)
            self._populate_exhaust_combo()
            new_idx = max(0, idx - 1)
            self.combo_exhaust_select.setCurrentIndex(new_idx)
            self._on_exhaust_selected(new_idx)
            self._on_equipment_pos_changed()
            self.run_simulation()

    def _on_curr_exhaust_param_changed(self):
        idx = self.combo_exhaust_select.currentIndex()
        if 0 <= idx < len(self.exhaust_units):
            self.exhaust_units[idx]["enabled"] = self.chk_curr_exhaust.isChecked()
            self.exhaust_units[idx]["flow"] = self.spin_exhaust_flow.value()
            self._populate_exhaust_combo()
            self.combo_exhaust_select.blockSignals(True)
            self.combo_exhaust_select.setCurrentIndex(idx)
            self.combo_exhaust_select.blockSignals(False)
            self._on_equipment_pos_changed()
            self.run_simulation()

    # Inyectores
    def _populate_supply_combo(self):
        if not hasattr(self, "combo_supply_select"): return
        self.combo_supply_select.blockSignals(True)
        self.combo_supply_select.clear()
        for u in self.supply_units:
            status = "✓" if u.get("enabled", True) else "✗"
            lvl = f"N{u.get('level', 1)}"
            self.combo_supply_select.addItem(f"{status} [{lvl}] {u['name']}")
        self.combo_supply_select.blockSignals(False)

    def _on_supply_selected(self, idx: int):
        if idx < 0 or idx >= len(self.supply_units): return
        u = self.supply_units[idx]
        self.chk_curr_supply.blockSignals(True)
        self.chk_curr_supply.setChecked(u.get("enabled", True))
        self.chk_curr_supply.blockSignals(False)

        self.combo_curr_supply_level.blockSignals(True)
        self.combo_curr_supply_level.setCurrentIndex(0 if u.get("level", 1) == 1 else 1)
        self.combo_curr_supply_level.blockSignals(False)

        self.combo_supply_preset.blockSignals(True)
        self.combo_supply_preset.setCurrentText(u.get("wall", "📍 Pared Sur (Frontal)"))
        self.combo_supply_preset.blockSignals(False)

        self.slider_supply_pos.blockSignals(True)
        self.slider_supply_pos.setValue(u.get("offset_pct", 50))
        self.slider_supply_pos.blockSignals(False)
        self.lbl_supply_pos.setText(f"{u.get('offset_pct', 50)}% a lo largo de la pared")

        self.spin_supply_flow.blockSignals(True)
        self.spin_supply_flow.setValue(u.get("flow", 1200.0))
        self.spin_supply_flow.blockSignals(False)
        if hasattr(self, "combo_supply_source"):
            self.combo_supply_source.blockSignals(True)
            self.combo_supply_source.setCurrentIndex(u.get("source", 0))
            self.combo_supply_source.blockSignals(False)

        self.spin_supply_x.blockSignals(True)
        self.spin_supply_y.blockSignals(True)
        self.spin_supply_z.blockSignals(True)
        self.spin_supply_x.setValue(u.get("x", 4.0))
        self.spin_supply_y.setValue(u.get("y", 0.15))
        self.spin_supply_z.setValue(u.get("z", 2.0))
        self.spin_supply_x.blockSignals(False)
        self.spin_supply_y.blockSignals(False)
        self.spin_supply_z.blockSignals(False)

    def _add_supply_unit(self):
        idx = len(self.supply_units) + 1
        pct = 30 if idx % 2 == 1 else 70
        new_unit = {
            "name": f"Inyector #{idx}",
            "level": 1 if self.combo_curr_supply_level.currentIndex() == 0 else 2,
            "wall": self.combo_supply_preset.currentText(),
            "offset_pct": pct,
            "flow": self.spin_supply_flow.value(),
            "x": 4.0, "y": 0.15, "z": 2.0,
            "enabled": True
        }
        self.supply_units.append(new_unit)
        self._populate_supply_combo()
        self.combo_supply_select.setCurrentIndex(len(self.supply_units) - 1)
        self._apply_supply_preset()
        self.run_simulation()

    def _remove_supply_unit(self):
        if len(self.supply_units) <= 1:
            return
        idx = self.combo_supply_select.currentIndex()
        if 0 <= idx < len(self.supply_units):
            self.supply_units.pop(idx)
            self._populate_supply_combo()
            new_idx = max(0, idx - 1)
            self.combo_supply_select.setCurrentIndex(new_idx)
            self._on_supply_selected(new_idx)
            self._on_equipment_pos_changed()
            self.run_simulation()

    def _on_curr_supply_param_changed(self):
        idx = self.combo_supply_select.currentIndex()
        if 0 <= idx < len(self.supply_units):
            self.supply_units[idx]["enabled"] = self.chk_curr_supply.isChecked()
            self.supply_units[idx]["flow"] = self.spin_supply_flow.value()
            if hasattr(self, "combo_supply_source"):
                self.supply_units[idx]["source"] = self.combo_supply_source.currentIndex()
            self._populate_supply_combo()
            self.combo_supply_select.blockSignals(True)
            self.combo_supply_select.setCurrentIndex(idx)
            self.combo_supply_select.blockSignals(False)
            self._on_equipment_pos_changed()
            self.run_simulation()

    # Ventiladores
    def _populate_fan_combo(self):
        if not hasattr(self, "combo_fan_select"): return
        self.combo_fan_select.blockSignals(True)
        self.combo_fan_select.clear()
        for u in self.fan_units:
            status = "✓" if u.get("enabled", True) else "✗"
            lvl = f"N{u.get('level', 1)}"
            m_str = "Techo" if u.get("mount", "techo") == "techo" else ("Mural" if u.get("mount") == "pared_alta" else "Pedestal")
            self.combo_fan_select.addItem(f"{status} [{lvl}] {u['name']} ({m_str})")
        self.combo_fan_select.blockSignals(False)

    def _on_fan_selected(self, idx: int):
        if idx < 0 or idx >= len(self.fan_units): return
        u = self.fan_units[idx]
        self.chk_curr_fan.blockSignals(True)
        self.chk_curr_fan.setChecked(u.get("enabled", True))
        self.chk_curr_fan.blockSignals(False)

        self.combo_curr_fan_level.blockSignals(True)
        self.combo_curr_fan_level.setCurrentIndex(0 if u.get("level", 1) == 1 else 1)
        self.combo_curr_fan_level.blockSignals(False)

        mount = u.get("mount", "techo")
        self.combo_fan_mount.blockSignals(True)
        if mount == "pared_alta":
            self.combo_fan_mount.setCurrentIndex(1)
        elif mount == "pedestal":
            self.combo_fan_mount.setCurrentIndex(2)
        else:
            self.combo_fan_mount.setCurrentIndex(0)
        self.combo_fan_mount.blockSignals(False)

        self.combo_fan_spd.blockSignals(True)
        self.combo_fan_spd.setCurrentText(u.get("speed", "Media (1.0 m/s - Confort Típico)"))
        self.combo_fan_spd.blockSignals(False)

        self.spin_fan_speed_custom.blockSignals(True)
        self.spin_fan_speed_custom.setValue(u.get("air_speed_m_s", 1.0))
        self.spin_fan_speed_custom.blockSignals(False)

        self.spin_fan_power_w.blockSignals(True)
        self.spin_fan_power_w.setValue(u.get("power_w", 75.0))
        self.spin_fan_power_w.blockSignals(False)

        self.combo_fan_preset.blockSignals(True)
        self.combo_fan_preset.setCurrentText(u.get("preset", "📍 Centro Habitación"))
        self.combo_fan_preset.blockSignals(False)

        self.slider_fan_x.blockSignals(True)
        self.slider_fan_x.setValue(u.get("offset_x", 50))
        self.slider_fan_x.blockSignals(False)
        self.slider_fan_y.blockSignals(True)
        self.slider_fan_y.setValue(u.get("offset_y", 50))
        self.slider_fan_y.blockSignals(False)

        self.spin_fan_x.blockSignals(True)
        self.spin_fan_y.blockSignals(True)
        self.spin_fan_z.blockSignals(True)
        self.spin_fan_x.setValue(u.get("x", 4.0))
        self.spin_fan_y.setValue(u.get("y", 2.5))
        self.spin_fan_z.setValue(u.get("z", 2.6))
        self.spin_fan_x.blockSignals(False)
        self.spin_fan_y.blockSignals(False)
        self.spin_fan_z.blockSignals(False)

        self._update_fan_relief_label()

    def _on_curr_fan_spd_preset_changed(self):
        txt = self.combo_fan_spd.currentText()
        if "Baja" in txt:
            self.spin_fan_speed_custom.setValue(0.5)
            self.spin_fan_power_w.setValue(45.0)
        elif "Media" in txt:
            self.spin_fan_speed_custom.setValue(1.0)
            self.spin_fan_power_w.setValue(75.0)
        elif "Alta" in txt:
            self.spin_fan_speed_custom.setValue(1.8)
            self.spin_fan_power_w.setValue(120.0)
        elif "Industrial" in txt:
            self.spin_fan_speed_custom.setValue(2.4)
            self.spin_fan_power_w.setValue(180.0)
        self._on_curr_fan_param_changed()

    def _update_fan_relief_label(self):
        if not hasattr(self, "lbl_fan_relief") or not hasattr(self, "combo_fan_mount"):
            return
        m_txt = self.combo_fan_mount.currentText()
        eff = 1.0 if "Techo" in m_txt else (0.88 if "Pared Alta" in m_txt else 0.95)
        v = self.spin_fan_speed_custom.value() if hasattr(self, "spin_fan_speed_custom") else 1.0
        dt = 1.25 * math.log(1.0 + (v / 0.15)) * eff if v > 0.15 else 0.0
        dt = min(4.8, max(0.4, dt))
        m_name = "Techo (Descendente)" if "Techo" in m_txt else ("Mural (Longitudinal)" if "Pared Alta" in m_txt else "Pedestal (Horizontal)")
        self.lbl_fan_relief.setText(f"❄️ Alivio ASHRAE 55: -{dt:.1f} °C aparente | {m_name}")

    def _add_fan_unit(self):
        idx = len(self.fan_units) + 1
        m_idx = self.combo_fan_mount.currentIndex() if hasattr(self, "combo_fan_mount") else 0
        mount = "techo" if m_idx == 0 else ("pared_alta" if m_idx == 1 else "pedestal")
        new_unit = {
            "name": f"Ventilador #{idx}",
            "level": 1 if self.combo_curr_fan_level.currentIndex() == 0 else 2,
            "mount": mount,
            "preset": "📍 Centro Habitación",
            "offset_x": 50, "offset_y": 50,
            "speed": self.combo_fan_spd.currentText() if hasattr(self, "combo_fan_spd") else "Media (1.0 m/s - Confort Típico)",
            "air_speed_m_s": self.spin_fan_speed_custom.value() if hasattr(self, "spin_fan_speed_custom") else 1.0,
            "power_w": self.spin_fan_power_w.value() if hasattr(self, "spin_fan_power_w") else 75.0,
            "airflow_m3_h": 4500.0,
            "x": 4.0, "y": 2.5, "z": 2.6,
            "enabled": True
        }
        self.fan_units.append(new_unit)
        self._populate_fan_combo()
        self.combo_fan_select.setCurrentIndex(len(self.fan_units) - 1)
        self._apply_fan_preset()
        self.run_simulation()

    def _remove_fan_unit(self):
        if len(self.fan_units) <= 1:
            return
        idx = self.combo_fan_select.currentIndex()
        if 0 <= idx < len(self.fan_units):
            self.fan_units.pop(idx)
            self._populate_fan_combo()
            new_idx = max(0, idx - 1)
            self.combo_fan_select.setCurrentIndex(new_idx)
            self._on_fan_selected(new_idx)
            self._on_equipment_pos_changed()
            self.run_simulation()

    def _on_curr_fan_param_changed(self):
        idx = self.combo_fan_select.currentIndex()
        if 0 <= idx < len(self.fan_units):
            self.fan_units[idx]["enabled"] = self.chk_curr_fan.isChecked()
            m_txt = self.combo_fan_mount.currentText()
            mount = "techo" if "Techo" in m_txt else ("pared_alta" if "Pared Alta" in m_txt else "pedestal")
            self.fan_units[idx]["mount"] = mount
            self.fan_units[idx]["speed"] = self.combo_fan_spd.currentText()
            self.fan_units[idx]["air_speed_m_s"] = self.spin_fan_speed_custom.value()
            self.fan_units[idx]["power_w"] = self.spin_fan_power_w.value()
            self._update_fan_relief_label()
            self._populate_fan_combo()
            self.combo_fan_select.blockSignals(True)
            self.combo_fan_select.setCurrentIndex(idx)
            self.combo_fan_select.blockSignals(False)
            self._on_equipment_pos_changed()
            self.run_simulation()

    # Aire Acondicionado Split
    def _populate_ac_combo(self):
        if not hasattr(self, "combo_ac_select"): return
        self.combo_ac_select.blockSignals(True)
        self.combo_ac_select.clear()
        for u in self.ac_units:
            status = "✓" if u.get("enabled", True) else "✗"
            lvl = f"N{u.get('level', 1)}"
            cap_k = f"{int(round(u.get('nominal_btu_h', 24000.0) / 1000.0))}k" if not u.get("is_auto", False) else "Auto"
            self.combo_ac_select.addItem(f"{status} [{lvl}] {u['name']} ({cap_k} BTU)")
        self.combo_ac_select.blockSignals(False)

    def _on_ac_selected(self, idx: int):
        if idx < 0 or idx >= len(self.ac_units): return
        u = self.ac_units[idx]
        self.chk_curr_ac.blockSignals(True)
        self.chk_curr_ac.setChecked(u.get("enabled", True))
        self.chk_curr_ac.blockSignals(False)

        self.combo_curr_ac_level.blockSignals(True)
        self.combo_curr_ac_level.setCurrentIndex(0 if u.get("level", 1) == 1 else 1)
        self.combo_curr_ac_level.blockSignals(False)

        self.spin_ac_setpoint.blockSignals(True)
        self.spin_ac_setpoint.setValue(u.get("setpoint", 24.0))
        self.spin_ac_setpoint.blockSignals(False)

        self.combo_ac_cap.blockSignals(True)
        self.combo_ac_cap.setCurrentText(u.get("cap_mode", "24,000 BTU/h (2.0 TR - Comercial Típico)"))
        self.combo_ac_cap.blockSignals(False)

        self.spin_ac_nominal_btu.blockSignals(True)
        self.spin_ac_nominal_btu.setValue(u.get("nominal_btu_h", 24000.0))
        self.spin_ac_nominal_btu.blockSignals(False)

        cop_val = u.get("cop", 3.2)
        self.combo_ac_cop.blockSignals(True)
        for i in range(self.combo_ac_cop.count()):
            if f"{cop_val:.1f}" in self.combo_ac_cop.itemText(i):
                self.combo_ac_cop.setCurrentIndex(i)
                break
        self.combo_ac_cop.blockSignals(False)

        self.combo_ac_preset.blockSignals(True)
        self.combo_ac_preset.setCurrentText(u.get("wall", "📍 Pared Sur (Frontal)"))
        self.combo_ac_preset.blockSignals(False)

        self.slider_ac_wall_pos.blockSignals(True)
        self.slider_ac_wall_pos.setValue(u.get("offset_pct", 50))
        self.slider_ac_wall_pos.blockSignals(False)
        self.lbl_ac_wall_pos.setText(f"{u.get('offset_pct', 50)}% a lo largo del muro")

        h_val = int(round(u.get("height_m", 2.3) * 10))
        self.slider_ac_height.blockSignals(True)
        self.slider_ac_height.setValue(h_val)
        self.slider_ac_height.blockSignals(False)
        self.lbl_ac_height.setText(f"{u.get('height_m', 2.3):.1f} m sobre nivel de piso terminado")

        self.spin_ac_x.blockSignals(True)
        self.spin_ac_y.blockSignals(True)
        self.spin_ac_z.blockSignals(True)
        self.spin_ac_x.setValue(u.get("x", 2.0))
        self.spin_ac_y.setValue(u.get("y", 0.15))
        self.spin_ac_z.setValue(u.get("z", 2.3))
        self.spin_ac_x.blockSignals(False)
        self.spin_ac_y.blockSignals(False)
        self.spin_ac_z.blockSignals(False)

    def _on_curr_ac_cap_preset_changed(self):
        txt = self.combo_ac_cap.currentText()
        if "12,000" in txt:
            self.spin_ac_nominal_btu.setValue(12000.0)
        elif "18,000" in txt:
            self.spin_ac_nominal_btu.setValue(18000.0)
        elif "24,000" in txt:
            self.spin_ac_nominal_btu.setValue(24000.0)
        elif "36,000" in txt:
            self.spin_ac_nominal_btu.setValue(36000.0)
        elif "48,000" in txt:
            self.spin_ac_nominal_btu.setValue(48000.0)
        elif "60,000" in txt:
            self.spin_ac_nominal_btu.setValue(60000.0)
        self._on_curr_ac_param_changed()

    def _add_ac_unit(self):
        idx = len(self.ac_units) + 1
        pct = 30 if idx % 2 == 1 else 70
        is_auto = "Auto-dimensionar" in self.combo_ac_cap.currentText() if hasattr(self, "combo_ac_cap") else False
        new_unit = {
            "name": f"A/C Split #{idx}",
            "level": 1 if self.combo_curr_ac_level.currentIndex() == 0 else 2,
            "wall": self.combo_ac_preset.currentText(),
            "offset_pct": pct,
            "height_m": self.slider_ac_height.value() / 10.0,
            "setpoint": self.spin_ac_setpoint.value(),
            "cap_mode": self.combo_ac_cap.currentText() if hasattr(self, "combo_ac_cap") else "24,000 BTU/h (2.0 TR - Comercial Típico)",
            "nominal_btu_h": self.spin_ac_nominal_btu.value() if hasattr(self, "spin_ac_nominal_btu") else 24000.0,
            "cop": 3.2,
            "is_auto": is_auto,
            "x": 2.0, "y": 0.15, "z": 2.3,
            "enabled": True
        }
        self.ac_units.append(new_unit)
        self._populate_ac_combo()
        self.combo_ac_select.setCurrentIndex(len(self.ac_units) - 1)
        self._apply_ac_preset()
        self.run_simulation()

    def _remove_ac_unit(self):
        if len(self.ac_units) <= 1:
            return
        idx = self.combo_ac_select.currentIndex()
        if 0 <= idx < len(self.ac_units):
            self.ac_units.pop(idx)
            self._populate_ac_combo()
            new_idx = max(0, idx - 1)
            self.combo_ac_select.setCurrentIndex(new_idx)
            self._on_ac_selected(new_idx)
            self._on_equipment_pos_changed()
            self.run_simulation()

    def _on_curr_ac_param_changed(self):
        idx = self.combo_ac_select.currentIndex()
        if 0 <= idx < len(self.ac_units):
            self.ac_units[idx]["enabled"] = self.chk_curr_ac.isChecked()
            self.ac_units[idx]["setpoint"] = self.spin_ac_setpoint.value()
            self.ac_units[idx]["cap_mode"] = self.combo_ac_cap.currentText()
            self.ac_units[idx]["nominal_btu_h"] = self.spin_ac_nominal_btu.value()
            is_auto = "Auto-dimensionar" in self.combo_ac_cap.currentText()
            self.ac_units[idx]["is_auto"] = is_auto

            cop_txt = self.combo_ac_cop.currentText()
            cop_val = 3.2
            if "2.8" in cop_txt: cop_val = 2.8
            elif "3.6" in cop_txt: cop_val = 3.6
            elif "4.0" in cop_txt: cop_val = 4.0
            self.ac_units[idx]["cop"] = cop_val

            self._populate_ac_combo()
            self.combo_ac_select.blockSignals(True)
            self.combo_ac_select.setCurrentIndex(idx)
            self.combo_ac_select.blockSignals(False)
            self._on_equipment_pos_changed()
            self.run_simulation()

    # Compatibilidad con código legado que llame a spin_*_qty.value()
    @property
    def spin_exhaust_qty(self):
        class _D:
            def __init__(self, v): self._v = v
            def value(self): return self._v
            def setEnabled(self, *a, **k): pass
            def setVisible(self, *a, **k): pass
            def setValue(self, v): self._v = v
            def blockSignals(self, *a, **k): pass
        return _D(max(1, len([u for u in getattr(self, "exhaust_units", []) if u.get("enabled", True)])))

    @property
    def spin_supply_qty(self):
        class _D:
            def __init__(self, v): self._v = v
            def value(self): return self._v
            def setEnabled(self, *a, **k): pass
            def setVisible(self, *a, **k): pass
            def setValue(self, v): self._v = v
            def blockSignals(self, *a, **k): pass
        return _D(max(1, len([u for u in getattr(self, "supply_units", []) if u.get("enabled", True)])))

    @property
    def spin_wind_turbines(self):
        class _D:
            def __init__(self, v): self._v = v
            def value(self): return self._v
            def setEnabled(self, *a, **k): pass
            def setVisible(self, *a, **k): pass
            def setValue(self, v): self._v = v
            def blockSignals(self, *a, **k): pass
        return _D(max(0, len([u for u in getattr(self, "eolic_units", []) if u.get("enabled", True)])))

    @property
    def spin_fan_qty(self):
        class _D:
            def __init__(self, v): self._v = v
            def value(self): return self._v
            def setEnabled(self, *a, **k): pass
            def setVisible(self, *a, **k): pass
            def setValue(self, v): self._v = v
            def blockSignals(self, *a, **k): pass
        return _D(max(1, len([u for u in getattr(self, "fan_units", []) if u.get("enabled", True)])))

    @property
    def spin_ac_qty(self):
        class _D:
            def __init__(self, v): self._v = v
            def value(self): return self._v
            def setEnabled(self, *a, **k): pass
            def setVisible(self, *a, **k): pass
            def setValue(self, v): self._v = v
            def blockSignals(self, *a, **k): pass
        return _D(max(1, len([u for u in getattr(self, "ac_units", []) if u.get("enabled", True)])))

    # -------------------------------------------------------------------------
    # GESTIÓN DE MATERIALES PERSONALIZADOS
    # -------------------------------------------------------------------------
    def _choose_roof_material(self):
        dlg = MaterialSelectionDialog("techo", PREDEFINED_ROOFS, self.selected_roof, self)
        if dlg.exec():
            self.selected_roof = dlg.selected_material
            self.lbl_current_roof.setText(self.selected_roof.name)
            if hasattr(self, "viewer_3d") and self.viewer_3d.building_model:
                for s in self.viewer_3d.building_model.surfaces:
                    if s.surface_type == "roof":
                        s.material_name = self.selected_roof.name
                        s.thickness_m = self.selected_roof.thickness
            self._populate_inspector()
            self.run_simulation()

    def _choose_slab_material(self):
        dlg = MaterialSelectionDialog("losa", PREDEFINED_ROOFS, self.selected_slab, self)
        if dlg.exec():
            self.selected_slab = dlg.selected_material
            self.lbl_current_slab.setText(self.selected_slab.name)
            self.run_simulation()

    def _on_window_open_changed(self, val: int):
        if val == 0:
            txt = "0% (Completamente Cerradas)"
        elif val == 50:
            txt = "50% (Máxima Apertura Útil Corrediza)"
        else:
            txt = f"{val}% de Área Abierta"
        self.lbl_open_val.setText(txt)
        self.run_simulation()

    def _choose_ceiling_material(self):
        dlg = MaterialSelectionDialog("cielo_raso", PREDEFINED_CEILINGS, self.selected_ceiling, self)
        if dlg.exec():
            self.selected_ceiling = dlg.selected_material
            name = self.selected_ceiling.name if self.selected_ceiling else "Sin Cielo Raso"
            self.lbl_current_ceiling.setText(name)
            self.run_simulation()

    def _choose_wall_material(self):
        dlg = MaterialSelectionDialog("muro", PREDEFINED_WALLS, self.selected_wall, self)
        if dlg.exec():
            self.selected_wall = dlg.selected_material
            self.lbl_current_wall.setText(self.selected_wall.name)
            if hasattr(self, "viewer_3d") and self.viewer_3d.building_model:
                for s in self.viewer_3d.building_model.surfaces:
                    if s.surface_type == "wall":
                        s.material_name = self.selected_wall.name
                        s.thickness_m = self.selected_wall.thickness
            self._populate_inspector()
            self.run_simulation()

    def _choose_window_material(self):
        dlg = MaterialSelectionDialog("ventana", PREDEFINED_WINDOWS, self.selected_window, self)
        if dlg.exec():
            self.selected_window = dlg.selected_material
            self.lbl_current_win.setText(self.selected_window.name)
            if hasattr(self, "viewer_3d") and self.viewer_3d.building_model:
                for s in self.viewer_3d.building_model.surfaces:
                    if s.surface_type == "window":
                        s.material_name = self.selected_window.name
                        s.thickness_m = self.selected_window.thickness
            self._populate_inspector()
            self.run_simulation()

    def _on_city_changed(self):
        city_name = self.combo_city.currentText()
        self.current_city = PERU_CITIES.get(city_name, self.current_city)
        self.lbl_city_desc.setText(self.current_city.description)
        self.run_simulation()

    def _on_geometry_changed(self):
        # Reconstruir modelo 3D paramétrico
        n_floors = self.spin_floors.value()
        length = self.spin_length.value()
        width = self.spin_width.value()
        h_piso = self.spin_height_piso.value()
        h_east = self.spin_obs_east.value()
        h_west = self.spin_obs_west.value()

        model = BuildingGeometry3D.create_default_building(
            length=length,
            width=width,
            height_piso=h_piso,
            num_floors=n_floors,
            neighbor_east_height=h_east,
            neighbor_west_height=h_west,
        )
        self.viewer_3d.set_model(model)
        if hasattr(self, "floor_plan_widget"):
            self.floor_plan_widget.set_model(model)
        self._populate_inspector()
        self.run_simulation()

    def load_geometry_file(self, file_path: str, show_dialog: bool = False):
        """Carga programática o interactiva de archivos OBJ o JSON de SketchUp."""
        model = None
        if file_path.lower().endswith(".json"):
            model = SketchUpLoader.load_from_json(file_path)
        elif file_path.lower().endswith(".obj"):
            model = SketchUpLoader.load_from_obj(file_path)

        if model and (model.surfaces or model.neighbor_obstacles):
            self.viewer_3d.set_model(model)
            if hasattr(self, "floor_plan_widget"):
                self.floor_plan_widget.set_model(model)
                self.floor_plan_widget.update_z_presets()

            hb = self.viewer_3d.get_house_bounds()
            if hb["len_x"] > 1.0 and hb["len_y"] > 1.0:
                self.spin_length.blockSignals(True)
                self.spin_width.blockSignals(True)
                self.spin_height_piso.blockSignals(True)
                self.spin_floors.blockSignals(True)

                self.spin_length.setValue(round(hb["len_x"], 2))
                self.spin_width.setValue(round(hb["len_y"], 2))

                has_l2 = any(s.level == 2 for s in model.surfaces if s.surface_type != "neighbor_wall") or (hb["height"] > 3.4)
                num_fl = 2 if has_l2 else 1
                self.spin_floors.setValue(num_fl)
                self.spin_height_piso.setValue(round(hb["height"] / num_fl, 2))

                self.spin_length.blockSignals(False)
                self.spin_width.blockSignals(False)
                self.spin_height_piso.blockSignals(False)
                self.spin_floors.blockSignals(False)

            self._populate_inspector()
            self._apply_ac_preset()
            self._apply_fan_preset()
            self._apply_eolic_preset()
            self._apply_exhaust_preset()
            self._apply_supply_preset()
            if show_dialog:
                QMessageBox.information(
                    self,
                    "Modelo Cargado",
                    f"Se cargó exitosamente el modelo de SketchUp con {len(model.surfaces)} superficies y {len(model.neighbor_obstacles)} obstáculos vecinos."
                )
            self.run_simulation()
            return True
        else:
            if show_dialog:
                QMessageBox.warning(self, "Error de Carga", "No se pudieron extraer superficies 3D válidas del archivo seleccionado.")
            return False

    def load_model_file(self, file_path: str):
        return self.load_geometry_file(file_path, show_dialog=False)

    def _import_sketchup_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Cargar Geometría de SketchUp",
                "",
                "Archivos Compatibles (*.obj *.json);;Wavefront OBJ (*.obj);;JSON Térmico (*.json)"
            )
            if not file_path:
                return

            model = None
            if file_path.lower().endswith(".json"):
                model = SketchUpLoader.load_from_json(file_path)
            elif file_path.lower().endswith(".obj"):
                model = SketchUpLoader.load_from_obj(file_path)

            if model and (model.surfaces or model.neighbor_obstacles):
                self.viewer_3d.set_model(model)
                if hasattr(self, "floor_plan_widget"):
                    self.floor_plan_widget.set_model(model)
                    self.floor_plan_widget.update_z_presets()

                # Auto-detectar dimensiones y número de pisos desde la geometría real
                hb = self.viewer_3d.get_house_bounds()
                if hb["len_x"] > 1.0 and hb["len_y"] > 1.0:
                    self.spin_length.blockSignals(True)
                    self.spin_width.blockSignals(True)
                    self.spin_height_piso.blockSignals(True)
                    self.spin_floors.blockSignals(True)

                    self.spin_length.setValue(round(hb["len_x"], 2))
                    self.spin_width.setValue(round(hb["len_y"], 2))

                    has_l2 = any(s.level == 2 for s in model.surfaces if s.surface_type != "neighbor_wall") or (hb["height"] > 3.4)
                    num_fl = 2 if has_l2 else 1
                    self.spin_floors.setValue(num_fl)
                    self.spin_height_piso.setValue(round(hb["height"] / num_fl, 2))

                    self.spin_length.blockSignals(False)
                    self.spin_width.blockSignals(False)
                    self.spin_height_piso.blockSignals(False)
                    self.spin_floors.blockSignals(False)

                self._populate_inspector()
                self._apply_ac_preset()
                self._apply_fan_preset()
                self._apply_eolic_preset()
                self._apply_exhaust_preset()
                self._apply_supply_preset()
                QMessageBox.information(
                    self,
                    "Modelo Cargado",
                    f"Se cargó exitosamente el modelo de SketchUp con {len(model.surfaces)} superficies y {len(model.neighbor_obstacles)} obstáculos vecinos."
                )
                self.run_simulation()
            else:
                QMessageBox.warning(self, "Error de Carga", "No se pudieron extraer superficies 3D válidas del archivo seleccionado.")
        except Exception as err:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error de Importación", f"Ocurrió un error al cargar el modelo:\n{err}")

    # -------------------------------------------------------------------------
    # EJECUCIÓN DEL MOTOR DE SIMULACIÓN Y ACTUALIZACIÓN EN TIEMPO REAL
    # -------------------------------------------------------------------------
    def run_simulation(self):
        # 1. Ensamble de cubierta y cielo raso
        assembly = RoofCeilingAssembly(
            name="Ensamble Techo",
            roof_material=self.selected_roof,
            ceiling_material=self.selected_ceiling,
            has_air_cavity=(self.selected_ceiling is not None),
            cavity_ventilated=self.chk_cavity_vent.isChecked(),
        )
        self.lbl_u_roof_total.setText(f"Transmitancia Ensamble: {assembly.u_value:.2f} W/m²K")

        # 2. Configurar zonas y ocupación
        num_floors = self.spin_floors.value()
        length = self.spin_length.value()
        width = self.spin_width.value()
        h_piso = self.spin_height_piso.value()

        # Ocupación y ganancia interna
        occ_1 = self.spin_occ_l1.value() if hasattr(self, "spin_occ_l1") else 2
        occ_2 = self.spin_occ_l2.value() if hasattr(self, "spin_occ_l2") else 2
        act_text = self.combo_occ_activity.currentText() if hasattr(self, "combo_occ_activity") else "100"
        if "75" in act_text:
            heat_per_person = 75.0
        elif "130" in act_text:
            heat_per_person = 130.0
        elif "180" in act_text:
            heat_per_person = 180.0
        else:
            heat_per_person = 100.0

        equip_w = self.spin_equip_w.value() if hasattr(self, "spin_equip_w") else 200.0
        total_people = occ_1 + (occ_2 if num_floors == 2 else 0)
        total_human_w = total_people * heat_per_person
        total_intern_w = total_human_w + equip_w

        h_loss_approx = max(50.0, (2.0 * (length + width) * h_piso * self.selected_wall.u_value) + (length * width * assembly.u_value) + (0.33 * 1.0 * length * width * h_piso))
        sensible_human_w = total_people * (heat_per_person * 0.65)
        latent_human_w = total_people * (heat_per_person * 0.35)
        flow_occ_m3_h = total_people * 18.0 if total_people > 0 else 0.0
        m_dot_vent = (flow_occ_m3_h / 3600.0) * 1.204
        q_vent_coeff = m_dot_vent * 1005.0
        h_loss_total = max(100.0, (2.0 * (length + width) * h_piso * self.selected_wall.u_value) + (length * width * assembly.u_value) + q_vent_coeff)
        approx_dt = min(3.8, max(0.2, (sensible_human_w + equip_w) / h_loss_total)) if total_people > 0 else 0.0
        if hasattr(self, "lbl_occ_power"):
            self.lbl_occ_power.setText(f"Calor Ocupantes: {total_human_w:.0f} W (Sensible: {sensible_human_w:.0f} W)  |  Equipos: {equip_w:.0f} W  |  Total: {total_intern_w:.0f} W")
        if hasattr(self, "lbl_occ_dt"):
            self.lbl_occ_dt.setText(f"Incremento Térmico por Ocupación: +{approx_dt:.1f} °C  (Ventilación Normativa: {flow_occ_m3_h:.0f} m³/h)")

        # Ventilación Mecánica Forzada: Asignación por niveles individuales (Multi-punto)
        has_ex = self.chk_exhaust.isChecked() if hasattr(self, "chk_exhaust") else False
        ex_units_1 = [u for u in self.exhaust_units if u.get("enabled", True) and u.get("level", 1) == 1] if has_ex else []
        ex_units_2 = [u for u in self.exhaust_units if u.get("enabled", True) and u.get("level", 1) == 2] if has_ex else []
        ex_flow_1 = sum(u.get("flow", 1200.0) for u in ex_units_1)
        ex_flow_2 = sum(u.get("flow", 1200.0) for u in ex_units_2)
        ex_qty_1 = len(ex_units_1)
        ex_qty_2 = len(ex_units_2)

        has_sup = self.chk_supply.isChecked() if hasattr(self, "chk_supply") else False
        sup_units_1 = [u for u in self.supply_units if u.get("enabled", True) and u.get("level", 1) == 1] if has_sup else []
        sup_units_2 = [u for u in self.supply_units if u.get("enabled", True) and u.get("level", 1) == 2] if has_sup else []
        sup_flow_1 = sum(u.get("flow", 1200.0) for u in sup_units_1)
        sup_flow_2 = sum(u.get("flow", 1200.0) for u in sup_units_2)
        sup_qty_1 = len(sup_units_1)
        sup_qty_2 = len(sup_units_2)

        source_deltas = [0.0, -2.5, -3.5, -5.0]
        sup_delta_1 = sum(source_deltas[min(3, max(0, u.get("source", 0)))] * u.get("flow", 1200.0) for u in sup_units_1) / max(1.0, sup_flow_1) if sup_units_1 else 0.0
        sup_delta_2 = sum(source_deltas[min(3, max(0, u.get("source", 0)))] * u.get("flow", 1200.0) for u in sup_units_2) / max(1.0, sup_flow_2) if sup_units_2 else 0.0

        mech_v_1 = MechanicalVentilation(
            has_exhaust_fan=(ex_qty_1 > 0),
            exhaust_flow_m3_h=ex_flow_1,
            exhaust_quantity=max(1, ex_qty_1),
            has_supply_fan=(sup_qty_1 > 0),
            supply_flow_m3_h=sup_flow_1,
            supply_quantity=max(1, sup_qty_1),
            supply_temp_delta_c=sup_delta_1,
        )

        mech_v_2 = MechanicalVentilation(
            has_exhaust_fan=(ex_qty_2 > 0),
            exhaust_flow_m3_h=ex_flow_2,
            exhaust_quantity=max(1, ex_qty_2),
            has_supply_fan=(sup_qty_2 > 0),
            supply_flow_m3_h=sup_flow_2,
            supply_quantity=max(1, sup_qty_2),
            supply_temp_delta_c=sup_delta_2,
        )

        has_fan = self.chk_fan.isChecked() if hasattr(self, "chk_fan") else False
        active_fans = [u for u in self.fan_units if u.get("enabled", True)] if has_fan else []
        active_fans_1 = [u for u in active_fans if u.get("level", 1) == 1] or (active_fans if num_floors == 1 else [])
        active_fans_2 = [u for u in active_fans if u.get("level", 1) == 2]

        v1 = sum(u.get("air_speed_m_s", 1.0) for u in active_fans_1) / max(1, len(active_fans_1))
        p1 = sum(u.get("power_w", 75.0) for u in active_fans_1)
        m1 = active_fans_1[0].get("mount", "techo") if active_fans_1 else "techo"
        comfort_fan_1 = CeilingComfortFan(
            enabled=len(active_fans_1) > 0,
            quantity=max(1, len(active_fans_1)),
            mount_type=m1,
            fan_speed=active_fans_1[0].get("speed", "media") if active_fans_1 else "media",
            air_speed_m_s=v1,
            motor_power_w=p1,
        )

        v2 = sum(u.get("air_speed_m_s", 1.0) for u in active_fans_2) / max(1, len(active_fans_2))
        p2 = sum(u.get("power_w", 75.0) for u in active_fans_2)
        m2 = active_fans_2[0].get("mount", "techo") if active_fans_2 else "techo"
        comfort_fan_2 = CeilingComfortFan(
            enabled=len(active_fans_2) > 0,
            quantity=max(1, len(active_fans_2)),
            mount_type=m2,
            fan_speed=active_fans_2[0].get("speed", "media") if active_fans_2 else "media",
            air_speed_m_s=v2,
            motor_power_w=p2,
        )

        has_ac = self.chk_ac.isChecked() if hasattr(self, "chk_ac") else False
        if has_ac and self.ac_units and not any(u.get("enabled", False) for u in self.ac_units):
            self.ac_units[0]["enabled"] = True
        active_ac = [u for u in self.ac_units if u.get("enabled", True)] if has_ac else []
        active_ac_1 = [u for u in active_ac if u.get("level", 1) == 1] or (active_ac if num_floors == 1 else [])
        active_ac_2 = [u for u in active_ac if u.get("level", 1) == 2]

        tot_btu_1 = sum(u.get("nominal_btu_h", 24000.0) for u in active_ac_1)
        is_auto_1 = any(u.get("is_auto", False) for u in active_ac_1)
        min_setpoint_1 = min((u.get("setpoint", 24.0) for u in active_ac_1), default=24.0)
        cop_1 = sum(u.get("cop", 3.2) for u in active_ac_1) / max(1, len(active_ac_1))
        ac_sys_1 = AirConditioningSystem(
            enabled=len(active_ac_1) > 0,
            quantity=1,
            target_temperature_c=min_setpoint_1,
            cop_efficiency=cop_1,
            is_auto_capacity=is_auto_1,
            nominal_cooling_btu_h=max(1000.0, tot_btu_1),
        )

        tot_btu_2 = sum(u.get("nominal_btu_h", 24000.0) for u in active_ac_2)
        is_auto_2 = any(u.get("is_auto", False) for u in active_ac_2)
        min_setpoint_2 = min((u.get("setpoint", 24.0) for u in active_ac_2), default=24.0)
        cop_2 = sum(u.get("cop", 3.2) for u in active_ac_2) / max(1, len(active_ac_2))
        ac_sys_2 = AirConditioningSystem(
            enabled=len(active_ac_2) > 0,
            quantity=1,
            target_temperature_c=min_setpoint_2,
            cop_efficiency=cop_2,
            is_auto_capacity=is_auto_2,
            nominal_cooling_btu_h=max(1000.0, tot_btu_2),
        )

        open_ratio = self.slider_window_open.value() / 100.0 if hasattr(self, 'slider_window_open') else 0.0

        z1 = ThermalZoneConfig(
            name="Nivel 1",
            level_number=1,
            length_m=length,
            width_m=width,
            height_m=h_piso,
            wall_material=self.selected_wall,
            window_material=self.selected_window,
            window_open_ratio=open_ratio,
            occupants=occ_1,
            occupant_heat_w=heat_per_person,
            equipment_w=equip_w / (2.0 if num_floors == 2 else 1.0),
            mechanical_vent=mech_v_1,
            comfort_fan=comfort_fan_1,
            ac_system=ac_sys_1,
        )

        z2 = None
        if num_floors == 2:
            z2 = ThermalZoneConfig(
                name="Nivel 2",
                level_number=2,
                length_m=length,
                width_m=width,
                height_m=h_piso,
                wall_material=self.selected_wall,
                window_material=self.selected_window,
                window_open_ratio=open_ratio,
                occupants=occ_2,
                occupant_heat_w=heat_per_person,
                equipment_w=equip_w / 2.0,
                mechanical_vent=mech_v_2,
                comfort_fan=comfort_fan_2,
                ac_system=ac_sys_2,
            )
        # Turbina eólica
        eolic_active = self.chk_eolic.isChecked() if hasattr(self, "chk_eolic") else True
        n_turbines = self.spin_wind_turbines.value() if hasattr(self, "spin_wind_turbines") else 2
        dia_inches = 24.0
        if "14" in self.combo_wind_dia.currentText():
            dia_inches = 14.0
        elif "20" in self.combo_wind_dia.currentText():
            dia_inches = 20.0
        elif "30" in self.combo_wind_dia.currentText():
            dia_inches = 30.0

        turbine = WindTurbineVentilator(
            enabled=eolic_active and (n_turbines > 0),
            quantity=n_turbines,
            throat_diameter_inches=dia_inches
        )

        # Obstáculos vecinos
        obs = []
        if self.spin_obs_east.value() > 0:
            obs.append(NeighborObstacle(name="Muro Este", direction="Este", height_m=self.spin_obs_east.value()))
        if self.spin_obs_west.value() > 0:
            obs.append(NeighborObstacle(name="Muro Oeste", direction="Oeste", height_m=self.spin_obs_west.value()))

        # Ejecutar simulación
        season = "summer" if "Verano" in self.combo_season.currentText() else "winter"
        sim = MultiLevelThermalSimulator(
            zone_1=z1,
            zone_2=z2,
            roof_assembly=assembly,
            wind_turbine=turbine,
            climate=self.current_city,
            obstacles=obs,
            north_orientation_deg=float(self.spin_north.value()),
            slab_material=self.selected_slab,
        )

        custom_t = None
        if hasattr(self, "chk_custom_temp") and self.chk_custom_temp.isChecked():
            custom_t = self.spin_custom_temp.value()

        self.last_results = sim.simulate_24h(season=season, custom_ambient_t=custom_t)

        # Actualizar Gráficos
        self.charts_widget.update_charts(self.last_results)

        # Actualizar Tarjetas KPI
        max_t1 = max(r["t_int_level_1"] for r in self.last_results)
        max_t2 = max(r["t_int_level_2"] for r in self.last_results) if num_floors == 2 else max_t1
        max_ac = max(r["ac_btu_h_1"] + r["ac_btu_h_2"] for r in self.last_results)

        self.card_l1.findChild(QLabel, "val_lbl").setText(f"{max_t1:.1f} °C")
        self.card_l2.findChild(QLabel, "val_lbl").setText(f"{max_t2:.1f} °C" if num_floors == 2 else "N/A (1 Piso)")
        self.card_shade.findChild(QLabel, "val_lbl").setText(f"-{max(0.0, max_t2 - max_t1):.1f} °C (Nivel 1 más fresco)")
        peak_r = max(self.last_results, key=lambda x: x.get("t_int_level_1", 0.0))
        is_suff = peak_r.get("ac_is_sufficient_1", True)
        deficit = peak_r.get("ac_deficit_btu_1", 0.0)
        demand = peak_r.get("ac_demand_btu_1", 0.0)
        nominal = peak_r.get("ac_nominal_btu_1", 0.0) + peak_r.get("ac_nominal_btu_2", 0.0)

        if not has_ac:
            self.card_ac.findChild(QLabel, "val_lbl").setText("0 BTU/h (Apagado)")
        elif any(u.get("is_auto", False) for u in active_ac):
            self.card_ac.findChild(QLabel, "val_lbl").setText(f"{max_ac:,.0f} BTU/h (Auto)")
        elif not is_suff and deficit > 500:
            self.card_ac.findChild(QLabel, "val_lbl").setText(f"{nominal:,.0f} BTU/h (Déficit -{deficit:,.0f})")
        else:
            self.card_ac.findChild(QLabel, "val_lbl").setText(f"{max_ac:,.0f} / {nominal:,.0f} BTU/h")

        if hasattr(self, "lbl_ac_diag"):
            if not has_ac:
                self.lbl_ac_diag.setText("📊 Climatización A/C inactiva (Modo Pasivo / Ventilación Natural)")
                self.lbl_ac_diag.setStyleSheet("color: #90a4ae; font-size: 11px;")
            elif any(u.get("is_auto", False) for u in active_ac):
                self.lbl_ac_diag.setText(f"⚡ Auto-dimensionado: Demanda Pico {demand:,.0f} BTU/h ({demand/12000.0:.1f} TR) satisfecha al 100%")
                self.lbl_ac_diag.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 11px;")
            elif not is_suff and deficit > 500:
                self.lbl_ac_diag.setText(f"⚠️ DÉFICIT FRIGORÍFICO: Faltan {deficit:,.0f} BTU/h ({nominal:,.0f} inst. vs {demand:,.0f} req.) | T. int sube a {max_t1:.1f} °C")
                self.lbl_ac_diag.setStyleSheet("color: #ff5252; font-weight: bold; font-size: 11px;")
            else:
                mod_pct = min(100.0, (demand / max(1.0, nominal)) * 100.0)
                self.lbl_ac_diag.setText(f"✓ Capacidad Suficiente: {nominal:,.0f} BTU/h instalados ({nominal/12000.0:.1f} TR) | Modulación Inverter: {mod_pct:.0f}%")
                self.lbl_ac_diag.setStyleSheet("color: #69f0ae; font-weight: bold; font-size: 11px;")
        if hasattr(self, "card_cmp") and self.last_results:
            peak_r = max(self.last_results, key=lambda x: x.get("t_int_level_1", 0.0))
            cmp_val = peak_r.get("cmp_level_1", 0.0)
            ppd_val = peak_r.get("ppd_level_1", 5.0)
            sens_val = peak_r.get("cmp_sensation_1", "Neutro")
            cmp_lbl = self.card_cmp.findChild(QLabel, "val_lbl")
            if cmp_lbl:
                cmp_lbl.setText(f"CMP {cmp_val:+.2f} ({sens_val})")
                cmp_lbl.setToolTip(f"Confort Medio Predicho (RNE EM.110 / ISO 7730 / Fanger PMV)\nValor CMP: {cmp_val:+.2f} | PPD: {ppd_val:.1f}% insatisfechos.")

        if hasattr(self, "lbl_t_ext_range") and self.last_results:
            t_min = min(r["t_ext"] for r in self.last_results)
            t_max = max(r["t_ext"] for r in self.last_results)
            self.lbl_t_ext_range.setText(f"Rango Diario {season.capitalize()}: Mín {t_min:.1f} °C / Máx {t_max:.1f} °C")

        # Actualizar ocupación en visores
        if hasattr(self, "viewer_3d"):
            self.viewer_3d.set_occupancy(occ_1, occ_2 if num_floors == 2 else 0, heat_per_person)
        if hasattr(self, "floor_plan_widget"):
            self.floor_plan_widget.set_occupancy(occ_1, occ_2 if num_floors == 2 else 0, heat_per_person)

        # Actualizar 3D y 2D a la hora actual del slider
        self._on_equipment_pos_changed()
        curr_h = self.viewer_3d.current_hour if hasattr(self, "viewer_3d") else 14
        self._on_hour_slider_changed(curr_h)

        # Actualizar Memoria de Cálculo Técnica (EM.110 / ASHRAE 55)
        self._update_calculation_memory(z1, z2, assembly)

    def _update_calculation_memory(self, z1, z2, assembly):
        """Genera y sincroniza la memoria de cálculo en Markdown y HTML."""
        if not hasattr(self, "calc_memory_widget") or not self.last_results:
            return
        try:
            has_ac = self.chk_ac.isChecked() if hasattr(self, "chk_ac") else False
            has_eolic = self.chk_eolic.isChecked() if hasattr(self, "chk_eolic") else True
            has_exhaust = self.chk_exhaust.isChecked() if hasattr(self, "chk_exhaust") else False
            has_supply = self.chk_supply.isChecked() if hasattr(self, "chk_supply") else False
            has_fan = self.chk_fan.isChecked() if hasattr(self, "chk_fan") else False

            md_text = CalculationMemoryGenerator.generate_markdown(
                project_name="Simulación Térmica y Bioclimática EM.110",
                city_climate=self.current_city,
                season_name=self.combo_season.currentText() if hasattr(self, "combo_season") else "Verano",
                north_deg=float(self.spin_north.value()) if hasattr(self, "spin_north") else 0.0,
                results=self.last_results,
                zone_1=z1,
                zone_2=z2,
                roof_assembly=assembly,
                slab_material=self.selected_slab,
                eolic_units=self.eolic_units,
                exhaust_units=self.exhaust_units,
                supply_units=self.supply_units,
                fan_units=self.fan_units,
                ac_units=self.ac_units,
                chk_ac_on=has_ac,
                chk_eolic_on=has_eolic,
                chk_exhaust_on=has_exhaust,
                chk_supply_on=has_supply,
                chk_fan_on=has_fan,
            )
            html_text = CalculationMemoryGenerator.generate_html(md_text)
            self.calc_memory_widget.set_content(md_text, html_text)
        except Exception as e:
            print(f"Aviso actualizando memoria de cálculo: {e}")

    def _apply_ac_preset(self):
        """Calcula las coordenadas 3D del Split A/C basado en el preset y pared seleccionada."""
        if not hasattr(self, "combo_ac_preset") or not hasattr(self, "viewer_3d"):
            return
        preset = self.combo_ac_preset.currentText()
        is_level_2 = (self.combo_curr_ac_level.currentIndex() == 1) if hasattr(self, "combo_curr_ac_level") else False

        hb = self.viewer_3d.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]
        zmin = hb["zmin"]
        lx, ly = hb["len_x"], hb["len_y"]

        h_piso = self.spin_height_piso.value() if hasattr(self, "spin_height_piso") else 2.85
        z_floor = zmin + (h_piso if is_level_2 else 0.0)
        h_m = self.slider_ac_height.value() / 10.0
        z = z_floor + min(h_m, h_piso - 0.15)

        pct = self.slider_ac_wall_pos.value() / 100.0
        self.lbl_ac_wall_pos.setText(f"{self.slider_ac_wall_pos.value()}% a lo largo del muro")
        self.lbl_ac_height.setText(f"{h_m:.1f} m sobre nivel de piso terminado")

        if "Personalizado" not in preset:
            if "Pared Sur" in preset:
                x = xmin + pct * lx
                y = ymin + 0.15
            elif "Pared Norte" in preset:
                x = xmin + pct * lx
                y = ymax - 0.15
            elif "Pared Oeste" in preset:
                x = xmin + 0.15
                y = ymin + pct * ly
            elif "Pared Este" in preset:
                x = xmax - 0.15
                y = ymin + pct * ly
            elif "Centro" in preset:
                x = xmin + lx / 2.0
                y = ymin + ly / 2.0
            else:
                x = xmin + pct * lx
                y = ymin + 0.15

            self.spin_ac_x.blockSignals(True)
            self.spin_ac_y.blockSignals(True)
            self.spin_ac_z.blockSignals(True)
            self.spin_ac_x.setValue(x)
            self.spin_ac_y.setValue(y)
            self.spin_ac_z.setValue(z)
            self.spin_ac_x.blockSignals(False)
            self.spin_ac_y.blockSignals(False)
            self.spin_ac_z.blockSignals(False)

        idx = self.combo_ac_select.currentIndex() if hasattr(self, "combo_ac_select") else 0
        if 0 <= idx < len(self.ac_units):
            self.ac_units[idx]["level"] = 2 if is_level_2 else 1
            self.ac_units[idx]["wall"] = preset
            self.ac_units[idx]["offset_pct"] = self.slider_ac_wall_pos.value()
            self.ac_units[idx]["height_m"] = h_m
            self.ac_units[idx]["x"] = self.spin_ac_x.value()
            self.ac_units[idx]["y"] = self.spin_ac_y.value()
            self.ac_units[idx]["z"] = self.spin_ac_z.value()

        self._on_equipment_pos_changed()

    def _apply_fan_preset(self):
        """Calcula la posición 3D del Ventilador de Confort basada en presets y sliders."""
        if not hasattr(self, "combo_fan_preset") or not hasattr(self, "viewer_3d"):
            return
        preset = self.combo_fan_preset.currentText()
        is_level_2 = (self.combo_curr_fan_level.currentIndex() == 1) if hasattr(self, "combo_curr_fan_level") else False

        hb = self.viewer_3d.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]
        zmin = hb["zmin"]
        lx, ly = hb["len_x"], hb["len_y"]

        h_piso = self.spin_height_piso.value() if hasattr(self, "spin_height_piso") else 2.85
        z_floor = zmin + (h_piso if is_level_2 else 0.0)
        z = z_floor + min(2.55, h_piso - 0.20)

        pct_x = self.slider_fan_x.value() / 100.0
        pct_y = self.slider_fan_y.value() / 100.0

        if "Personalizado" not in preset:
            if "Centro" in preset:
                x = xmin + 0.50 * lx
                y = ymin + 0.50 * ly
            elif "Frontal" in preset:
                x = xmin + pct_x * lx
                y = ymin + 0.25 * ly
            elif "Posterior" in preset:
                x = xmin + pct_x * lx
                y = ymin + 0.75 * ly
            else:
                x = xmin + pct_x * lx
                y = ymin + pct_y * ly

            self.spin_fan_x.blockSignals(True)
            self.spin_fan_y.blockSignals(True)
            self.spin_fan_z.blockSignals(True)
            self.spin_fan_x.setValue(x)
            self.spin_fan_y.setValue(y)
            self.spin_fan_z.setValue(z)
            self.spin_fan_x.blockSignals(False)
            self.spin_fan_y.blockSignals(False)
            self.spin_fan_z.blockSignals(False)

        idx = self.combo_fan_select.currentIndex() if hasattr(self, "combo_fan_select") else 0
        if 0 <= idx < len(self.fan_units):
            self.fan_units[idx]["level"] = 2 if is_level_2 else 1
            self.fan_units[idx]["preset"] = preset
            self.fan_units[idx]["offset_x"] = self.slider_fan_x.value()
            self.fan_units[idx]["offset_y"] = self.slider_fan_y.value()
            self.fan_units[idx]["x"] = self.spin_fan_x.value()
            self.fan_units[idx]["y"] = self.spin_fan_y.value()
            self.fan_units[idx]["z"] = self.spin_fan_z.value()

        self._on_equipment_pos_changed()

    def _apply_eolic_preset(self):
        """Calcula la posición 3D del Extractor Eólico en cubierta según preset y desplazamiento."""
        if not hasattr(self, "combo_eolic_preset") or not hasattr(self, "viewer_3d"):
            return
        preset = self.combo_eolic_preset.currentText()

        hb = self.viewer_3d.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]
        zmax = hb["zmax"]
        lx, ly = hb["len_x"], hb["len_y"]

        pct = self.slider_eolic_pos.value() / 100.0
        self.lbl_eolic_pos.setText(f"{self.slider_eolic_pos.value()}% a lo largo del techo")

        if "Personalizado" not in preset:
            if "Cumbrera" in preset:
                x = xmin + pct * lx
                y = ymin + 0.50 * ly
                z = zmax + 0.15
            elif "Frontal" in preset:
                x = xmin + pct * lx
                y = ymin + 0.20 * ly
                z = zmax - 0.20
            elif "Posterior" in preset:
                x = xmin + pct * lx
                y = ymin + 0.80 * ly
                z = zmax - 0.20
            elif "Este" in preset:
                x = xmax - 0.25 * lx
                y = ymin + pct * ly
                z = zmax - 0.20
            elif "Oeste" in preset:
                x = xmin + 0.25 * lx
                y = ymin + pct * ly
                z = zmax - 0.20
            else:
                x = xmin + pct * lx
                y = ymin + 0.50 * ly
                z = zmax + 0.15

            self.spin_eolic_x.blockSignals(True)
            self.spin_eolic_y.blockSignals(True)
            self.spin_eolic_z.blockSignals(True)
            self.spin_eolic_x.setValue(x)
            self.spin_eolic_y.setValue(y)
            self.spin_eolic_z.setValue(z)
            self.spin_eolic_x.blockSignals(False)
            self.spin_eolic_y.blockSignals(False)
            self.spin_eolic_z.blockSignals(False)

        idx = self.combo_eolic_select.currentIndex() if hasattr(self, "combo_eolic_select") else 0
        if 0 <= idx < len(self.eolic_units):
            self.eolic_units[idx]["preset"] = preset
            self.eolic_units[idx]["offset_pct"] = self.slider_eolic_pos.value()
            self.eolic_units[idx]["x"] = self.spin_eolic_x.value()
            self.eolic_units[idx]["y"] = self.spin_eolic_y.value()
            self.eolic_units[idx]["z"] = self.spin_eolic_z.value()

        self._on_equipment_pos_changed()

    def _apply_exhaust_preset(self):
        """Calcula la posición 3D del Extractor Mecánico según preset y pared."""
        if not hasattr(self, "combo_exhaust_preset") or not hasattr(self, "viewer_3d"):
            return
        preset = self.combo_exhaust_preset.currentText()
        is_level_2 = (self.combo_curr_exhaust_level.currentIndex() == 1) if hasattr(self, "combo_curr_exhaust_level") else False

        hb = self.viewer_3d.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]
        zmin, zmax = hb["zmin"], hb["zmax"]
        lx, ly = hb["len_x"], hb["len_y"]

        h_piso = self.spin_height_piso.value() if hasattr(self, "spin_height_piso") else 2.85
        z_floor = zmin + (h_piso if is_level_2 else 0.0)
        z = z_floor + min(2.4, h_piso - 0.20)

        pct = self.slider_exhaust_pos.value() / 100.0
        self.lbl_exhaust_pos.setText(f"{self.slider_exhaust_pos.value()}% a lo largo de la pared")

        if "Personalizado" not in preset:
            if "Techo" in preset:
                x = xmin + pct * lx
                y = ymin + 0.50 * ly
                z = zmax + 0.15
            elif "Pared Sur" in preset:
                x = xmin + pct * lx
                y = ymin + 0.15
            elif "Pared Norte" in preset:
                x = xmin + pct * lx
                y = ymax - 0.15
            elif "Pared Oeste" in preset:
                x = xmin + 0.15
                y = ymin + pct * ly
            elif "Pared Este" in preset:
                x = xmax - 0.15
                y = ymin + pct * ly
            else:
                x = xmin + pct * lx
                y = ymax - 0.15

            self.spin_exhaust_x.blockSignals(True)
            self.spin_exhaust_y.blockSignals(True)
            self.spin_exhaust_z.blockSignals(True)
            self.spin_exhaust_x.setValue(x)
            self.spin_exhaust_y.setValue(y)
            self.spin_exhaust_z.setValue(z)
            self.spin_exhaust_x.blockSignals(False)
            self.spin_exhaust_y.blockSignals(False)
            self.spin_exhaust_z.blockSignals(False)

        idx = self.combo_exhaust_select.currentIndex() if hasattr(self, "combo_exhaust_select") else 0
        if 0 <= idx < len(self.exhaust_units):
            self.exhaust_units[idx]["level"] = 2 if is_level_2 else 1
            self.exhaust_units[idx]["wall"] = preset
            self.exhaust_units[idx]["offset_pct"] = self.slider_exhaust_pos.value()
            self.exhaust_units[idx]["x"] = self.spin_exhaust_x.value()
            self.exhaust_units[idx]["y"] = self.spin_exhaust_y.value()
            self.exhaust_units[idx]["z"] = self.spin_exhaust_z.value()

        self._on_equipment_pos_changed()

    def _apply_supply_preset(self):
        """Calcula la posición 3D del Inyector de Aire Exterior según preset y pared."""
        if not hasattr(self, "combo_supply_preset") or not hasattr(self, "viewer_3d"):
            return
        preset = self.combo_supply_preset.currentText()
        is_level_2 = (self.combo_curr_supply_level.currentIndex() == 1) if hasattr(self, "combo_curr_supply_level") else False

        hb = self.viewer_3d.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]
        zmin = hb["zmin"]
        lx, ly = hb["len_x"], hb["len_y"]

        h_piso = self.spin_height_piso.value() if hasattr(self, "spin_height_piso") else 2.85
        z_floor = zmin + (h_piso if is_level_2 else 0.0)
        z = z_floor + min(2.0, h_piso - 0.30)

        pct = self.slider_supply_pos.value() / 100.0
        self.lbl_supply_pos.setText(f"{self.slider_supply_pos.value()}% a lo largo de la pared")

        if "Personalizado" not in preset:
            if "Pared Sur" in preset:
                x = xmin + pct * lx
                y = ymin + 0.15
            elif "Pared Norte" in preset:
                x = xmin + pct * lx
                y = ymax - 0.15
            elif "Pared Oeste" in preset:
                x = xmin + 0.15
                y = ymin + pct * ly
            elif "Pared Este" in preset:
                x = xmax - 0.15
                y = ymin + pct * ly
            else:
                x = xmin + pct * lx
                y = ymin + 0.15

            self.spin_supply_x.blockSignals(True)
            self.spin_supply_y.blockSignals(True)
            self.spin_supply_z.blockSignals(True)
            self.spin_supply_x.setValue(x)
            self.spin_supply_y.setValue(y)
            self.spin_supply_z.setValue(z)
            self.spin_supply_x.blockSignals(False)
            self.spin_supply_y.blockSignals(False)
            self.spin_supply_z.blockSignals(False)

        idx = self.combo_supply_select.currentIndex() if hasattr(self, "combo_supply_select") else 0
        if 0 <= idx < len(self.supply_units):
            self.supply_units[idx]["level"] = 2 if is_level_2 else 1
            self.supply_units[idx]["wall"] = preset
            self.supply_units[idx]["offset_pct"] = self.slider_supply_pos.value()
            self.supply_units[idx]["x"] = self.spin_supply_x.value()
            self.supply_units[idx]["y"] = self.spin_supply_y.value()
            self.supply_units[idx]["z"] = self.spin_supply_z.value()

        self._on_equipment_pos_changed()

    def _on_equipment_pos_changed(self):
        """Sincroniza todas las unidades individuales con los visores 3D y 2D."""
        if hasattr(self, "combo_eolic_select"):
            idx = self.combo_eolic_select.currentIndex()
            if 0 <= idx < len(self.eolic_units):
                self.eolic_units[idx]["x"] = self.spin_eolic_x.value()
                self.eolic_units[idx]["y"] = self.spin_eolic_y.value()
                self.eolic_units[idx]["z"] = self.spin_eolic_z.value()

        if hasattr(self, "combo_exhaust_select"):
            idx = self.combo_exhaust_select.currentIndex()
            if 0 <= idx < len(self.exhaust_units):
                self.exhaust_units[idx]["x"] = self.spin_exhaust_x.value()
                self.exhaust_units[idx]["y"] = self.spin_exhaust_y.value()
                self.exhaust_units[idx]["z"] = self.spin_exhaust_z.value()

        if hasattr(self, "combo_supply_select"):
            idx = self.combo_supply_select.currentIndex()
            if 0 <= idx < len(self.supply_units):
                self.supply_units[idx]["x"] = self.spin_supply_x.value()
                self.supply_units[idx]["y"] = self.spin_supply_y.value()
                self.supply_units[idx]["z"] = self.spin_supply_z.value()

        if hasattr(self, "combo_fan_select"):
            idx = self.combo_fan_select.currentIndex()
            if 0 <= idx < len(self.fan_units):
                self.fan_units[idx]["x"] = self.spin_fan_x.value()
                self.fan_units[idx]["y"] = self.spin_fan_y.value()
                self.fan_units[idx]["z"] = self.spin_fan_z.value()

        if hasattr(self, "combo_ac_select"):
            idx = self.combo_ac_select.currentIndex()
            if 0 <= idx < len(self.ac_units):
                self.ac_units[idx]["x"] = self.spin_ac_x.value()
                self.ac_units[idx]["y"] = self.spin_ac_y.value()
                self.ac_units[idx]["z"] = self.spin_ac_z.value()

        eolic_active = (self.chk_eolic.isChecked() and any(u.get("enabled", True) for u in self.eolic_units)) if hasattr(self, "chk_eolic") else True

        if hasattr(self, "viewer_3d") and hasattr(self, "spin_ac_x"):
            self.viewer_3d.set_equipment_state(
                ac_on=self.chk_ac.isChecked(),
                ac_xyz=[self.spin_ac_x.value(), self.spin_ac_y.value(), self.spin_ac_z.value()],
                ac_qty=len(self.ac_units),
                fan_on=self.chk_fan.isChecked(),
                fan_xyz=[self.spin_fan_x.value(), self.spin_fan_y.value(), self.spin_fan_z.value()],
                fan_qty=len(self.fan_units),
                eolic_on=eolic_active,
                eolic_xyz=[self.spin_eolic_x.value(), self.spin_eolic_y.value(), self.spin_eolic_z.value()],
                eolic_qty=len(self.eolic_units),
                exhaust_on=self.chk_exhaust.isChecked(),
                exhaust_xyz=[self.spin_exhaust_x.value(), self.spin_exhaust_y.value(), self.spin_exhaust_z.value()],
                exhaust_qty=len(self.exhaust_units),
                supply_on=self.chk_supply.isChecked(),
                supply_xyz=[self.spin_supply_x.value(), self.spin_supply_y.value(), self.spin_supply_z.value()],
                supply_qty=len(self.supply_units),
                ac_units=self.ac_units,
                fan_units=self.fan_units,
                eolic_units=self.eolic_units,
                exhaust_units=self.exhaust_units,
                supply_units=self.supply_units,
            )

        if hasattr(self, "floor_plan_widget"):
            self.floor_plan_widget.set_equipment_state(
                ac_on=self.chk_ac.isChecked(),
                ac_xyz=[self.spin_ac_x.value(), self.spin_ac_y.value(), self.spin_ac_z.value()],
                ac_qty=len(self.ac_units),
                fan_on=self.chk_fan.isChecked(),
                fan_xyz=[self.spin_fan_x.value(), self.spin_fan_y.value(), self.spin_fan_z.value()],
                fan_qty=len(self.fan_units),
                eolic_on=eolic_active,
                eolic_xyz=[self.spin_eolic_x.value(), self.spin_eolic_y.value(), self.spin_eolic_z.value()],
                eolic_qty=len(self.eolic_units),
                exhaust_on=self.chk_exhaust.isChecked(),
                exhaust_xyz=[self.spin_exhaust_x.value(), self.spin_exhaust_y.value(), self.spin_exhaust_z.value()],
                exhaust_qty=len(self.exhaust_units),
                supply_on=self.chk_supply.isChecked(),
                supply_xyz=[self.spin_supply_x.value(), self.spin_supply_y.value(), self.spin_supply_z.value()],
                supply_qty=len(self.supply_units),
                ac_units=self.ac_units,
                fan_units=self.fan_units,
                eolic_units=self.eolic_units,
                exhaust_units=self.exhaust_units,
                supply_units=self.supply_units,
            )

    def _on_floor_plan_equipment_moved(self, eq_type: str, x: float, y: float):
        """Sincroniza la nueva posición del equipo movido interactivamente en la planta 2D."""
        if eq_type == "ac":
            idx = self.combo_ac_select.currentIndex() if hasattr(self, "combo_ac_select") else 0
            if 0 <= idx < len(self.ac_units):
                self.ac_units[idx]["x"] = x
                self.ac_units[idx]["y"] = y
            if hasattr(self, "spin_ac_x") and hasattr(self, "spin_ac_y"):
                self.spin_ac_x.blockSignals(True)
                self.spin_ac_y.blockSignals(True)
                self.spin_ac_x.setValue(x)
                self.spin_ac_y.setValue(y)
                self.spin_ac_x.blockSignals(False)
                self.spin_ac_y.blockSignals(False)
            if hasattr(self, "chk_ac") and not self.chk_ac.isChecked():
                self.chk_ac.setChecked(True)
        elif eq_type == "exhaust":
            idx = self.combo_exhaust_select.currentIndex() if hasattr(self, "combo_exhaust_select") else 0
            if 0 <= idx < len(self.exhaust_units):
                self.exhaust_units[idx]["x"] = x
                self.exhaust_units[idx]["y"] = y
            if hasattr(self, "spin_exhaust_x") and hasattr(self, "spin_exhaust_y"):
                self.spin_exhaust_x.blockSignals(True)
                self.spin_exhaust_y.blockSignals(True)
                self.spin_exhaust_x.setValue(x)
                self.spin_exhaust_y.setValue(y)
                self.spin_exhaust_x.blockSignals(False)
                self.spin_exhaust_y.blockSignals(False)
            if hasattr(self, "chk_exhaust") and not self.chk_exhaust.isChecked():
                self.chk_exhaust.setChecked(True)
        elif eq_type == "supply":
            idx = self.combo_supply_select.currentIndex() if hasattr(self, "combo_supply_select") else 0
            if 0 <= idx < len(self.supply_units):
                self.supply_units[idx]["x"] = x
                self.supply_units[idx]["y"] = y
            if hasattr(self, "spin_supply_x") and hasattr(self, "spin_supply_y"):
                self.spin_supply_x.blockSignals(True)
                self.spin_supply_y.blockSignals(True)
                self.spin_supply_x.setValue(x)
                self.spin_supply_y.setValue(y)
                self.spin_supply_x.blockSignals(False)
                self.spin_supply_y.blockSignals(False)
            if hasattr(self, "chk_supply") and not self.chk_supply.isChecked():
                self.chk_supply.setChecked(True)
        elif eq_type == "fan":
            idx = self.combo_fan_select.currentIndex() if hasattr(self, "combo_fan_select") else 0
            if 0 <= idx < len(self.fan_units):
                self.fan_units[idx]["x"] = x
                self.fan_units[idx]["y"] = y
            if hasattr(self, "spin_fan_x") and hasattr(self, "spin_fan_y"):
                self.spin_fan_x.blockSignals(True)
                self.spin_fan_y.blockSignals(True)
                self.spin_fan_x.setValue(x)
                self.spin_fan_y.setValue(y)
                self.spin_fan_x.blockSignals(False)
                self.spin_fan_y.blockSignals(False)
            if hasattr(self, "chk_fan") and not self.chk_fan.isChecked():
                self.chk_fan.setChecked(True)

        self._on_equipment_pos_changed()
        self.run_simulation()
    def _on_hour_slider_changed(self, hour: int):
        if not self.last_results:
            return
        h_data = self.last_results[hour]
        north = float(self.spin_north.value())
        if hasattr(self, "lbl_t_ext_now"):
            self.lbl_t_ext_now.setText(f"T. Exterior ({hour:02d}:00): {h_data['t_ext']:.1f} °C")
        if hasattr(self, "viewer_3d"):
            self.viewer_3d.set_temperatures(
                t1=h_data["t_int_level_1"],
                t2=h_data["t_int_level_2"],
                elev=h_data["solar_elevation"],
                azim=h_data["solar_azimuth"],
                north_deg=north,
            )
        if hasattr(self, "floor_plan_widget"):
            self.floor_plan_widget.set_temperatures(
                t1=h_data["t_int_level_1"],
                t2=h_data["t_int_level_2"],
                elev=h_data["solar_elevation"],
                azim=h_data["solar_azimuth"],
                north_deg=north,
            )

    def _export_technical_report(self):
        if not self.last_results:
            QMessageBox.warning(self, "Aviso", "Aún no hay resultados de simulación para exportar.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Informe Técnico Bioclimático",
            f"Informe_Termico_{self.current_city.region}.html",
            "Documento HTML (*.html);;Todos los archivos (*.*)"
        )
        if not save_path:
            return

        # Ensambles actuales
        assembly = RoofCeilingAssembly(
            name="Ensamble Techo",
            roof_material=self.selected_roof,
            ceiling_material=self.selected_ceiling,
            has_air_cavity=(self.selected_ceiling is not None),
            cavity_ventilated=self.chk_cavity_vent.isChecked(),
        )

        # Evaluación de la Norma EM.110
        em110_res = EM110Evaluator.evaluate(
            region=self.current_city.region,
            u_roof=assembly.u_value,
            u_wall=self.selected_wall.u_value
        )

        z1 = ThermalZoneConfig(
            name="Nivel 1",
            level_number=1,
            wall_material=self.selected_wall,
            window_material=self.selected_window
        )
        z2 = ThermalZoneConfig(
            name="Nivel 2",
            level_number=2,
            wall_material=self.selected_wall,
            window_material=self.selected_window
        ) if self.spin_floors.value() == 2 else None

        ThermalReportGenerator.generate_html_report(
            project_name=os.path.basename(save_path).replace(".html", ""),
            city_name=self.current_city.name,
            season_name=self.combo_season.currentText(),
            north_deg=float(self.spin_north.value()),
            results=self.last_results,
            zone_1_cfg=z1,
            zone_2_cfg=z2,
            roof_assembly=assembly,
            em110_results=em110_res,
            output_filepath=save_path
        )

        # Abrir en el navegador de Windows
        try:
            os.startfile(save_path)
        except Exception:
            pass

        self.statusBar().showMessage(f"Informe guardado y abierto con éxito: {save_path}", 6000)

    def _apply_dark_theme(self):
        """Aplica un tema oscuro profesional estilo ingeniería / CAD."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a24;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #333344;
                background-color: #20202c;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #1a1a24;
                color: #aaaaaa;
                padding: 6px 10px;
                border: 1px solid #2d2d3d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #2b2b3b;
                color: #ffffff;
                font-weight: bold;
                border-color: #0288d1;
            }
            QGroupBox {
                border: 1px solid #3d3d4f;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 10px;
                font-weight: bold;
                color: #bbbbcc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QComboBox, QLineEdit {
                background-color: #2a2a38;
                border: 1px solid #444458;
                border-radius: 4px;
                padding: 4px 6px;
                color: #ffffff;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2a2a38;
                border: 1px solid #444458;
                border-radius: 4px;
                padding: 4px 6px;
                padding-right: 22px;
                color: #ffffff;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 18px;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #0288d1;
            }
            QPushButton {
                background-color: #333348;
                border: 1px solid #4f4f6a;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #444460;
                border-color: #0288d1;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #333344;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0288d1;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #0288d1;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QSplitter::handle:horizontal {
                background: #2a2a3e;
                width: 6px;
                border-left: 1px solid #383850;
                border-right: 1px solid #383850;
            }
            QSplitter::handle:horizontal:hover {
                background: #00e5ff;
            }
        """)
