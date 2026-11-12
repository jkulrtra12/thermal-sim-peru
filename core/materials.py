"""
Módulo de Catálogo de Materiales y Ensambles Térmicos para Perú.
Incluye soporte para materiales predefinidos y Materiales Personalizados ("Custom").
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class Material:
    """Propiedades termofísicas de un material constructivo."""
    name: str
    category: str  # 'techo', 'cielo_raso', 'muro', 'aislante', 'ventana'
    thickness: float  # Espesor en metros (m)
    conductivity: float  # Conductividad térmica lambda (W/m·K). Si es 0, se usa R directa
    thermal_resistance: float = 0.0  # Resistencia térmica R (m²·K/W)
    solar_absorptance: float = 0.6  # Absortancia solar (alfa), 0.0 a 1.0 (claro a oscuro)
    density: float = 1800.0  # Densidad (kg/m³)
    specific_heat: float = 1000.0  # Calor específico (J/kg·K)
    is_custom: bool = False
    description: str = ""

    def __post_init__(self):
        # Si no se definió R directamente y la conductividad es > 0, calcular R = d / lambda
        if self.thermal_resistance <= 0.0 and self.conductivity > 0.0:
            self.thermal_resistance = self.thickness / self.conductivity
        elif self.thermal_resistance > 0.0 and self.conductivity <= 0.0 and self.thickness > 0.0:
            self.conductivity = self.thickness / self.thermal_resistance

    @property
    def direct_u_value(self) -> float:
        """Transmitancia térmica U directa del material (W/m²·K) sin resistencias superficiales (1/R)."""
        if self.thermal_resistance > 0.0:
            return 1.0 / self.thermal_resistance
        return 999.0

    @property
    def u_value(self) -> float:
        """
        Transmitancia térmica U (W/m²·K) según ISO 6946 y RNE Norma EM.110,
        incorporando las resistencias superficiales estándar de película de aire (R_si + R_se).
        - Para cerramientos verticales (muros y ventanas): R_si + R_se = 0.13 + 0.04 = 0.17 m²·K/W.
        - Para techos y cubiertas: R_si + R_se = 0.10 + 0.04 = 0.14 m²·K/W.
        """
        r_surf = 0.14 if self.category in ("techo", "cielo_raso") else 0.17
        r_tot = self.thermal_resistance + r_surf
        if r_tot > 0.0:
            return 1.0 / r_tot
        return 999.0

    def with_thickness(self, new_thickness_m: float) -> "Material":
        """Retorna una copia del material con un nuevo espesor, recalculando su resistencia térmica."""
        cond = self.conductivity
        new_t = max(0.0001, new_thickness_m)
        r_new = new_t / cond if cond > 0.0 else (self.thermal_resistance * (new_t / max(0.0001, self.thickness)))
        return Material(
            name=f"{self.name} ({new_t*1000:.1f}mm)",
            category=self.category,
            thickness=new_t,
            conductivity=cond,
            thermal_resistance=r_new,
            solar_absorptance=self.solar_absorptance,
            density=self.density,
            specific_heat=self.specific_heat,
            is_custom=self.is_custom,
            description=self.description
        )


# ==============================================================================
# CATÁLOGO DE MATERIALES PREDEFINIDOS PARA PERÚ
# ==============================================================================

PREDEFINED_ROOFS: Dict[str, Material] = {
    "UPVC 2.0 mm": Material(
        name="UPVC 2.0 mm",
        category="techo",
        thickness=0.002,
        conductivity=0.17,
        solar_absorptance=0.45,
        density=1400.0,
        specific_heat=1050.0,
        description="Plancha ondulada/trapezoidal de UPVC de 2.0 mm. Excelente resistencia anticorrosiva."
    ),
    "UPVC 2.5 mm": Material(
        name="UPVC 2.5 mm",
        category="techo",
        thickness=0.0025,
        conductivity=0.17,
        solar_absorptance=0.45,
        density=1400.0,
        specific_heat=1050.0,
        description="Plancha de UPVC de 2.5 mm con protección UV de alta durabilidad."
    ),
    "UPVC 3.0 mm": Material(
        name="UPVC 3.0 mm",
        category="techo",
        thickness=0.003,
        conductivity=0.17,
        solar_absorptance=0.40,
        density=1400.0,
        specific_heat=1050.0,
        description="Plancha de UPVC de 3.0 mm para cubiertas industriales de alta exigencia acústica y térmica."
    ),
    "Termotecho 5 cm (PUR 50mm)": Material(
        name="Termotecho 5 cm (PUR 50mm)",
        category="techo",
        thickness=0.05,
        conductivity=0.022,
        thermal_resistance=2.27,
        solar_absorptance=0.30,  # Cara superior blanca/marfil
        density=40.0,
        specific_heat=1400.0,
        description="Panel sándwich con caras de acero prepintado y núcleo aislante PUR de 50 mm (U = 0.44 W/m²K)."
    ),
    "Termotecho 10 cm (PUR 100mm)": Material(
        name="Termotecho 10 cm (PUR 100mm)",
        category="techo",
        thickness=0.10,
        conductivity=0.022,
        thermal_resistance=4.54,
        solar_absorptance=0.30,
        density=40.0,
        specific_heat=1400.0,
        description="Panel sándwich con núcleo PUR de 100 mm para máximo aislamiento térmico (U = 0.22 W/m²K)."
    ),
    "Techo Aluzinc Simple (Calibre 26)": Material(
        name="Techo Aluzinc Simple (Calibre 26)",
        category="techo",
        thickness=0.0005,
        conductivity=50.0,
        thermal_resistance=0.0001,
        solar_absorptance=0.65,
        density=7850.0,
        specific_heat=480.0,
        description="Chapa trapezoidal de Aluzinc simple. Alta transferencia de calor solar si no cuenta con aislante."
    ),
    "Losa Aligerada Concreto (20 cm)": Material(
        name="Losa Aligerada Concreto (20 cm)",
        category="techo",
        thickness=0.20,
        conductivity=1.10,
        thermal_resistance=0.25,
        solar_absorptance=0.70,
        density=1800.0,
        specific_heat=1000.0,
        description="Losa tradicional con viguetas de concreto y bovedillas de arcilla con ladrillo pastelero superior."
    ),
}

PREDEFINED_CEILINGS: Dict[str, Optional[Material]] = {
    "Sin Cielo Raso": None,
    "Fibra Mineral (15 mm / 5/8\")": Material(
        name="Fibra Mineral (15 mm / 5/8\")",
        category="cielo_raso",
        thickness=0.015,
        conductivity=0.052,
        thermal_resistance=0.29,
        solar_absorptance=0.25,
        density=350.0,
        specific_heat=1100.0,
        description="Baldoza suspendida de fibra mineral acústica y termoaislante."
    ),
    "Fibrocemento (Superboard 6 mm)": Material(
        name="Fibrocemento (Superboard 6 mm)",
        category="cielo_raso",
        thickness=0.006,
        conductivity=0.25,
        thermal_resistance=0.024,
        solar_absorptance=0.50,
        density=1350.0,
        specific_heat=1000.0,
        description="Placa plana de fibrocemento de 6 mm para cielo raso suspendido continuo resistente a la humedad."
    ),
}

PREDEFINED_WALLS: Dict[str, Material] = {
    "Ladrillo King Kong 18 huecos (Tarrajeado 15 cm)": Material(
        name="Ladrillo King Kong 18 huecos (Tarrajeado 15 cm)",
        category="muro",
        thickness=0.15,
        conductivity=0.68,
        thermal_resistance=0.22,
        solar_absorptance=0.60,
        density=1700.0,
        specific_heat=900.0,
        description="Muro tradicional de arcilla cocida tarrajeado en ambas caras. Alta masa térmica."
    ),
    "Ladrillo Pandereta (12 cm)": Material(
        name="Ladrillo Pandereta (12 cm)",
        category="muro",
        thickness=0.12,
        conductivity=0.55,
        thermal_resistance=0.21,
        solar_absorptance=0.60,
        density=1200.0,
        specific_heat=900.0,
        description="Ladrillo hueco de arcilla usado habitualmente en tabiquería y divisiones ligeras."
    ),
    "Bloques de Concreto Alveolares (Parcialmente Rellenos 14 cm)": Material(
        name="Bloques de Concreto Alveolares (Parcialmente Rellenos 14 cm)",
        category="muro",
        thickness=0.14,
        conductivity=0.72,
        thermal_resistance=0.28,
        solar_absorptance=0.65,
        density=1600.0,
        specific_heat=1000.0,
        description="Albañilería armada con bloques de concreto huecos, alvéolos con refuerzo y celdas de aire intermedias."
    ),
    "Termomuro 5 cm (PUR 50mm)": Material(
        name="Termomuro 5 cm (PUR 50mm)",
        category="muro",
        thickness=0.05,
        conductivity=0.022,
        thermal_resistance=2.27,
        solar_absorptance=0.35,
        density=40.0,
        specific_heat=1400.0,
        description="Panel autoportante sándwich con caras de acero y núcleo de poliuretano inyectado de 50 mm."
    ),
    "Termomuro 10 cm (PUR 100mm)": Material(
        name="Termomuro 10 cm (PUR 100mm)",
        category="muro",
        thickness=0.10,
        conductivity=0.022,
        thermal_resistance=4.54,
        solar_absorptance=0.35,
        density=40.0,
        specific_heat=1400.0,
        description="Panel aislante para cámaras y muros de alta exigencia energética (U = 0.22 W/m²K)."
    ),
    "Fibrocemento SIN aislante (Doble placa 8 mm)": Material(
        name="Fibrocemento SIN aislante (Doble placa 8 mm)",
        category="muro",
        thickness=0.08,
        conductivity=0.35,
        thermal_resistance=0.23,
        solar_absorptance=0.55,
        density=1300.0,
        specific_heat=1000.0,
        description="Tabique de perfilería metálica galvanizada con placa de fibrocemento exterior e interior y cámara hueca."
    ),
    "Fibrocemento CON aislante (Lana de Vidrio 50 mm)": Material(
        name="Fibrocemento CON aislante (Lana de Vidrio 50 mm)",
        category="muro",
        thickness=0.09,
        conductivity=0.045,
        thermal_resistance=1.35,
        solar_absorptance=0.55,
        density=400.0,
        specific_heat=950.0,
        description="Sistema de fachada ligera con placas de fibrocemento y aislamiento termoacústico de lana de vidrio."
    ),
    "Concreto Armado (15 cm)": Material(
        name="Concreto Armado (15 cm)",
        category="muro",
        thickness=0.15,
        conductivity=1.74,
        thermal_resistance=0.086,
        solar_absorptance=0.70,
        density=2400.0,
        specific_heat=1000.0,
        description="Muro estructural de placas de concreto armado con gran masa e inercia térmica."
    ),
}

PREDEFINED_WINDOWS: Dict[str, Material] = {
    "Vidrio Simple Claro 4 mm": Material(
        name="Vidrio Simple Claro 4 mm",
        category="ventana",
        thickness=0.004,
        conductivity=1.0,
        thermal_resistance=0.004,
        solar_absorptance=0.15,
        density=2500.0,
        specific_heat=840.0,
        description="Vidrio simple transparente de 4 mm. Factor solar SHGC = 0.82, U = 5.7 W/m²K."
    ),
    "Vidrio Simple Claro 6 mm": Material(
        name="Vidrio Simple Claro 6 mm",
        category="ventana",
        thickness=0.006,
        conductivity=1.0,
        thermal_resistance=0.006,
        solar_absorptance=0.16,
        density=2500.0,
        specific_heat=840.0,
        description="Vidrio simple transparente de 6 mm. SHGC = 0.79, U = 5.6 W/m²K."
    ),
    "Vidrio Templado Tintado / Control Solar 6 mm": Material(
        name="Vidrio Templado Tintado / Control Solar 6 mm",
        category="ventana",
        thickness=0.006,
        conductivity=1.0,
        thermal_resistance=0.006,
        solar_absorptance=0.45,
        density=2500.0,
        specific_heat=840.0,
        description="Vidrio de control solar (bronce/gris/verde). SHGC = 0.50, U = 5.4 W/m²K."
    ),
    "Doble Vidrio Hermético DVH (4-12-4 mm)": Material(
        name="Doble Vidrio Hermético DVH (4-12-4 mm)",
        category="ventana",
        thickness=0.020,
        conductivity=0.07,
        thermal_resistance=0.35,
        solar_absorptance=0.20,
        density=1800.0,
        specific_heat=840.0,
        description="Doble acristalamiento con cámara de aire de 12 mm. SHGC = 0.65, U = 2.8 W/m²K."
    ),
}


def create_custom_material(
    name: str,
    category: str,
    thickness_m: float,
    conductivity_w_mk: Optional[float] = None,
    thermal_resistance_r: Optional[float] = None,
    solar_absorptance: float = 0.6,
    density_kg_m3: float = 1600.0,
    specific_heat_j_kgk: float = 1000.0,
    description: str = "Material personalizado por el usuario"
) -> Material:
    """
    Crea un material personalizado permitiendo definir R directamente o mediante
    espesor (m) y conductividad térmica lambda (W/m·K).
    """
    cond = conductivity_w_mk if conductivity_w_mk is not None else 0.0
    r_val = thermal_resistance_r if thermal_resistance_r is not None else 0.0

    if r_val <= 0.0 and cond > 0.0 and thickness_m > 0.0:
        r_val = thickness_m / cond
    elif r_val > 0.0 and cond <= 0.0 and thickness_m > 0.0:
        cond = thickness_m / r_val

    return Material(
        name=name,
        category=category,
        thickness=max(0.0001, thickness_m),
        conductivity=cond,
        thermal_resistance=r_val,
        solar_absorptance=max(0.05, min(0.98, solar_absorptance)),
        density=density_kg_m3,
        specific_heat=specific_heat_j_kgk,
        is_custom=True,
        description=description
    )


ALL_MATERIALS: Dict[str, Material] = {}
for _d in [PREDEFINED_ROOFS, PREDEFINED_WALLS, PREDEFINED_WINDOWS]:
    ALL_MATERIALS.update(_d)
for _k, _v in PREDEFINED_CEILINGS.items():
    if _v is not None:
        ALL_MATERIALS[_k] = _v
