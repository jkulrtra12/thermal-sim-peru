"""
Modelo geométrico 3D de la edificación y su entorno (obstáculos y muros vecinos).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np


@dataclass
class Surface3D:
    """Superficie poligonal 3D (muro, techo, ventana o muro vecino)."""
    name: str
    surface_type: str  # 'wall', 'roof', 'floor', 'window', 'neighbor_wall'
    level: int  # 1, 2 o 0 (si es obstáculo vecino)
    vertices: List[Tuple[float, float, float]]  # [(x, y, z), ...]
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    area_m2: float = 0.0
    orientation: str = "Horizontal"  # 'Norte', 'Sur', 'Este', 'Oeste', 'Techo', 'Piso'
    component_name: str = ""
    thickness_m: float = 0.15
    material_name: str = ""

    def __post_init__(self):
        if not self.area_m2 and len(self.vertices) >= 3:
            self._compute_geometry()

    def _compute_geometry(self):
        pts = np.array(self.vertices)
        if len(pts) < 3:
            return

        # Vector normal mediante producto cruz de dos aristas
        v1 = pts[1] - pts[0]
        v2 = pts[2] - pts[0]
        normal_vec = np.cross(v1, v2)
        norm = np.linalg.norm(normal_vec)
        if norm > 1e-6:
            normal_vec = normal_vec / norm
            self.normal = (float(normal_vec[0]), float(normal_vec[1]), float(normal_vec[2]))

        # Área de polígono 3D
        if len(pts) == 3:
            self.area_m2 = 0.5 * norm
        elif len(pts) == 4:
            # Cuadrilátero como 2 triángulos
            t1 = 0.5 * np.linalg.norm(np.cross(pts[1] - pts[0], pts[2] - pts[0]))
            t2 = 0.5 * np.linalg.norm(np.cross(pts[2] - pts[0], pts[3] - pts[0]))
            self.area_m2 = float(t1 + t2)

        # Determinar orientación por la normal
        nx, ny, nz = self.normal
        if nz > 0.7:
            self.orientation = "Techo"
        elif nz < -0.7:
            self.orientation = "Piso"
        elif abs(ny) >= abs(nx):
            self.orientation = "Norte" if ny > 0 else "Sur"
        else:
            self.orientation = "Este" if nx > 0 else "Oeste"


@dataclass
class BuildingGeometry3D:
    """Colección completa de superficies 3D del proyecto."""
    surfaces: List[Surface3D] = field(default_factory=list)
    neighbor_obstacles: List[Surface3D] = field(default_factory=list)

    def add_surface(self, surface: Surface3D):
        if surface.surface_type == "neighbor_wall":
            self.neighbor_obstacles.append(surface)
        else:
            self.surfaces.append(surface)

    @classmethod
    def create_default_building(
        cls,
        length: float = 8.0,
        width: float = 5.0,
        height_piso: float = 2.8,
        num_floors: int = 2,
        neighbor_east_height: float = 6.0,
        neighbor_west_height: float = 5.0,
    ) -> "BuildingGeometry3D":
        """
        Crea un modelo 3D por defecto paramétrico similar al modelo de SketchUp del usuario:
        Edificación de 1 o 2 niveles con ventanas frontales y muros vecinos altos en los costados.
        """
        model = cls()

        for floor in range(1, num_floors + 1):
            z_bot = (floor - 1) * height_piso
            z_top = floor * height_piso

            # Muro Sur (Frontal - con vanos de ventanas)
            # Fachada frontal en Y = 0
            model.add_surface(Surface3D(
                name=f"Muro_Frontal_Sur_N{floor}",
                surface_type="wall",
                level=floor,
                vertices=[(0.0, 0.0, z_bot), (length, 0.0, z_bot), (length, 0.0, z_top), (0.0, 0.0, z_top)],
                orientation="Sur"
            ))

            # Muro Norte (Posterior) en Y = width
            model.add_surface(Surface3D(
                name=f"Muro_Posterior_Norte_N{floor}",
                surface_type="wall",
                level=floor,
                vertices=[(length, width, z_bot), (0.0, width, z_bot), (0.0, width, z_top), (length, width, z_top)],
                orientation="Norte"
            ))

            # Muro Este (Lateral Derecho) en X = length
            model.add_surface(Surface3D(
                name=f"Muro_Lateral_Este_N{floor}",
                surface_type="wall",
                level=floor,
                vertices=[(length, 0.0, z_bot), (length, width, z_bot), (length, width, z_top), (length, 0.0, z_top)],
                orientation="Este"
            ))

            # Muro Oeste (Lateral Izquierdo) en X = 0
            model.add_surface(Surface3D(
                name=f"Muro_Lateral_Oeste_N{floor}",
                surface_type="wall",
                level=floor,
                vertices=[(0.0, width, z_bot), (0.0, 0.0, z_bot), (0.0, 0.0, z_top), (0.0, width, z_top)],
                orientation="Oeste"
            ))

            # Ventanas frontales (en muro sur)
            w_w = 1.6
            w_h = 1.2
            w_sill = 1.0
            model.add_surface(Surface3D(
                name=f"Ventana_1_N{floor}",
                surface_type="window",
                level=floor,
                vertices=[(1.5, -0.02, z_bot + w_sill), (1.5 + w_w, -0.02, z_bot + w_sill), (1.5 + w_w, -0.02, z_bot + w_sill + w_h), (1.5, -0.02, z_bot + w_sill + w_h)],
                orientation="Sur"
            ))
            model.add_surface(Surface3D(
                name=f"Ventana_2_N{floor}",
                surface_type="window",
                level=floor,
                vertices=[(4.5, -0.02, z_bot + w_sill), (4.5 + w_w, -0.02, z_bot + w_sill), (4.5 + w_w, -0.02, z_bot + w_sill + w_h), (4.5, -0.02, z_bot + w_sill + w_h)],
                orientation="Sur"
            ))

            # Techo/Cubierta (en el último piso)
            if floor == num_floors:
                model.add_surface(Surface3D(
                    name="Cubierta_Techo",
                    surface_type="roof",
                    level=floor,
                    vertices=[(0.0, 0.0, z_top), (length, 0.0, z_top), (length, width, z_top), (0.0, width, z_top)],
                    orientation="Techo"
                ))

        # Muros vecinos colindantes (Obstáculos pasivos de sombra)
        if neighbor_east_height > 0:
            # Muro colindante en el lado Este (X = length + 0.3)
            x_obs = length + 0.3
            model.add_surface(Surface3D(
                name="Muro_Vecino_Colindante_Este",
                surface_type="neighbor_wall",
                level=0,
                vertices=[(x_obs, -1.0, 0.0), (x_obs, width + 1.0, 0.0), (x_obs, width + 1.0, neighbor_east_height), (x_obs, -1.0, neighbor_east_height)],
                orientation="Este"
            ))

        if neighbor_west_height > 0:
            # Muro colindante en el lado Oeste (X = -0.3)
            x_obs = -0.3
            model.add_surface(Surface3D(
                name="Muro_Vecino_Colindante_Oeste",
                surface_type="neighbor_wall",
                level=0,
                vertices=[(x_obs, width + 1.0, 0.0), (x_obs, -1.0, 0.0), (x_obs, -1.0, neighbor_west_height), (x_obs, width + 1.0, neighbor_west_height)],
                orientation="Oeste"
            ))

        return model
