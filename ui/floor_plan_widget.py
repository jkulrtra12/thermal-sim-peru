"""
Widget 2D de Mapas de Calor por Planta y Cortes por Altura Z.
Visualización arquitectónica precisa en planta con curvas de nivel (isotermas),
estratificación térmica vertical, carpintería (muros, puertas, ventanas),
escala bioclimática fija absoluta (18°C - 40°C) y colocación interactiva de equipos HVAC con snap a muros.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import matplotlib as mpl
import matplotlib.colors as mcolors

from geometry.building_model import BuildingGeometry3D


class FloorPlanWidget(QWidget):
    """Visor 2D de Cortes Térmicos en Planta a diferentes alturas Z con manipulación interactiva de equipos."""
    height_changed = pyqtSignal(float)
    equipment_moved = pyqtSignal(str, float, float)  # tipo ('ac', 'exhaust', 'supply', 'fan'), x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.building_model: BuildingGeometry3D = BuildingGeometry3D.create_default_building()
        self.t_level_1: float = 26.0
        self.t_level_2: float = 31.0
        self.solar_elev: float = 45.0
        self.solar_azim: float = 238.0
        self.north_deg: float = 0.0

        # Ocupación
        self.occupants_l1: int = 15
        self.occupants_l2: int = 15
        self.occupant_heat_w: float = 100.0

        # Estado de equipos
        self.ac_enabled: bool = False
        self.ac_pos: list = [4.0, 0.15, 2.3]
        self.ac_qty: int = 1

        self.fan_enabled: bool = True
        self.fan_pos: list = [4.0, 2.5, 2.6]
        self.fan_qty: int = 1

        self.eolic_enabled: bool = True
        self.eolic_pos: list = [4.0, 2.5, 5.6]
        self.eolic_qty: int = 2

        self.exhaust_enabled: bool = False
        self.exhaust_pos: list = [4.0, 4.85, 2.3]
        self.exhaust_qty: int = 1

        self.supply_enabled: bool = False
        self.supply_pos: list = [4.0, 0.15, 2.0]
        self.supply_qty: int = 1

        # Altura actual evaluada
        self.current_z: float = 1.10  # Altura de confort sentado
        self.color_palette: str = "turbo"
        self.use_fixed_scale: bool = True  # Escala térmica absoluta fija 18°C a 40°C
        self.show_isolines: bool = True
        self.show_equipment: bool = True
        self.cbar = None
        self._dragging_equipment: bool = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Canvas Matplotlib 2D con Eje Dedicado para Colorbar
        self.fig = Figure(facecolor="#181820")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_axes([0.08, 0.08, 0.79, 0.86])
        self.ax.set_facecolor("#181820")
        self.cax = self.fig.add_axes([0.89, 0.16, 0.022, 0.68])
        self.cax.set_facecolor("#181820")
        layout.addWidget(self.canvas)

        # Conectar eventos de ratón para mover equipos interactivamente sobre el plano 2D
        self.canvas.mpl_connect("button_press_event", self._on_canvas_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_canvas_motion)
        self.canvas.mpl_connect("button_release_event", self._on_canvas_release)

        # 2. Barra Superior de Control de Planta y Altura Z
        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(6, 4, 6, 2)

        # Selector de Planta / Nivel
        self.combo_floor = QComboBox()
        self.combo_floor.addItems(["Planta Nivel 1", "Planta Nivel 2", "Corte Libre por Altura Z"])
        self.combo_floor.currentIndexChanged.connect(self._on_floor_mode_changed)
        self.combo_floor.setFixedWidth(130)
        tools_layout.addWidget(self.combo_floor)

        # Presets Rápidos de Altura Z (Dinámicos según el modelo)
        self.combo_z_preset = QComboBox()
        self.combo_z_preset.setMinimumWidth(230)
        self.combo_z_preset.setStyleSheet("QComboBox { min-width: 220px; } QComboBox QAbstractItemView { min-width: 280px; }")
        self.combo_z_preset.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        if self.combo_z_preset.view():
            self.combo_z_preset.view().setMinimumWidth(290)
            self.combo_z_preset.view().setTextElideMode(Qt.TextElideMode.ElideNone)
        self.combo_z_preset.currentIndexChanged.connect(self._on_preset_changed)
        tools_layout.addWidget(self.combo_z_preset)

        # Slider de Altura Z
        self.lbl_z = QLabel("Z: 1.10 m")
        self.lbl_z.setStyleSheet("font-weight: bold; font-size: 11px; color: #00e5ff;")
        tools_layout.addWidget(self.lbl_z)

        self.slider_z = QSlider(Qt.Orientation.Horizontal)
        self.slider_z.setRange(0, 100)  # 0 a 10.0 m (paso 0.10 m)
        self.slider_z.setValue(11)      # 1.10 m
        self.slider_z.valueChanged.connect(self._on_slider_z_changed)
        tools_layout.addWidget(self.slider_z)

        # Escala fija vs relativa
        self.chk_fixed_scale = QCheckBox("Escala Absoluta (18-40°C)")
        self.chk_fixed_scale.setToolTip("Escala térmica estándar fija: Verde = Confort 21-26°C, Amarillo = 27-29°C, Naranja = 30-33°C, Rojo = >34°C. Evita que 30°C se pinte de azul.")
        self.chk_fixed_scale.setChecked(True)
        self.chk_fixed_scale.toggled.connect(self._toggle_fixed_scale)
        tools_layout.addWidget(self.chk_fixed_scale)

        # Paleta de Color
        self.combo_pal = QComboBox()
        self.combo_pal.addItems(["turbo (Google)", "jet (Clásico)", "coolwarm (Frío-Calor)", "plasma (Contraste)"])
        self.combo_pal.currentIndexChanged.connect(self._on_palette_changed)
        self.combo_pal.setFixedWidth(115)
        tools_layout.addWidget(self.combo_pal)

        self.chk_iso = QCheckBox("Isotermas")
        self.chk_iso.setChecked(True)
        self.chk_iso.toggled.connect(self._toggle_isolines)
        tools_layout.addWidget(self.chk_iso)

        self.chk_eq = QCheckBox("Equipos")
        self.chk_eq.setChecked(True)
        self.chk_eq.toggled.connect(self._toggle_equipment)
        tools_layout.addWidget(self.chk_eq)

        layout.addLayout(tools_layout)

        # 3. Barra Inferior de Manipulación Interactiva de Equipos (Snap a Muros)
        move_bar = QHBoxLayout()
        move_bar.setContentsMargins(6, 2, 6, 4)

        lbl_drag_hint = QLabel("🖱️ Colocar en Plano (Snap a Muros):")
        lbl_drag_hint.setStyleSheet("color: #ffb74d; font-weight: bold; font-size: 11px;")
        move_bar.addWidget(lbl_drag_hint)

        self.combo_move_tool = QComboBox()
        self.combo_move_tool.addItems([
            "✋ Solo Visualizar / Navegar",
            "❄️ Mover A/C Split (Snap a Pared)",
            "💨 Mover Extractor Mecánico (Snap a Pared)",
            "🌬️ Mover Inyector de Aire (Snap a Pared)",
            "🌀 Mover Ventilador de Confort (Interior)"
        ])
        self.combo_move_tool.setFixedWidth(270)
        self.combo_move_tool.currentIndexChanged.connect(self._on_move_tool_changed)
        move_bar.addWidget(self.combo_move_tool)

        self.lbl_move_status = QLabel("Haz clic sobre el plano para colocar el equipo directamente en el muro deseado.")
        self.lbl_move_status.setStyleSheet("color: #90a4ae; font-size: 10.5px; font-style: italic;")
        move_bar.addWidget(self.lbl_move_status)
        move_bar.addStretch()

        layout.addLayout(move_bar)

        # Actualizar presets dinámicos iniciales y render
        self.update_z_presets()
        self.render_plan()

    def update_z_presets(self):
        """Calcula dinámicamente los cortes predefinidos de altura según las cotas reales del modelo."""
        hb = self.get_house_bounds()
        zmin = hb["zmin"]
        zmax = hb["zmax"]
        has_level_2 = any(s.level == 2 for s in self.building_model.surfaces if s.surface_type != "neighbor_wall") or (hb["height"] > 3.4)

        z_floor_1 = zmin + 0.10
        z_sit_1 = zmin + 1.10
        z_stand_1 = zmin + 1.70
        z_ac_1 = min(zmax - 0.3, zmin + 2.30)

        self.combo_z_preset.blockSignals(True)
        self.combo_z_preset.clear()
        self.combo_z_preset.addItem(f"📍 Suelo N1 (Z = {z_floor_1:.2f} m)", z_floor_1)
        self.combo_z_preset.addItem(f"📍 Sentado N1 (Z = {z_sit_1:.2f} m)", z_sit_1)
        self.combo_z_preset.addItem(f"📍 Respiración N1 (Z = {z_stand_1:.2f} m)", z_stand_1)
        self.combo_z_preset.addItem(f"📍 A/C Split N1 (Z = {z_ac_1:.2f} m)", z_ac_1)

        if has_level_2:
            z_floor_2 = max(zmin + 2.6, (zmin + zmax) * 0.48)
            z_conf_2 = min(zmax - 0.4, z_floor_2 + 1.10)
            self.combo_z_preset.addItem(f"📍 Suelo N2 (Z = {z_floor_2:.2f} m)", z_floor_2)
            self.combo_z_preset.addItem(f"📍 Confort Nivel 2 (Z = {z_conf_2:.2f} m)", z_conf_2)

        z_roof = max(z_floor_1 + 2.0, zmax - 0.25)
        self.combo_z_preset.addItem(f"📍 Bajo Techo (Z = {z_roof:.2f} m)", z_roof)
        self.combo_z_preset.addItem("⚙️ Personalizado (Slider)", None)
        self.combo_z_preset.setCurrentIndex(1)  # Confort sentado N1
        self.combo_z_preset.blockSignals(False)

    def _on_move_tool_changed(self):
        idx = self.combo_move_tool.currentIndex()
        if idx == 0:
            self.lbl_move_status.setText("Modo visualización activo.")
        elif idx == 1:
            self.lbl_move_status.setText("Haz clic o arrastra para colocar el A/C Split pegado a la pared perimetral.")
        elif idx == 2:
            self.lbl_move_status.setText("Haz clic o arrastra para colocar el Extractor Mecánico pegado al muro.")
        elif idx == 3:
            self.lbl_move_status.setText("Haz clic o arrastra para colocar el Inyector de Aire en el muro deseado.")
        elif idx == 4:
            self.lbl_move_status.setText("Haz clic o arrastra para situar el Ventilador de Confort en la planta.")

    def _on_canvas_press(self, event):
        if event.inaxes != self.ax or event.button != 1:
            return
        if self.combo_move_tool.currentIndex() == 0:
            return
        self._dragging_equipment = True
        self._handle_equipment_drag(event.xdata, event.ydata, is_final=False)

    def _on_canvas_motion(self, event):
        if not self._dragging_equipment or event.inaxes != self.ax:
            return
        self._handle_equipment_drag(event.xdata, event.ydata, is_final=False)

    def _on_canvas_release(self, event):
        if self._dragging_equipment:
            self._dragging_equipment = False
            if event.inaxes == self.ax and event.xdata is not None and event.ydata is not None:
                self._handle_equipment_drag(event.xdata, event.ydata, is_final=True)
            else:
                self.render_plan()

    def _handle_equipment_drag(self, x_click, y_click, is_final: bool = True):
        if x_click is None or y_click is None:
            return
        tool_idx = self.combo_move_tool.currentIndex()
        if tool_idx == 0:
            return

        hb = self.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]

        # Equipos adosados a muros (A/C, Extractor, Inyector): Snap magnético a la pared más cercana
        if tool_idx in [1, 2, 3]:
            d_south = abs(y_click - ymin)
            d_north = abs(y_click - ymax)
            d_west = abs(x_click - xmin)
            d_east = abs(x_click - xmax)
            min_dist = min(d_south, d_north, d_west, d_east)

            snap_inset = 0.15
            if min_dist == d_south:
                snap_x = float(np.clip(x_click, xmin + 0.3, xmax - 0.3))
                snap_y = ymin + snap_inset
                wall_name = "Pared Sur (Frontal)"
            elif min_dist == d_north:
                snap_x = float(np.clip(x_click, xmin + 0.3, xmax - 0.3))
                snap_y = ymax - snap_inset
                wall_name = "Pared Norte (Posterior)"
            elif min_dist == d_west:
                snap_x = xmin + snap_inset
                snap_y = float(np.clip(y_click, ymin + 0.3, ymax - 0.3))
                wall_name = "Pared Lateral Oeste"
            else:
                snap_x = xmax - snap_inset
                snap_y = float(np.clip(y_click, ymin + 0.3, ymax - 0.3))
                wall_name = "Pared Lateral Este"

            if tool_idx == 1:
                eq_type = "ac"
                self.ac_pos = [snap_x, snap_y, self.ac_pos[2] if len(self.ac_pos) > 2 else 2.3]
                self.ac_enabled = True
                self.lbl_move_status.setText(f"A/C Split adosado a {wall_name} en X={snap_x:.2f}m, Y={snap_y:.2f}m")
            elif tool_idx == 2:
                eq_type = "exhaust"
                self.exhaust_pos = [snap_x, snap_y, self.exhaust_pos[2] if len(self.exhaust_pos) > 2 else 2.3]
                self.exhaust_enabled = True
                self.lbl_move_status.setText(f"Extractor adosado a {wall_name} en X={snap_x:.2f}m, Y={snap_y:.2f}m")
            else:
                eq_type = "supply"
                self.supply_pos = [snap_x, snap_y, self.supply_pos[2] if len(self.supply_pos) > 2 else 2.0]
                self.supply_enabled = True
                self.lbl_move_status.setText(f"Inyector adosado a {wall_name} en X={snap_x:.2f}m, Y={snap_y:.2f}m")

            if is_final:
                self.equipment_moved.emit(eq_type, snap_x, snap_y)
            else:
                self.render_plan()

        elif tool_idx == 4:
            # Ventilador de confort: posición libre en la planta dentro del salón
            fan_x = float(np.clip(x_click, xmin + 0.4, xmax - 0.4))
            fan_y = float(np.clip(y_click, ymin + 0.4, ymax - 0.4))
            self.fan_pos = [fan_x, fan_y, self.fan_pos[2] if len(self.fan_pos) > 2 else 2.6]
            self.fan_enabled = True
            self.lbl_move_status.setText(f"Ventilador de confort situado en X={fan_x:.2f}m, Y={fan_y:.2f}m")
            if is_final:
                self.equipment_moved.emit("fan", fan_x, fan_y)
            else:
                self.render_plan()

    def _toggle_fixed_scale(self, checked: bool):
        self.use_fixed_scale = checked
        self.render_plan()

    def _on_floor_mode_changed(self):
        txt = self.combo_floor.currentText()
        if "Nivel 1" in txt:
            self.set_height(1.10)
        elif "Nivel 2" in txt:
            hb = self.get_house_bounds()
            z2 = min(hb["zmax"] - 0.5, max(3.5, hb["zmin"] + 3.8))
            self.set_height(z2)
        self.render_plan()

    def _on_preset_changed(self):
        z_val = self.combo_z_preset.currentData()
        if z_val is not None:
            self.set_height(float(z_val))

    def _on_slider_z_changed(self, val: int):
        z = val * 0.10
        self.current_z = z
        self.lbl_z.setText(f"Z: {z:.2f} m")
        self.combo_z_preset.blockSignals(True)
        # Buscar si coincide con alguno o dejar en personalizado
        matched = False
        for idx in range(self.combo_z_preset.count() - 1):
            preset_z = self.combo_z_preset.itemData(idx)
            if preset_z is not None and abs(preset_z - z) < 0.06:
                self.combo_z_preset.setCurrentIndex(idx)
                matched = True
                break
        if not matched:
            self.combo_z_preset.setCurrentIndex(self.combo_z_preset.count() - 1)
        self.combo_z_preset.blockSignals(False)
        self.height_changed.emit(z)
        self.render_plan()

    def set_height(self, z: float):
        self.current_z = max(0.0, z)
        val = int(round(self.current_z * 10))
        self.slider_z.blockSignals(True)
        self.slider_z.setValue(val)
        self.slider_z.blockSignals(False)
        self.lbl_z.setText(f"Z: {self.current_z:.2f} m")
        self.height_changed.emit(self.current_z)
        self.render_plan()

    def _on_palette_changed(self):
        txt = self.combo_pal.currentText()
        if "jet" in txt:
            self.color_palette = "jet"
        elif "coolwarm" in txt:
            self.color_palette = "coolwarm"
        elif "plasma" in txt:
            self.color_palette = "plasma"
        else:
            self.color_palette = "turbo"
        self.render_plan()

    def _toggle_isolines(self, checked: bool):
        self.show_isolines = checked
        self.render_plan()

    def _toggle_equipment(self, checked: bool):
        self.show_equipment = checked
        self.render_plan()

    def set_model(self, model: BuildingGeometry3D):
        self.building_model = model
        hb = self.get_house_bounds()
        max_h = max(10.0, hb["zmax"] + 1.0)
        self.slider_z.setRange(0, int(round(max_h * 10)))
        self.update_z_presets()
        self.render_plan()

    def set_temperatures(self, t1: float, t2: float, elev: float, azim: float, north_deg: float = 0.0):
        self.t_level_1 = t1
        self.t_level_2 = t2
        self.solar_elev = elev
        self.solar_azim = azim
        self.north_deg = north_deg
        self.render_plan()

    def set_occupancy(self, occ_l1: int, occ_l2: int, heat_w: float = 100.0):
        self.occupants_l1 = occ_l1
        self.occupants_l2 = occ_l2
        self.occupant_heat_w = heat_w
        self.render_plan()

    def set_equipment_state(
        self,
        ac_on: bool = False, ac_xyz: list = None, ac_qty: int = 1,
        fan_on: bool = False, fan_xyz: list = None, fan_qty: int = 1,
        eolic_on: bool = False, eolic_xyz: list = None, eolic_qty: int = 2,
        exhaust_on: bool = False, exhaust_xyz: list = None, exhaust_qty: int = 1,
        supply_on: bool = False, supply_xyz: list = None, supply_qty: int = 1,
        ac_units: list = None, fan_units: list = None, eolic_units: list = None,
        exhaust_units: list = None, supply_units: list = None
    ):
        self.ac_enabled = ac_on
        self.ac_units = ac_units if ac_units is not None else []
        if not self.ac_units and ac_xyz is not None:
            self.ac_units = [{"name": f"A/C #{i+1}", "x": ac_xyz[0], "y": ac_xyz[1], "z": ac_xyz[2], "enabled": True} for i in range(ac_qty)]
        if ac_xyz is not None:
            self.ac_pos = ac_xyz
        self.ac_qty = max(1, len(self.ac_units) if self.ac_units else ac_qty)

        self.fan_enabled = fan_on
        self.fan_units = fan_units if fan_units is not None else []
        if not self.fan_units and fan_xyz is not None:
            self.fan_units = [{"name": f"Vent #{i+1}", "x": fan_xyz[0], "y": fan_xyz[1], "z": fan_xyz[2], "enabled": True} for i in range(fan_qty)]
        if fan_xyz is not None:
            self.fan_pos = fan_xyz
        self.fan_qty = max(1, len(self.fan_units) if self.fan_units else fan_qty)

        self.eolic_enabled = eolic_on
        self.eolic_units = eolic_units if eolic_units is not None else []
        if not self.eolic_units and eolic_xyz is not None:
            self.eolic_units = [{"name": f"Eolico #{i+1}", "x": eolic_xyz[0], "y": eolic_xyz[1], "z": eolic_xyz[2], "enabled": True} for i in range(eolic_qty)]
        if eolic_xyz is not None:
            self.eolic_pos = eolic_xyz
        self.eolic_qty = max(0, len(self.eolic_units) if self.eolic_units else eolic_qty)

        self.exhaust_enabled = exhaust_on
        self.exhaust_units = exhaust_units if exhaust_units is not None else []
        if not self.exhaust_units and exhaust_xyz is not None:
            self.exhaust_units = [{"name": f"Extr #{i+1}", "x": exhaust_xyz[0], "y": exhaust_xyz[1], "z": exhaust_xyz[2], "enabled": True} for i in range(exhaust_qty)]
        if exhaust_xyz is not None:
            self.exhaust_pos = exhaust_xyz
        self.exhaust_qty = max(1, len(self.exhaust_units) if self.exhaust_units else exhaust_qty)

        self.supply_enabled = supply_on
        self.supply_units = supply_units if supply_units is not None else []
        if not self.supply_units and supply_xyz is not None:
            self.supply_units = [{"name": f"Iny #{i+1}", "x": supply_xyz[0], "y": supply_xyz[1], "z": supply_xyz[2], "enabled": True} for i in range(supply_qty)]
        if supply_xyz is not None:
            self.supply_pos = supply_xyz
        self.supply_qty = max(1, len(self.supply_units) if self.supply_units else supply_qty)

        self.render_plan()

    def get_house_bounds(self) -> dict:
        house_surfs = [s for s in self.building_model.surfaces if s.surface_type != "neighbor_wall"]
        if not house_surfs:
            return {"xmin": 0.0, "xmax": 8.0, "ymin": 0.0, "ymax": 5.0, "zmin": 0.0, "zmax": 5.6, "len_x": 8.0, "len_y": 5.0, "height": 5.6}
        arr = np.array([v for s in house_surfs for v in s.vertices])
        xmin, ymin, zmin = np.min(arr, axis=0)
        xmax, ymax, zmax = np.max(arr, axis=0)
        return {
            "xmin": float(xmin), "xmax": float(xmax),
            "ymin": float(ymin), "ymax": float(ymax),
            "zmin": float(max(0.0, zmin)), "zmax": float(zmax),
            "len_x": float(max(xmax - xmin, 1.0)),
            "len_y": float(max(ymax - ymin, 1.0)),
            "height": float(max(zmax - zmin, 1.0))
        }

    def render_plan(self):
        """Genera el corte en planta 2D del mapa térmico y carpintería arquitectónica (protegido contra re-entrada)."""
        if getattr(self, "_is_rendering", False):
            return
        self._is_rendering = True
        try:
            self._do_render_plan()
        except Exception as e:
            print("Aviso en render_plan:", e)
        finally:
            self._is_rendering = False

    def _do_render_plan(self):
        self.ax.clear()
        self.ax.set_facecolor("#121218")
        self.fig.patch.set_facecolor("#181820")

        hb = self.get_house_bounds()
        xmin, xmax = hb["xmin"], hb["xmax"]
        ymin, ymax = hb["ymin"], hb["ymax"]
        lx, ly = hb["len_x"], hb["len_y"]
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0

        # Malla 2D de alta resolución (64x64)
        grid_n = 64
        x_vals = np.linspace(xmin, xmax, grid_n)
        y_vals = np.linspace(ymin, ymax, grid_n)
        X, Y = np.meshgrid(x_vals, y_vals)

        # 1. Determinar nivel activo y temperatura base con estratificación vertical
        has_level_2 = any(s.level == 2 for s in self.building_model.surfaces if s.surface_type != "neighbor_wall") or (hb["height"] > 3.4)
        is_level_2 = (self.current_z > 2.8) and has_level_2
        t_base = self.t_level_2 if is_level_2 else self.t_level_1
        z_floor_ref = 2.85 if is_level_2 else 0.05
        z_offset = max(0.0, self.current_z - z_floor_ref)

        # Estratificación: si hay ventilador o extractores funcionando, se reduce la estratificación
        mixing_factor = 0.35 if (self.fan_enabled or self.exhaust_enabled) else 0.70
        stratification_dt = z_offset * 0.65 * mixing_factor
        T_field = np.full_like(X, t_base + stratification_dt)

        # 2. Carga térmica por ocupación de personas (distribuida en la planta)
        occ = self.occupants_l2 if is_level_2 else self.occupants_l1
        if occ > 0:
            q_occ_total = occ * self.occupant_heat_w
            # Delta T realista según aforo y volumen
            dt_occ = min(4.5, (q_occ_total / max(50.0, lx * ly * 12.0)) * 0.40)
            T_field += dt_occ

        # 3. Influencia de Equipos HVAC activos individuales (Solo en su nivel correspondiente)
        # A/C Split (modulado según capacidad nominal instalada)
        if self.ac_enabled and hasattr(self, "ac_units") and self.ac_units:
            for item in self.ac_units:
                if not item.get("enabled", True):
                    continue
                ac_is_l2 = (item.get("z", 2.3) > 2.5)
                if ac_is_l2 == is_level_2 or not has_level_2:
                    z_diff = abs(self.current_z - item.get("z", 2.3))
                    z_atten = np.exp(-z_diff / 2.2)
                    d_sq = (X - item.get("x", 4.0))**2 + (Y - item.get("y", 2.5))**2
                    nom_btu = item.get("nominal_btu_h", 24000.0)
                    scale = min(1.35, max(0.45, nom_btu / 24000.0))
                    T_field -= (7.0 * scale * z_atten) * np.exp(-d_sq / 4.8)

        # Ventiladores de Confort (modulado según tipo de montaje y velocidad de fabricante)
        if self.fan_enabled and hasattr(self, "fan_units") and self.fan_units:
            for item in self.fan_units:
                if not item.get("enabled", True):
                    continue
                fan_is_l2 = (item.get("z", 2.55) > 2.5)
                if fan_is_l2 == is_level_2 or not has_level_2:
                    z_diff = abs(self.current_z - item.get("z", 2.55))
                    z_atten = np.exp(-z_diff / 2.8)
                    d_sq = (X - item.get("x", 4.0))**2 + (Y - item.get("y", 2.5))**2
                    mount = item.get("mount", "techo")
                    eff = 1.0 if mount == "techo" else (0.88 if mount == "pared_alta" else 0.95)
                    v = item.get("air_speed_m_s", 1.0)
                    relief = min(4.8, 1.25 * np.log(1.0 + (v / 0.15)) * eff * 1.4)
                    T_field -= (relief * z_atten) * np.exp(-d_sq / 5.5)

        # Inyector de Aire Exterior
        if self.supply_enabled and hasattr(self, "supply_units") and self.supply_units:
            for item in self.supply_units:
                if not item.get("enabled", True):
                    continue
                sup_is_l2 = (item.get("z", 2.0) > 2.5)
                if sup_is_l2 == is_level_2 or not has_level_2:
                    z_diff = abs(self.current_z - item.get("z", 2.0))
                    z_atten = np.exp(-z_diff / 2.5)
                    d_sq = (X - item.get("x", 4.0))**2 + (Y - item.get("y", 2.5))**2
                    T_field -= (2.5 * z_atten) * np.exp(-d_sq / 5.0)

        # Extractor Mecánico
        if self.exhaust_enabled and hasattr(self, "exhaust_units") and self.exhaust_units:
            for item in self.exhaust_units:
                if not item.get("enabled", True):
                    continue
                exh_is_l2 = (item.get("z", 2.4) > 2.5)
                if exh_is_l2 == is_level_2 or not has_level_2:
                    z_diff = abs(self.current_z - item.get("z", 2.4))
                    z_atten = np.exp(-z_diff / 2.2)
                    d_sq = (X - item.get("x", 4.0))**2 + (Y - item.get("y", 2.5))**2
                    T_field -= (2.0 * z_atten) * np.exp(-d_sq / 4.5)

        # Extractor Eólico de Cubierta: SOLO actúa en Nivel 2 o bajo techo
        if self.eolic_enabled and hasattr(self, "eolic_units") and self.eolic_units and (is_level_2 or not has_level_2 or self.current_z > hb["zmax"] - 1.5):
            for item in self.eolic_units:
                if not item.get("enabled", True):
                    continue
                z_diff = abs(self.current_z - item.get("z", 5.6))
                z_atten = np.exp(-z_diff / 2.5)
                d_sq = (X - item.get("x", 4.0))**2 + (Y - item.get("y", 2.5))**2
                T_field -= (2.8 * z_atten) * np.exp(-d_sq / 6.0)

        # 4. Ganancia Solar incidente orientada según la posición solar astronómica real
        if self.solar_elev > 4.0:
            phi_rel = self.solar_azim - self.north_deg
            rad_phi = np.radians(phi_rel)
            sin_p = np.sin(rad_phi)
            cos_p = np.cos(rad_phi)
            sun_proj = ((X - cx) / (lx / 2.0)) * sin_p + ((Y - cy) / (ly / 2.0)) * cos_p
            sun_gain = np.clip(sun_proj, 0.0, 1.0) ** 1.8
            solar_power = np.sin(np.radians(self.solar_elev)) * 4.2
            T_field += solar_power * sun_gain

        # 5. Escala y Representación del Campo de Temperatura
        if self.use_fixed_scale:
            # Escala térmica absoluta estándar de ingeniería bioclimática (18°C a 40°C)
            norm = mcolors.Normalize(vmin=18.0, vmax=40.0)
        else:
            t_min = float(np.min(T_field))
            t_max = float(np.max(T_field))
            if t_max - t_min < 3.0:
                t_min -= 1.5
                t_max += 1.5
            norm = mcolors.Normalize(vmin=t_min, vmax=t_max)

        cmap = mpl.colormaps[self.color_palette]

        # Mapa de Calor Continuo 2D
        cf = self.ax.contourf(X, Y, T_field, levels=32, cmap=cmap, norm=norm, alpha=0.92)

        # Curvas de Nivel (Isotermas) con etiquetas de temperatura
        if self.show_isolines:
            try:
                cs = self.ax.contour(X, Y, T_field, levels=8, colors="#ffffff", alpha=0.45, linewidths=0.9)
                if hasattr(cs, "levels") and len(cs.levels) > 0:
                    self.ax.clabel(cs, inline=True, fontsize=8, fmt="%.1f°C", colors="#ffffff")
            except Exception:
                pass

        # 6. Dibujar Carpintería Arquitectónica en Planta a la altura Z (Muros, Ventanas, Puertas)
        target_level = 2 if is_level_2 else 1
        level_surfs = [s for s in self.building_model.surfaces if s.level == target_level and s.surface_type != "neighbor_wall"]

        for surf in level_surfs:
            pts = [(v[0], v[1]) for v in surf.vertices]
            if len(pts) < 2:
                continue

            z_verts = [v[2] for v in surf.vertices]
            z_bot = min(z_verts)
            z_top = max(z_verts)
            is_cut = (z_bot - 0.2 <= self.current_z <= z_top + 0.2)
            alpha_line = 1.0 if is_cut else 0.35

            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]

            if surf.surface_type == "window":
                self.ax.plot(xs, ys, color="#00e5ff", linewidth=3.5, alpha=alpha_line, solid_capstyle="round")
                self.ax.plot(xs, ys, color="#ffffff", linewidth=1.2, alpha=alpha_line)
            elif surf.surface_type == "door":
                self.ax.plot(xs, ys, color="#bcaaa4", linewidth=3.0, alpha=alpha_line)
            elif surf.surface_type == "wall":
                self.ax.plot(xs, ys, color="#eceff1" if is_cut else "#546e7a", linewidth=2.5 if is_cut else 1.2, alpha=alpha_line)

        # Contorno perimetral del edificio
        self.ax.plot([xmin, xmax, xmax, xmin, xmin], [ymin, ymin, ymax, ymax, ymin], color="#ffffff", linewidth=2.0)

        # 7. Marcadores de Equipos HVAC en Planta
        if self.show_equipment:
            if self.ac_enabled and hasattr(self, "ac_units") and self.ac_units:
                for item in self.ac_units:
                    if not item.get("enabled", True):
                        continue
                    ac_is_l2 = (item.get("z", 2.3) > 2.5)
                    if ac_is_l2 == is_level_2 or not has_level_2:
                        ax_p, ay_p = item.get("x", 4.0), item.get("y", 2.5)
                        name = item.get("name", "A/C")
                        self.ax.scatter([ax_p], [ay_p], color="#00e5ff", s=150, marker="s", edgecolors="#ffffff", linewidths=1.5, zorder=5)
                        cap_k = f"{int(round(item.get('nominal_btu_h', 24000.0)/1000.0))}k" if not item.get("is_auto", False) else "Auto"
                        self.ax.text(ax_p, ay_p + (ly * 0.04), f"[AC] {name} ({cap_k})", color="#00e5ff", fontsize=8, fontweight="bold",
                                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#00363a", alpha=0.90, edgecolor="#00e5ff"))

            if self.fan_enabled and hasattr(self, "fan_units") and self.fan_units:
                for item in self.fan_units:
                    if not item.get("enabled", True):
                        continue
                    fan_is_l2 = (item.get("z", 2.55) > 2.5)
                    if fan_is_l2 == is_level_2 or not has_level_2:
                        fx_p, fy_p = item.get("x", 4.0), item.get("y", 2.5)
                        name = item.get("name", "Vent")
                        self.ax.scatter([fx_p], [fy_p], color="#4caf50", s=140, marker="o", edgecolors="#ffffff", linewidths=1.5, zorder=5)
                        mount = item.get("mount", "techo")
                        m_tag = "Techo" if mount == "techo" else ("Mural" if mount == "pared_alta" else "Pedestal")
                        self.ax.text(fx_p, fy_p + (ly * 0.04), f"[Vent] {name} ({m_tag})", color="#81c784", fontsize=8, fontweight="bold",
                                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#1b5e20", alpha=0.90, edgecolor="#81c784"))

            if self.supply_enabled and hasattr(self, "supply_units") and self.supply_units:
                for item in self.supply_units:
                    if not item.get("enabled", True):
                        continue
                    sup_is_l2 = (item.get("z", 2.0) > 2.5)
                    if sup_is_l2 == is_level_2 or not has_level_2:
                        sx_p, sy_p = item.get("x", 4.0), item.get("y", 2.5)
                        name = item.get("name", "Iny")
                        self.ax.scatter([sx_p], [sy_p], color="#00bcd4", s=130, marker="D", edgecolors="#ffffff", linewidths=1.5, zorder=5)
                        self.ax.text(sx_p, sy_p - (ly * 0.05), f"[Iny] {name}", color="#80deea", fontsize=8,
                                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#004d40", alpha=0.90, edgecolor="#00bcd4"))

            if self.exhaust_enabled and hasattr(self, "exhaust_units") and self.exhaust_units:
                for item in self.exhaust_units:
                    if not item.get("enabled", True):
                        continue
                    exh_is_l2 = (item.get("z", 2.4) > 2.5)
                    if exh_is_l2 == is_level_2 or not has_level_2:
                        ex_p, ey_p = item.get("x", 4.0), item.get("y", 2.5)
                        name = item.get("name", "Ext")
                        self.ax.scatter([ex_p], [ey_p], color="#e91e63", s=140, marker="h", edgecolors="#ffffff", linewidths=1.5, zorder=5)
                        self.ax.text(ex_p, ey_p + (ly * 0.05), f"[Ext] {name}", color="#f48fb1", fontsize=8,
                                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#4a148c", alpha=0.90, edgecolor="#e91e63"))

        # 8. Pines de Temperatura Mínima, Media y Máxima
        val_min = float(np.min(T_field))
        val_max = float(np.max(T_field))
        val_mean = float(np.mean(T_field))

        min_pos = np.unravel_index(np.argmin(T_field), T_field.shape)
        max_pos = np.unravel_index(np.argmax(T_field), T_field.shape)
        min_x, min_y = X[min_pos], Y[min_pos]
        max_x, max_y = X[max_pos], Y[max_pos]

        # Etiqueta Mínima
        self.ax.scatter([min_x], [min_y], color="#00e5ff", s=60, edgecolors="#ffffff", linewidths=1.2, zorder=6)
        lbl_min = f"Mín: {val_min:.1f} °C" if self.ac_enabled else f"Mín: {val_min:.1f} °C"
        self.ax.text(min_x, min_y - (ly * 0.05), lbl_min, color="#ffffff", fontsize=8.5, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.25", facecolor="#004d40", alpha=0.92, edgecolor="#00e5ff"), zorder=7)

        # Etiqueta Media
        self.ax.scatter([cx], [cy], color="#ffeb3b", s=50, edgecolors="#ffffff", linewidths=1.0, zorder=6)
        self.ax.text(cx, cy, f"Prom: {val_mean:.1f} °C", color="#ffffff", fontsize=8.5,
                     bbox=dict(boxstyle="round,pad=0.25", facecolor="#263238", alpha=0.92, edgecolor="#78909c"), zorder=7)

        # Etiqueta Máxima
        if val_max > val_min + 0.8:
            self.ax.scatter([max_x], [max_y], color="#ff1744", s=60, edgecolors="#ffffff", linewidths=1.2, zorder=6)
            lbl_hot = f"Sol: {val_max:.1f} °C" if self.solar_elev > 4 else f"Máx: {val_max:.1f} °C"
            self.ax.text(max_x, max_y + (ly * 0.05), lbl_hot, color="#ffffff", fontsize=8.5, fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.25", facecolor="#b71c1c", alpha=0.92, edgecolor="#ff5252"), zorder=7)

        # 9. Flecha de Norte 2D (Rosa de los vientos)
        arr_x = xmin + lx * 0.08
        arr_y = ymax - ly * 0.08
        arr_len = min(lx, ly) * 0.14
        north_rad = np.radians(self.north_deg)
        nx = arr_x + arr_len * np.sin(north_rad)
        ny = arr_y + arr_len * np.cos(north_rad)
        self.ax.annotate(
            "", xy=(nx, ny), xytext=(arr_x, arr_y),
            arrowprops=dict(arrowstyle="->", color="#ff1744", lw=2.2)
        )
        self.ax.text(nx, ny + (ly * 0.03), "N", color="#ff1744", fontsize=9, fontweight="bold", ha="center")

        # 10. Configuración de Ejes y Dimensiones
        pad_x = lx * 0.12
        pad_y = ly * 0.12
        self.ax.set_xlim(xmin - pad_x, xmax + pad_x)
        self.ax.set_ylim(ymin - pad_y, ymax + pad_y)
        self.ax.set_aspect("equal")
        self.ax.set_xlabel("Longitud X (metros)", color="#aaaaaa", fontsize=9)
        self.ax.set_ylabel("Profundidad Y (metros)", color="#aaaaaa", fontsize=9)
        self.ax.tick_params(colors="#aaaaaa", labelsize=8)
        self.ax.grid(True, linestyle=":", color="#252538", alpha=0.6)
        self.ax.set_title(f"Mapa Térmico en Planta 2D (Corte Z = {self.current_z:.2f} m) - EM.110 Perú", color="#ffffff", fontsize=10, fontweight="bold", pad=8)

        # 11. Barra de Color Térmica Estable en cax
        self.cax.clear()
        sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        self.cbar = self.fig.colorbar(sm, cax=self.cax)
        self.cbar.set_label("Temperatura (°C) - EM.110", color="#ffffff", fontsize=8, fontweight="bold")
        if self.use_fixed_scale:
            self.cbar.set_ticks([18, 21, 24, 27, 30, 33, 36, 40])
            self.cbar.set_ticklabels(["18°", "21°", "24° (Conf)", "27°", "30°", "33°", "36°", "40°C"])
        self.cbar.ax.tick_params(colors="#ffffff", labelsize=7)

        self.canvas.draw_idle()
