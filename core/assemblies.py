"""
Módulo de Ensambles Constructivos Multicapa.
Permite combinar cubiertas con cielos rasos (con y sin cámara de aire),
muros con aislantes o multicapas, calculando transmitancia U global y masa térmica.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from core.materials import Material


# Resistencias superficiales estándar según ISO 6946 y Norma Técnica EM.110 (m²·K/W)
R_SE_HORIZONTAL = 0.04   # Muros hacia el exterior
R_SI_HORIZONTAL = 0.13   # Muros cara interior

R_SE_ROOF_SUMMER = 0.04  # Techo cara exterior (flujo descendente en calor)
R_SI_ROOF_SUMMER = 0.10  # Techo cara interior


@dataclass
class RoofCeilingAssembly:
    """
    Ensamble compuesto de Cubierta Superior + Cámara de Aire + Cielo Raso.
    """
    name: str
    roof_material: Material
    ceiling_material: Optional[Material] = None
    has_air_cavity: bool = True
    cavity_thickness_m: float = 0.15  # 15 cm típico entre techo y cielo raso
    cavity_ventilated: bool = False   # True si hay extractores eólicos aliviando la cámara

    @property
    def cavity_thermal_resistance(self) -> float:
        """Resistencia térmica de la cámara de aire intermedia (m²·K/W)."""
        if not self.ceiling_material or not self.has_air_cavity:
            return 0.0
        if self.cavity_ventilated:
            # En cámara muy ventilada por extractores, el calor se evacúa directamente al exterior
            return 0.05
        # Cámara estanca / no ventilada horizontal-inclinada
        return 0.17

    @property
    def total_thermal_resistance(self) -> float:
        """Resistencia térmica total R_total (m²·K/W) incluyendo resistencias superficiales."""
        r_sum = R_SE_ROOF_SUMMER + R_SI_ROOF_SUMMER
        r_sum += self.roof_material.thermal_resistance

        if self.ceiling_material:
            r_sum += self.cavity_thermal_resistance
            r_sum += self.ceiling_material.thermal_resistance

        return r_sum

    @property
    def u_value(self) -> float:
        """Transmitancia térmica U (W/m²·K) del ensamble techo-cielo raso."""
        r_tot = self.total_thermal_resistance
        return 1.0 / r_tot if r_tot > 0 else 999.0

    @property
    def effective_solar_absorptance(self) -> float:
        """Absortancia solar de la cara externa expuesta."""
        return self.roof_material.solar_absorptance

    @property
    def total_thickness(self) -> float:
        """Espesor total en metros."""
        t = self.roof_material.thickness
        if self.ceiling_material:
            t += self.cavity_thickness_m + self.ceiling_material.thickness
        return t

    @property
    def description(self) -> str:
        ceiling_str = self.ceiling_material.name if self.ceiling_material else "Sin Cielo Raso"
        vent_str = " (Cámara Ventilada con Extractor)" if (self.ceiling_material and self.cavity_ventilated) else ""
        return f"{self.roof_material.name} + {ceiling_str}{vent_str} -> U = {self.u_value:.2f} W/m²K"


@dataclass
class WallAssembly:
    """
    Ensamble de Muro (monocapa o multicapa).
    """
    name: str
    main_material: Material
    insulation_material: Optional[Material] = None
    finish_material: Optional[Material] = None

    @property
    def total_thermal_resistance(self) -> float:
        """R_total (m²·K/W) con resistencias superficiales."""
        r_sum = R_SE_HORIZONTAL + R_SI_HORIZONTAL
        r_sum += self.main_material.thermal_resistance
        if self.insulation_material:
            r_sum += self.insulation_material.thermal_resistance
        if self.finish_material:
            r_sum += self.finish_material.thermal_resistance
        return r_sum

    @property
    def u_value(self) -> float:
        """Transmitancia térmica U (W/m²·K)."""
        r_tot = self.total_thermal_resistance
        return 1.0 / r_tot if r_tot > 0 else 999.0

    @property
    def effective_solar_absorptance(self) -> float:
        return self.main_material.solar_absorptance

    @property
    def total_thickness(self) -> float:
        t = self.main_material.thickness
        if self.insulation_material:
            t += self.insulation_material.thickness
        if self.finish_material:
            t += self.finish_material.thickness
        return t
