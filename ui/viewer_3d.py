"""
Visor 3D Interactivo de Alta Precisión con Plataforma de Terreno Sólida (Z=0),
Mapa de Calor Continuo Orientado Físicamente a la Radiación Solar Real,
Representación de Ventanas y Posicionamiento de Climatización y Ventilación Forzada.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import matplotlib as mpl
import matplotlib.colors as mcolors

from geometry.building_model import BuildingGeometry3D


class Viewer3DWidget(QWidget):
    """Widget 3D con órbita interactiva, mapas de calor en pisos y suelo sólido a Z=0."""
    hour_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.building_model: BuildingGeometry3D = BuildingGeometry3D.create_default_building()
        self.t_level_1: float = 26.0
        self.t_level_2: float = 31.0
        self.solar_elev: float = 45.0
        self.solar_azim: float = 45.0
        self.current_hour: int = 14
        self.selected_surface_name: str = ""
        self.north_deg: float = 0.0

        # Estado y posiciones de equipos (X, Y, Z) y cantidades
        self.ac_enabled: bool = False
        self.ac_pos: list = [4.0, 0.15, 2.3]  # Montado en pared
        self.ac_qty: int = 1

        self.fan_enabled: bool = True
        self.fan_pos: list = [4.0, 2.5, 2.6]  # Centro
        self.fan_qty: int = 1

        self.eolic_enabled: bool = True
        self.eolic_pos: list = [4.0, 2.5, 5.6]  # Cumbrera
        self.eolic_qty: int = 2

        self.exhaust_enabled: bool = False
        self.exhaust_pos: list = [4.0, 4.85, 2.3]  # Extractor mecánico en pared
        self.exhaust_qty: int = 1

        self.supply_enabled: bool = False
        self.supply_pos: list = [4.0, 0.15, 2.0]  # Inyector de aire fresco
        self.supply_qty: int = 1

        # Ocupación
        self.occupants_l1: int = 2
        self.occupants_l2: int = 2
        self.occupant_heat_w: float = 100.0

        # Modos de visualización
        self.show_heatmaps: bool = True
        self.transparent_roof: bool = True
        self.focus_mode: str = "house"  # 'house' o 'site'
        self.proj_type: str = "ortho"   # 'ortho' (isométrica 1:1:1) o 'persp' (perspectiva)
        self.floor_filter: str = "all"  # 'all', '1', '2'
        self.zoom_factor: float = 1.0
        self.color_palette: str = "turbo"  # 'turbo', 'jet', 'coolwarm', 'plasma'
        self.use_fixed_scale: bool = True  # Escala térmica absoluta fija (18°C - 40°C)
        self.show_neighbors: bool = False
        self.cbar = None
        self._is_rendering: bool = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Canvas Matplotlib 3D con Eje Fijo y Eje Dedicado para Barra de Color
        self.fig = Figure(facecolor="#181820")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_axes([0.02, 0.04, 0.88, 0.92], projection="3d")
        self.ax.set_facecolor("#181820")
        self.cax = self.fig.add_axes([0.91, 0.22, 0.022, 0.56])
        self.cax.set_facecolor("#181820")
        layout.addWidget(self.canvas)

        # Conectar eventos de ratón para Zoom intuitivo con la rueda
        self.canvas.mpl_connect("scroll_event", self._on_mouse_scroll)

        # 2. Barra de Herramientas de Navegación 3D y Control de Cámara
        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(6, 4, 6, 4)

        # Zoom
        btn_zoom_in = QPushButton("🔍+")
        btn_zoom_in.setToolTip("Acercar (Zoom In)")
        btn_zoom_in.setFixedWidth(32)
        btn_zoom_in.clicked.connect(lambda: self._zoom(0.85))
        tools_layout.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("🔍-")
        btn_zoom_out.setToolTip("Alejar (Zoom Out)")
        btn_zoom_out.setFixedWidth(32)
        btn_zoom_out.clicked.connect(lambda: self._zoom(1.18))
        tools_layout.addWidget(btn_zoom_out)

        # Enfoque Casa vs Terreno
        self.btn_focus = QPushButton("🏠 Casa")
        self.btn_focus.setToolTip("Alternar entre enfocar solo la casa o ver todo el terreno con vecinos")
        self.btn_focus.clicked.connect(self._toggle_focus_mode)
        tools_layout.addWidget(self.btn_focus)

        # Proyección Isométrica vs Perspectiva
        self.btn_proj = QPushButton("📐 Isométrica")
        self.btn_proj.setToolTip("Alternar entre vista isométrica ortográfica (1:1:1 sin deformación) y perspectiva")
        self.btn_proj.clicked.connect(self._toggle_projection)
        tools_layout.addWidget(self.btn_proj)

        # Vistas Predefinidas
        btn_iso_view = QPushButton("🔄 3D")
        btn_iso_view.setToolTip("Restaurar vista 3D estándar a escala 1:1:1")
        btn_iso_view.clicked.connect(self._reset_view)
        tools_layout.addWidget(btn_iso_view)

        btn_top_view = QPushButton("🔝 Planta")
        btn_top_view.setToolTip("Vista superior cenital")
        btn_top_view.clicked.connect(lambda: self.set_view_angles(elev=90, azim=-90))
        tools_layout.addWidget(btn_top_view)

        btn_front_view = QPushButton("🏢 Frente")
        btn_front_view.setToolTip("Vista frontal")
        btn_front_view.clicked.connect(lambda: self.set_view_angles(elev=0, azim=-90))
        tools_layout.addWidget(btn_front_view)

        # Filtro de Pisos
        self.combo_floors = QComboBox()
        self.combo_floors.addItems(["Todos los Pisos", "Solo Nivel 1", "Solo Nivel 2"])
        self.combo_floors.currentIndexChanged.connect(self._on_floor_filter_changed)
        self.combo_floors.setToolTip("Aislar la vista de calor en un piso específico")
        self.combo_floors.setFixedWidth(115)
        tools_layout.addWidget(self.combo_floors)

        # Paleta de Color Térmica
        self.combo_pal = QComboBox()
        self.combo_pal.addItems(["turbo (Google)", "jet (Clásico)", "coolwarm (Frío-Calor)", "plasma (Contraste)"])
        self.combo_pal.currentIndexChanged.connect(self._on_palette_changed)
        self.combo_pal.setToolTip("Escala de color para los mapas de temperatura")
        self.combo_pal.setFixedWidth(125)
        tools_layout.addWidget(self.combo_pal)

        # Techo Translúcido
        self.chk_roof = QCheckBox("Techo Alámbrico")
        self.chk_roof.setChecked(True)
        self.chk_roof.setToolTip("Hacer el techo translúcido/alámbrico para observar los mapas térmicos de los pisos")
        self.chk_roof.toggled.connect(self._toggle_transparent_roof)
        tools_layout.addWidget(self.chk_roof)

        # Escala fija vs relativa
        self.chk_fixed_scale = QCheckBox("Escala Absoluta (18-40°C)")
        self.chk_fixed_scale.setChecked(True)
        self.chk_fixed_scale.setToolTip("Escala térmica estándar fija: Verde = Confort 21-26°C, Amarillo = 27-29°C, Naranja = 30-33°C, Rojo = >34°C. Evita que 30°C se pinte de azul.")
        self.chk_fixed_scale.toggled.connect(self._toggle_fixed_scale)
        tools_layout.addWidget(self.chk_fixed_scale)
        self.chk_neighbors = QCheckBox("Vecinos")
        self.chk_neighbors.setChecked(False)
        self.chk_neighbors.setToolTip("Mostrar u ocultar los obstáculos y terreno de edificaciones vecinas importadas.")
        self.chk_neighbors.toggled.connect(self._toggle_neighbors)
        tools_layout.addWidget(self.chk_neighbors)

        tools_layout.addSpacing(6)

        # Control Horario
        self.lbl_hour = QLabel(f"Hora: {self.current_hour:02d}:00")
        self.lbl_hour.setStyleSheet("font-weight: bold; font-size: 11px; color: #ffffff;")
        tools_layout.addWidget(self.lbl_hour)

        self.slider_hour = QSlider(Qt.Orientation.Horizontal)
        self.slider_hour.setRange(6, 18)
        self.slider_hour.setValue(self.current_hour)
        self.slider_hour.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_hour.setTickInterval(1)
        self.slider_hour.valueChanged.connect(self._on_slider_changed)
        tools_layout.addWidget(self.slider_hour)

        layout.addLayout(tools_layout)

        # Dibujo inicial
        self.render_scene()

    def _toggle_focus_mode(self):
        if self.focus_mode == "house":
            self.focus_mode = "site"
            self.btn_focus.setText("🌐 Terreno")
            self.btn_focus.setToolTip("Actualmente viendo todo el sitio. Clic para enfocar solo la casa.")
        else:
            self.focus_mode = "house"
            self.btn_focus.setText("🏠 Casa")
            self.btn_focus.setToolTip("Actualmente enfocando la casa. Clic para ver el terreno completo.")
        self.render_scene()

    def _toggle_projection(self):
        if self.proj_type == "ortho":
            self.proj_type = "persp"
            self.btn_proj.setText("👁️ Perspectiva")
        else:
            self.proj_type = "ortho"
            self.btn_proj.setText("📐 Isométrica")
        self.render_scene()

    def _toggle_transparent_roof(self, checked: bool):
        self.transparent_roof = checked
        self.render_scene()

    def _toggle_fixed_scale(self, checked: bool):
        self.use_fixed_scale = checked
        self.render_scene()

    def _toggle_neighbors(self, checked: bool):
        self.show_neighbors = checked
        self.render_scene()

    def _on_floor_filter_changed(self):
        txt = self.combo_floors.currentText()
        if "Nivel 1" in txt:
            self.floor_filter = "1"
        elif "Nivel 2" in txt:
            self.floor_filter = "2"
        else:
            self.floor_filter = "all"
        self.render_scene()

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
        self.render_scene()

    def _on_mouse_scroll(self, event):
        if event.button == "up":
            self._zoom(0.85)
        elif event.button == "down":
            self._zoom(1.18)

    def _zoom(self, scale_mult: float):
        self.zoom_factor *= scale_mult
        self.zoom_factor = max(0.25, min(4.0, self.zoom_factor))
        self.render_scene()

    def _reset_view(self):
        """Restaura la vista 3D a escala isométrica 1:1:1 perfecta."""
        self.zoom_factor = 1.0
        self.focus_mode = "house"
        self.btn_focus.setText("🏠 Casa")
        self.proj_type = "ortho"
        self.btn_proj.setText("📐 Isométrica")
        self.ax.dist = 10.0
        self.ax.view_init(elev=25, azim=-60)
        self.render_scene()

    def set_view_angles(self, elev: float, azim: float):
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw_idle()

    def _on_slider_changed(self, val: int):
        self.current_hour = val
        self.lbl_hour.setText(f"Hora: {self.current_hour:02d}:00")
        self.hour_changed.emit(val)

    def set_temperatures(self, t1: float, t2: float, elev: float, azim: float, north_deg: float = 0.0):
        self.t_level_1 = t1
        self.t_level_2 = t2
        self.solar_elev = elev
        self.solar_azim = azim
        self.north_deg = north_deg
        self.render_scene()

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
        self.ac_qty = max(1, len(self.ac_units) if self.ac_units else ac_qty)

        self.fan_enabled = fan_on
        self.fan_units = fan_units if fan_units is not None else []
        if not self.fan_units and fan_xyz is not None:
            self.fan_units = [{"name": f"Vent #{i+1}", "x": fan_xyz[0], "y": fan_xyz[1], "z": fan_xyz[2], "enabled": True} for i in range(fan_qty)]
        self.fan_qty = max(1, len(self.fan_units) if self.fan_units else fan_qty)

        self.eolic_enabled = eolic_on
        self.eolic_units = eolic_units if eolic_units is not None else []
        if not self.eolic_units and eolic_xyz is not None:
            self.eolic_units = [{"name": f"Eolico #{i+1}", "x": eolic_xyz[0], "y": eolic_xyz[1], "z": eolic_xyz[2], "enabled": True} for i in range(eolic_qty)]
        self.eolic_qty = max(0, len(self.eolic_units) if self.eolic_units else eolic_qty)

        self.exhaust_enabled = exhaust_on
        self.exhaust_units = exhaust_units if exhaust_units is not None else []
        if not self.exhaust_units and exhaust_xyz is not None:
            self.exhaust_units = [{"name": f"Extr #{i+1}", "x": exhaust_xyz[0], "y": exhaust_xyz[1], "z": exhaust_xyz[2], "enabled": True} for i in range(exhaust_qty)]
        self.exhaust_qty = max(1, len(self.exhaust_units) if self.exhaust_units else exhaust_qty)

        self.supply_enabled = supply_on
        self.supply_units = supply_units if supply_units is not None else []
        if not self.supply_units and supply_xyz is not None:
            self.supply_units = [{"name": f"Iny #{i+1}", "x": supply_xyz[0], "y": supply_xyz[1], "z": supply_xyz[2], "enabled": True} for i in range(supply_qty)]
        self.supply_qty = max(1, len(self.supply_units) if self.supply_units else supply_qty)

        self.render_scene()

    def set_occupancy(self, occ_l1: int, occ_l2: int, heat_w: float = 100.0):
        self.occupants_l1 = occ_l1
        self.occupants_l2 = occ_l2
        self.occupant_heat_w = heat_w
        self.render_scene()

    def set_model(self, model: BuildingGeometry3D):
        self.building_model = model
        self.render_scene()

    def select_surface(self, name: str):
        self.selected_surface_name = name
        self.render_scene()

    def get_house_bounds(self) -> dict:
        """Calcula las dimensiones exactas de la casa principal para posicionamiento de equipos y planos de piso."""
        house_surfs = [
            s for s in self.building_model.surfaces 
            if s.surface_type != "neighbor_wall" and s.level in [1, 2]
        ]
        if not house_surfs:
            return {
                "xmin": 0.0, "xmax": 8.0, "ymin": 0.0, "ymax": 5.0,
                "zmin": 0.0, "zmax": 5.6, "zmid": 2.8,
                "len_x": 8.0, "len_y": 5.0, "height": 5.6
            }

        all_v = [v for s in house_surfs for v in s.vertices]
        arr = np.array(all_v)
        xmin, ymin, zmin = np.min(arr, axis=0)
        xmax, ymax, zmax = np.max(arr, axis=0)
        return {
            "xmin": float(xmin), "xmax": float(xmax),
            "ymin": float(ymin), "ymax": float(ymax),
            "zmin": float(max(0.0, zmin)), "zmax": float(zmax),
            "zmid": float((zmin + zmax) / 2.0),
            "len_x": float(max(xmax - xmin, 1.0)),
            "len_y": float(max(ymax - ymin, 1.0)),
            "height": float(max(zmax - zmin, 1.0))
        }

    def _render_floor_heatmap(self, z_level: float, t_base: float, floor_name: str, x_span: tuple, y_span: tuple, global_norm: mcolors.Normalize):
        """
        Dibuja un mapa de calor continuo acotado estrictamente a la huella de la casa,
        con gradientes físicos basados en la orientación solar real y posición de equipos HVAC.
        """
        x_min, x_max = x_span
        y_min, y_max = y_span
        if x_max - x_min < 0.5 or y_max - y_min < 0.5:
            return

        grid_n = 32
        x_vals = np.linspace(x_min, x_max, grid_n)
        y_vals = np.linspace(y_min, y_max, grid_n)
        X, Y = np.meshgrid(x_vals, y_vals)
        Z = np.full_like(X, z_level)

        # Campo térmico base del nivel
        T_field = np.full_like(X, t_base)

        # Determinar nivel evaluado
        is_floor_2 = (z_level > 1.8)
        has_2_floors = any(s.level == 2 for s in self.building_model.surfaces if s.surface_type != "neighbor_wall")

        # 1. Influencia del Split de A/C (Cono de enfriamiento escalado a su capacidad instalada)
        if self.ac_enabled and hasattr(self, "ac_units") and self.ac_units:
            for item in self.ac_units:
                if not item.get("enabled", True):
                    continue
                ac_is_l2 = (item.get("z", 2.3) > 2.5)
                if ac_is_l2 == is_floor_2 or not has_2_floors:
                    ux = item.get("x", 4.0)
                    uy = item.get("y", 2.5)
                    dist_sq = (X - ux)**2 + (Y - uy)**2
                    nom_btu = item.get("nominal_btu_h", 24000.0)
                    scale = min(1.35, max(0.45, nom_btu / 24000.0))
                    T_field -= (7.0 * scale) * np.exp(-dist_sq / 4.8)

        # 2. Influencia del Ventilador de Confort (alivio según tipo de montaje y velocidad de fabricante)
        if self.fan_enabled and hasattr(self, "fan_units") and self.fan_units:
            for item in self.fan_units:
                if not item.get("enabled", True):
                    continue
                fan_is_l2 = (item.get("z", 2.55) > 2.5)
                if fan_is_l2 == is_floor_2 or not has_2_floors:
                    ux = item.get("x", 4.0)
                    uy = item.get("y", 2.5)
                    dist_sq = (X - ux)**2 + (Y - uy)**2
                    mount = item.get("mount", "techo")
                    eff = 1.0 if mount == "techo" else (0.88 if mount == "pared_alta" else 0.95)
                    v = item.get("air_speed_m_s", 1.0)
                    dt_app = min(4.8, 1.25 * np.log(1.0 + (v / 0.15)) * eff * 1.4)
                    T_field -= dt_app * np.exp(-dist_sq / 5.5)

        # 3. Influencia del Inyector de Aire Exterior (incorporación de aire fresco)
        if self.supply_enabled and hasattr(self, "supply_units") and self.supply_units:
            for item in self.supply_units:
                if not item.get("enabled", True):
                    continue
                sup_is_l2 = (item.get("z", 2.0) > 2.5)
                if sup_is_l2 == is_floor_2 or not has_2_floors:
                    ux = item.get("x", 4.0)
                    uy = item.get("y", 2.5)
                    dist_sq = (X - ux)**2 + (Y - uy)**2
                    T_field -= 2.5 * np.exp(-dist_sq / 5.0)

        # 4. Influencia del Extractor Mecánico (desalojo de aire viciado caliente)
        if self.exhaust_enabled and hasattr(self, "exhaust_units") and self.exhaust_units:
            for item in self.exhaust_units:
                if not item.get("enabled", True):
                    continue
                exh_is_l2 = (item.get("z", 2.4) > 2.5)
                if exh_is_l2 == is_floor_2 or not has_2_floors:
                    ux = item.get("x", 4.0)
                    uy = item.get("y", 2.5)
                    dist_sq = (X - ux)**2 + (Y - uy)**2
                    T_field -= 1.8 * np.exp(-dist_sq / 4.5)

        # 5. Ganancia Solar FÍSICA según posición real astronómica del sol
        # Solo se calienta la fachada orientada HACIA el sol
        center_x = (x_min + x_max) / 2.0
        center_y = (y_min + y_max) / 2.0
        half_x = max((x_max - x_min) / 2.0, 1.0)
        half_y = max((y_max - y_min) / 2.0, 1.0)

        if self.solar_elev > 4.0:
            phi_rel = self.solar_azim - self.north_deg
            rad_phi = np.radians(phi_rel)
            sin_phi = np.sin(rad_phi)
            cos_phi = np.cos(rad_phi)

            # Proyección hacia el sol: positiva únicamente en la fachada que mira al sol
            sun_proj = ((X - center_x) / half_x) * sin_phi + ((Y - center_y) / half_y) * cos_phi
            sun_exposure = np.clip(sun_proj, 0.0, 1.0) ** 1.8
            solar_intensity = np.sin(np.radians(self.solar_elev)) * 4.2
            T_field += solar_intensity * sun_exposure

        # Mapeo de colores adaptativo con paleta seleccionada
        cmap = mpl.colormaps[self.color_palette]
        colors = cmap(global_norm(T_field))
        colors[..., 3] = 0.92  # Opaco para nitidez sobre el suelo

        # Renderizar plano térmico continuo
        self.ax.plot_surface(X, Y, Z, facecolors=colors, shade=False, alpha=0.92, rstride=1, cstride=1)

        # Contorno perimetral del piso
        border_x = [x_min, x_max, x_max, x_min, x_min]
        border_y = [y_min, y_min, y_max, y_max, y_min]
        border_z = [z_level] * 5
        self.ax.plot(border_x, border_y, border_z, color="#ffffff", linewidth=1.2, alpha=0.85)

        # 6. Pines Flotantes con Etiquetas de Temperatura Estilo Bioclimático Profesional (Ref. Greenhouse)
        # Punto más frío
        min_idx = np.unravel_index(np.argmin(T_field), T_field.shape)
        min_x, min_y, min_t = X[min_idx], Y[min_idx], T_field[min_idx]
        self.ax.plot([min_x, min_x], [min_y, min_y], [z_level, z_level + 0.35], color="#00e5ff", linewidth=1.2, alpha=0.9)
        self.ax.scatter([min_x], [min_y], [z_level + 0.02], color="#00e5ff", s=35, edgecolors="#ffffff", linewidths=1.2)
        lbl_cold = f"A/C: {min_t:.1f} °C" if self.ac_enabled else (f"Inyector: {min_t:.1f} °C" if self.supply_enabled else f"Min: {min_t:.1f} °C")
        self.ax.text(min_x, min_y, z_level + 0.38, lbl_cold, color="#ffffff", fontsize=8.5, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.28", facecolor="#004d40", alpha=0.92, edgecolor="#00e5ff"))

        # Punto medio / confort
        mid_x, mid_y = center_x, center_y
        mid_t = T_field[grid_n // 2, grid_n // 2]
        self.ax.plot([mid_x, mid_x], [mid_y, mid_y], [z_level, z_level + 0.30], color="#90a4ae", linewidth=1.0, alpha=0.8)
        self.ax.scatter([mid_x], [mid_y], [z_level + 0.02], color="#ffeb3b", s=28, edgecolors="#ffffff", linewidths=1.0)
        self.ax.text(mid_x, mid_y, z_level + 0.32, f"{floor_name}: {mid_t:.1f} °C", color="#ffffff", fontsize=8.5,
                     bbox=dict(boxstyle="round,pad=0.28", facecolor="#263238", alpha=0.92, edgecolor="#78909c"))

        # Punto más caliente (situado en la fachada expuesta al sol)
        max_idx = np.unravel_index(np.argmax(T_field), T_field.shape)
        max_x, max_y, max_t = X[max_idx], Y[max_idx], T_field[max_idx]
        if max_t > min_t + 1.0:
            self.ax.plot([max_x, max_x], [max_y, max_y], [z_level, z_level + 0.35], color="#ff5252", linewidth=1.2, alpha=0.9)
            self.ax.scatter([max_x], [max_y], [z_level + 0.02], color="#ff1744", s=35, edgecolors="#ffffff", linewidths=1.2)
            lbl_hot = f"Sol: {max_t:.1f} °C" if self.solar_elev > 4 else f"Max: {max_t:.1f} °C"
            self.ax.text(max_x, max_y, z_level + 0.38, lbl_hot, color="#ffffff", fontsize=8.5, fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.28", facecolor="#b71c1c", alpha=0.92, edgecolor="#ff5252"))

    def render_scene(self):
        if getattr(self, "_is_rendering", False):
            return
        self._is_rendering = True
        try:
            self._do_render_scene()
        except Exception as e:
            print("Aviso en render_scene:", e)
        finally:
            self._is_rendering = False

    def _do_render_scene(self):
        elev, azim = self.ax.elev, self.ax.azim
        self.ax.clear()
        self.ax.set_facecolor("#181820")
        self.fig.patch.set_facecolor("#181820")

        # Configurar tipo de proyección (Ortográfica Isométrica vs Perspectiva)
        self.ax.set_proj_type(self.proj_type)

        # Ocultar completamente la caja de coordenadas 3D para una visualización arquitectónica limpia (Ref. Greenhouse)
        self.ax.set_axis_off()

        # 1. Separar estrictamente superficies de la Casa vs Vecinos
        house_surfs = []
        neighbor_surfs = list(self.building_model.neighbor_obstacles)

        for surf in self.building_model.surfaces:
            if surf.surface_type == "neighbor_wall" or surf.level == 0:
                neighbor_surfs.append(surf)
            else:
                house_surfs.append(surf)

        # Dimensiones de la casa
        hb = self.get_house_bounds()
        hx_min, hx_max = hb["xmin"], hb["xmax"]
        hy_min, hy_max = hb["ymin"], hb["ymax"]
        hz_min, hz_max = hb["zmin"], hb["zmax"]

        center_x = (hx_min + hx_max) / 2.0
        center_y = (hy_min + hy_max) / 2.0
        max_span = max(hb["len_x"], hb["len_y"], hb["height"], 6.0)

        # 2. RETÍCULA ARQUITECTÓNICA DE SUELO A Z = 0.0
        # Malla de referencia sobre el terreno sin polígonos opacos que ocluyan el modelo
        g_span = max_span * 1.40
        gx0, gx1 = center_x - g_span, center_x + g_span
        gy0, gy1 = center_y - g_span, center_y + g_span

        # Contorno perimetral de la plataforma de terreno
        ground_border_x = [gx0, gx1, gx1, gx0, gx0]
        ground_border_y = [gy0, gy0, gy1, gy1, gy0]
        ground_border_z = [0.0] * 5
        self.ax.plot(ground_border_x, ground_border_y, ground_border_z, color="#373752", linewidth=1.6, alpha=0.85)

        # Retícula arquitectónica de referencia sobre el terreno (Z = 0.0)
        step = 5.0 if g_span > 15 else 2.5
        grid_xs = np.arange(np.floor(gx0 / step) * step, gx1 + step / 2, step)
        grid_ys = np.arange(np.floor(gy0 / step) * step, gy1 + step / 2, step)
        for gx in grid_xs:
            if gx0 <= gx <= gx1:
                self.ax.plot([gx, gx], [gy0, gy1], [0.0, 0.0], color="#232336", linewidth=0.8, alpha=0.6)
        for gy in grid_ys:
            if gy0 <= gy <= gy1:
                self.ax.plot([gx0, gx1], [gy, gy], [0.0, 0.0], color="#232336", linewidth=0.8, alpha=0.6)

        # Escala térmica absoluta fija estándar (18°C a 40°C) o adaptativa
        if self.use_fixed_scale:
            global_norm = mcolors.Normalize(vmin=18.0, vmax=40.0)
        else:
            t_candidates = [self.t_level_1, self.t_level_2]
            if self.ac_enabled:
                t_candidates.append(self.t_level_1 - 7.0)
            if self.fan_enabled:
                t_candidates.append(self.t_level_1 - 3.2)
            if self.solar_elev > 4.0:
                t_candidates.append(max(self.t_level_1, self.t_level_2) + 3.8)

            t_min_scene = min(t_candidates)
            t_max_scene = max(t_candidates)
            if t_max_scene - t_min_scene < 4.0:
                t_min_scene -= 2.0
                t_max_scene += 2.0
            global_norm = mcolors.Normalize(vmin=t_min_scene, vmax=t_max_scene)

        # 3. Renderizar superficies de la casa (Muros, Techos, Ventanas, Puertas, Pisos)
        for surf in house_surfs:
            pts = surf.vertices
            if len(pts) < 3:
                continue

            is_selected = (surf.name == self.selected_surface_name)

            if surf.surface_type == "window":
                # Ventana de cristal celeste nítido con marco perimetral y carpintería
                poly_color = (0.05, 0.75, 0.95, 0.55)
                edge_color = "#00e5ff"
                linewidth = 4.5 if is_selected else 2.4
                # Dibujar carpintería en cruz (+) para que el paño de vidrio no parezca un vano vacío
                if len(pts) == 4:
                    p0, p1, p2, p3 = pts
                    mid_h1 = [(p0[i] + p3[i]) / 2.0 for i in range(3)]
                    mid_h2 = [(p1[i] + p2[i]) / 2.0 for i in range(3)]
                    mid_v1 = [(p0[i] + p1[i]) / 2.0 for i in range(3)]
                    mid_v2 = [(p3[i] + p2[i]) / 2.0 for i in range(3)]
                    self.ax.plot([mid_h1[0], mid_h2[0]], [mid_h1[1], mid_h2[1]], [mid_h1[2], mid_h2[2]],
                                 color="#ffffff", linewidth=1.2, alpha=0.90)
                    self.ax.plot([mid_v1[0], mid_v2[0]], [mid_v1[1], mid_v2[1]], [mid_v1[2], mid_v2[2]],
                                 color="#ffffff", linewidth=1.2, alpha=0.90)
            elif surf.surface_type == "door":
                # Puerta moderna madera/vidrio
                poly_color = (0.60, 0.42, 0.28, 0.75)
                edge_color = "#8d6e63"
                linewidth = 4.5 if is_selected else 2.0
            elif surf.surface_type == "floor":
                # Losa de piso
                poly_color = (0.35, 0.38, 0.44, 0.45)
                edge_color = "#546e7a"
                linewidth = 4.5 if is_selected else 1.2
            elif surf.surface_type == "roof":
                if self.show_heatmaps and self.transparent_roof:
                    poly_color = (0.7, 0.7, 0.8, 0.08)
                    edge_color = "#ffa726"
                    linewidth = 4.5 if is_selected else 1.2
                else:
                    poly_color = (0.85, 0.55, 0.35, 0.75)
                    edge_color = "#e65100"
                    linewidth = 4.5 if is_selected else 1.5
            else:
                # Muro arquitectónico transparente (estilo maqueta limpia, ref. Greenhouse)
                if self.show_heatmaps:
                    poly_color = (0.88, 0.92, 0.98, 0.18)
                    edge_color = "#90a4ae"
                    linewidth = 4.5 if is_selected else 1.4
                else:
                    poly_color = (0.70, 0.75, 0.80, 0.85)
                    edge_color = "#455a64"
                    linewidth = 4.5 if is_selected else 1.2

            if is_selected:
                edge_color = "#ffff00"  # Resaltado amarillo brillante
                poly_color = (1.0, 1.0, 0.2, 0.50)

            poly = Poly3DCollection([pts], alpha=poly_color[3], facecolor=poly_color[:3], edgecolor=edge_color, linewidths=linewidth)
            self.ax.add_collection3d(poly)

        # 4. Renderizar obstáculos vecinos (muros perimetrales y edificios colindantes)
        if getattr(self, "show_neighbors", False):
            for obs in neighbor_surfs:
                pts = obs.vertices
                if len(pts) < 3:
                    continue
                if self.focus_mode == "house":
                    # Enfoque casa: los vecinos se dibujan como sutiles referencias alámbricas para no tapar la casa
                    poly = Poly3DCollection([pts], alpha=0.04, facecolor="#37474f", edgecolor="#546e7a", linewidths=0.8, linestyles=":")
                else:
                    # Enfoque sitio completo: volumetría completa en gris arquitectónico
                    poly = Poly3DCollection([pts], alpha=0.18, facecolor="#455a64", edgecolor="#78909c", linewidths=1.0, linestyles="--")
                self.ax.add_collection3d(poly)

        # 5. Renderizar Mapas de Calor Continuos en Pisos (Acotados a la Casa con Alturas Dinámicas)
        if self.show_heatmaps:
            l1_surfs = [s for s in house_surfs if s.level == 1]
            l2_surfs = [s for s in house_surfs if s.level == 2]

            z_l1 = hz_min + 0.05
            if l1_surfs:
                min_z1 = min(v[2] for s in l1_surfs for v in s.vertices)
                z_l1 = max(0.0, min_z1) + 0.05

            if self.floor_filter in ["all", "1"]:
                self._render_floor_heatmap(z_l1, self.t_level_1, "Nivel 1", (hx_min, hx_max), (hy_min, hy_max), global_norm)

            if hb["height"] > 2.8 and (l2_surfs or hb["height"] > 3.0):
                z_l2 = hz_min + 2.85
                if l2_surfs:
                    min_z2 = min(v[2] for s in l2_surfs for v in s.vertices)
                    if min_z2 > z_l1 + 1.2:
                        z_l2 = min_z2 + 0.05
                if self.floor_filter in ["all", "2"]:
                    self._render_floor_heatmap(z_l2, self.t_level_2, "Nivel 2", (hx_min, hx_max), (hy_min, hy_max), global_norm)

        # 6. Dibujar Equipos 3D Individuales (HVAC y Ventilación Forzada)
        if self.ac_enabled and hasattr(self, "ac_units") and self.ac_units:
            for item in self.ac_units:
                if not item.get("enabled", True):
                    continue
                ax, ay, az = item.get("x", 4.0), item.get("y", 2.5), item.get("z", 2.3)
                name = item.get("name", "A/C")
                cap_k = f"{int(round(item.get('nominal_btu_h', 24000.0)/1000.0))}k" if not item.get("is_auto", False) else "Auto"
                self.ax.scatter([ax], [ay], [az], color="#00e5ff", s=220, marker="s", edgecolors="#ffffff", linewidths=1.8)
                self.ax.text(ax, ay, az + 0.28, f"[{name} {cap_k}]", color="#00e5ff", fontsize=8, fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.25", facecolor="#00363a", alpha=0.92, edgecolor="#00e5ff"))

        if self.fan_enabled and hasattr(self, "fan_units") and self.fan_units:
            for item in self.fan_units:
                if not item.get("enabled", True):
                    continue
                fx, fy, fz = item.get("x", 4.0), item.get("y", 2.5), item.get("z", 2.55)
                name = item.get("name", "Vent")
                mount = item.get("mount", "techo")
                m_tag = "Techo" if mount == "techo" else ("Mural" if mount == "pared_alta" else "Pedestal")
                self.ax.scatter([fx], [fy], [fz], color="#4caf50", s=180, marker="o", edgecolors="#ffffff", linewidths=1.8)
                self.ax.text(fx, fy, fz + 0.28, f"[{name} - {m_tag}]", color="#81c784", fontsize=8, fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.25", facecolor="#1b5e20", alpha=0.92, edgecolor="#81c784"))

        if self.eolic_enabled and hasattr(self, "eolic_units") and self.eolic_units:
            for item in self.eolic_units:
                if not item.get("enabled", True):
                    continue
                ex, ey, ez = item.get("x", 4.0), item.get("y", 2.5), item.get("z", 5.6)
                name = item.get("name", "Eolico")
                self.ax.scatter([ex], [ey], [ez], color="#ff9800", s=220, marker="^", edgecolors="#ffffff", linewidths=1.8)
                self.ax.text(ex, ey, ez + 0.38, f"[{name}]", color="#ffb74d", fontsize=8, fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.25", facecolor="#4e342e", alpha=0.92, edgecolor="#ff9800"))

        if self.exhaust_enabled and hasattr(self, "exhaust_units") and self.exhaust_units:
            for item in self.exhaust_units:
                if not item.get("enabled", True):
                    continue
                mx, my, mz = item.get("x", 4.0), item.get("y", 2.5), item.get("z", 2.4)
                name = item.get("name", "Extr")
                self.ax.scatter([mx], [my], [mz], color="#e91e63", s=200, marker="h", edgecolors="#ffffff", linewidths=1.8)
                self.ax.text(mx, my, mz + 0.28, f"[{name}]", color="#f48fb1", fontsize=8, fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.25", facecolor="#4a148c", alpha=0.92, edgecolor="#e91e63"))

        if self.supply_enabled and hasattr(self, "supply_units") and self.supply_units:
            for item in self.supply_units:
                if not item.get("enabled", True):
                    continue
                sx, sy, sz = item.get("x", 4.0), item.get("y", 2.5), item.get("z", 2.0)
                name = item.get("name", "Iny")
                self.ax.scatter([sx], [sy], [sz], color="#00bcd4", s=190, marker="D", edgecolors="#ffffff", linewidths=1.8)
                self.ax.text(sx, sy, sz + 0.28, f"[{name}]", color="#80deea", fontsize=8, fontweight="bold",
                             bbox=dict(boxstyle="round,pad=0.25", facecolor="#004d40", alpha=0.92, edgecolor="#00bcd4"))

        # 7. ENFOQUE INTELIGENTE Y BLOQUEO DE SUELO A Z=0
        if self.focus_mode == "house" or not neighbor_surfs:
            center_x = (hx_min + hx_max) / 2.0
            center_y = (hy_min + hy_max) / 2.0
            half = (max_span / 2.0) * 1.42 * self.zoom_factor
        else:
            all_pts = [v for s in (house_surfs + neighbor_surfs) for v in s.vertices]
            pts_arr = np.array(all_pts)
            min_xyz = np.min(pts_arr, axis=0)
            max_xyz = np.max(pts_arr, axis=0)
            center_x = (min_xyz[0] + max_xyz[0]) / 2.0
            center_y = (min_xyz[1] + max_xyz[1]) / 2.0
            spans = max_xyz - min_xyz
            max_span = max(float(spans[0]), float(spans[1]), float(spans[2]), 8.0)
            half = (max_span / 2.0) * 1.25 * self.zoom_factor

        self.ax.set_xlim(center_x - half, center_x + half)
        self.ax.set_ylim(center_y - half, center_y + half)
        # Z empieza estrictamente en 0.0 (fijo al suelo sólido)
        z_max_val = max(hz_max, 4.0) * 1.35 * self.zoom_factor
        self.ax.set_zlim(0.0, z_max_val)

        # Proporción geométrica 1:1:1 bloqueada a escala física real (nunca se deforma al rotar o hacer zoom)
        self.ax.set_box_aspect((2.0 * half, 2.0 * half, z_max_val))
        self.ax.dist = 10.0

        # 8. Barra de Color Térmica (en eje dedicado cax, 100% estable sin encoger el 3D)
        self.cax.clear()
        if self.show_heatmaps:
            self.cax.set_visible(True)
            cmap = mpl.colormaps[self.color_palette]
            sm = mpl.cm.ScalarMappable(cmap=cmap, norm=global_norm)
            sm.set_array([])
            self.cbar = self.fig.colorbar(sm, cax=self.cax)
            self.cbar.set_label("Temperatura (°C) - EM.110", color="#ffffff", fontsize=8, fontweight="bold")
            if self.use_fixed_scale:
                self.cbar.set_ticks([18, 21, 24, 27, 30, 33, 36, 40])
                self.cbar.set_ticklabels(["18°", "21°", "24° (Conf)", "27°", "30°", "33°", "36°", "40°C"])
            self.cbar.ax.tick_params(colors="#ffffff", labelsize=7)
        else:
            self.cax.set_visible(False)

        # 9. Flecha de Norte 3D (Brújula) sobre el terreno en primer plano
        corner_x = center_x - half * 0.65
        corner_y = center_y - half * 0.65
        corner_z = 0.02
        arrow_len = half * 0.25
        north_rad = np.radians(self.north_deg)
        nx = corner_x + arrow_len * np.sin(north_rad)
        ny = corner_y + arrow_len * np.cos(north_rad)

        self.ax.plot([corner_x, nx], [corner_y, ny], [corner_z, corner_z], color="#ff1744", linewidth=2.8)
        self.ax.scatter([nx], [ny], [corner_z], color="#ff1744", s=110, marker="^", edgecolors="#ffffff", linewidths=1.5)
        self.ax.text(nx, ny, corner_z + 0.15, "N (Norte)", color="#ffffff", fontsize=8, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.25", facecolor="#b71c1c", alpha=0.92, edgecolor="#ff1744"))

        # 10. Vector Solar Orientado Astronómicamente
        if self.solar_elev > 0:
            phi_rel = self.solar_azim - self.north_deg
            rad_elev = np.radians(self.solar_elev)
            rad_phi = np.radians(phi_rel)
            dist = max_span * 1.55

            sun_x = center_x + dist * np.cos(rad_elev) * np.sin(rad_phi)
            sun_y = center_y + dist * np.cos(rad_elev) * np.cos(rad_phi)
            sun_z = max_span * 0.4 + dist * np.sin(rad_elev) * 0.85

            # Esfera del Sol
            self.ax.scatter([sun_x], [sun_y], [sun_z], color="#ffd700", s=220, edgecolors="#ff8800", linewidths=2.0)

            # Punto de impacto en la fachada expuesta al sol
            impact_x = center_x + (hb["len_x"] / 2.0) * np.sin(rad_phi)
            impact_y = center_y + (hb["len_y"] / 2.0) * np.cos(rad_phi)
            impact_z = hz_min + (hb["height"] * 0.65)

            # Rayo solar conectando el sol con la fachada soleada
            self.ax.plot([sun_x, impact_x], [sun_y, impact_y], [sun_z, impact_z],
                         color="#ffeb3b", linestyle=":", linewidth=2.0, alpha=0.85)

        if elev is not None and azim is not None:
            self.ax.view_init(elev=elev, azim=azim)
        else:
            self.ax.view_init(elev=25, azim=-60)

        self.canvas.draw_idle()
