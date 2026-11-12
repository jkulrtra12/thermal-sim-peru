"""
Módulo de Cálculo de Sombras 3D y Obstáculos Vecinos.
Calcula el factor de sombreado horario para Nivel 1 y Nivel 2
proyectado por muros perimetrales, medianeras y edificaciones colindantes.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class NeighborObstacle:
    """Obstáculo vecino o muro perimetral colindante."""
    name: str
    direction: str  # 'Norte', 'Sur', 'Este', 'Oeste'
    height_m: float  # Altura del muro u obstáculo en metros
    distance_to_wall_m: float = 0.5  # Distancia al muro de la edificación propia (0.0 a 5.0m)


class SolarShadingCalculator:
    """Calculador de factor de sombra solar horario."""

    DIRECTION_AZIMUTHS = {
        "Norte": 0.0,
        "Este": 90.0,
        "Sur": 180.0,
        "Oeste": 270.0,
    }

    @classmethod
    def calculate_facade_shading_factor(
        cls,
        facade_direction: str,
        level: int,  # 1 o 2
        level_height_m: float,  # ej. 2.8m por piso
        solar_elevation_deg: float,
        solar_azimuth_deg: float,
        obstacles: List[NeighborObstacle]
    ) -> float:
        """
        Calcula la fracción de la fachada que queda en sombra (0.0 = totalmente al sol, 1.0 = totalmente en sombra).
        """
        if solar_elevation_deg <= 0.0:
            return 1.0  # Sin sol directo (noche)

        facade_azimuth = cls.DIRECTION_AZIMUTHS.get(facade_direction, 0.0)

        # Ángulo entre el sol y la normal de la fachada
        azimuth_diff = abs(solar_azimuth_deg - facade_azimuth)
        if azimuth_diff > 180.0:
            azimuth_diff = 360.0 - azimuth_diff

        # Si el sol está detrás de la fachada, la fachada está en auto-sombra
        if azimuth_diff >= 90.0:
            return 1.0

        # Buscar si hay un obstáculo en esta dirección
        matching_obs = [obs for obs in obstacles if obs.direction == facade_direction]
        if not matching_obs:
            return 0.0  # Sin obstáculo vecino: totalmente expuesto al sol

        obs = matching_obs[0]

        # Altura de la base y tope del nivel evaluado
        y_bottom = (level - 1) * level_height_m
        y_top = level * level_height_m

        # Proyección de la longitud de sombra proyectada por el obstáculo
        # Longitud sombra = (H_obs - Y) / tan(elevación)
        elev_rad = math.radians(solar_elevation_deg)
        tan_elev = math.tan(elev_rad)
        if tan_elev < 1e-4:
            return 1.0

        # Altura a la que llega la sombra en la pared propia situada a distancia D
        # H_sombra_en_pared = H_obs - (D * tan(elevación) / cos(azimuth_diff))
        cos_diff = math.cos(math.radians(azimuth_diff))
        if cos_diff < 0.05:
            return 1.0

        effective_dist = obs.distance_to_wall_m / cos_diff
        shadow_height_at_wall = obs.height_m - (effective_dist * tan_elev)

        if shadow_height_at_wall <= y_bottom:
            # La sombra no alcanza la base de este piso -> Totalmente al sol
            return 0.0
        elif shadow_height_at_wall >= y_top:
            # La sombra cubre totalmente este piso
            return 1.0
        else:
            # Sombra parcial
            fraction = (shadow_height_at_wall - y_bottom) / (y_top - y_bottom)
            return max(0.0, min(1.0, fraction))
