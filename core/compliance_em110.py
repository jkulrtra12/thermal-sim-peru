"""
Módulo de Verificación Normativa EM.110 (RNE - Perú).
"Confort Térmico y Lumínico con Eficiencia Energética".
Evalúa si los materiales de muros, techos y vidrios cumplen los valores límite
de transmitancia térmica (U_max) según la Zona Bioclimática del Perú.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class BioclimaticLimitEM110:
    zone_code: str
    zone_name: str
    max_u_roof: float   # W/m²·K (Valor máximo admisible)
    max_u_wall: float   # W/m²·K
    max_shgc_glass: float  # Factor solar máximo de ventanas
    natural_vent_required: bool
    description: str


# Tabla de límites máximos admisibles según la Norma EM.110
BIOCLIMATIC_ZONES_EM110: Dict[str, BioclimaticLimitEM110] = {
    "Costa": BioclimaticLimitEM110(
        zone_code="Zona 1 / 2",
        zone_name="Desértico / Marino (Costa)",
        max_u_roof=1.00,   # Techos deben aislar radiación
        max_u_wall=2.30,   # Ladrillo tarrajeado o bloque aislado
        max_shgc_glass=0.60,
        natural_vent_required=True,
        description="Requiere protección solar en techos, colores claros y ventilación nocturna/cruzada."
    ),
    "Sierra": BioclimaticLimitEM110(
        zone_code="Zona 4 / 5",
        zone_name="Mesoandino / Altoandino (Sierra)",
        max_u_roof=0.85,   # Alto aislamiento de techo contra heladas
        max_u_wall=1.80,   # Muros con inercia o aislamiento
        max_shgc_glass=0.75, # Permitir ganancia solar diurna
        natural_vent_required=False,
        description="Requiere alta inercia térmica, captación solar diurna y hermeticidad nocturna."
    ),
    "Selva": BioclimaticLimitEM110(
        zone_code="Zona 8 / 9",
        zone_name="Selva Alta y Baja (Tropical)",
        max_u_roof=0.80,   # Techo con cámara muy ventilada o panel aislante
        max_u_wall=2.00,
        max_shgc_glass=0.50,
        natural_vent_required=True,
        description="Ventilación cruzada continua obligatoria, aleros amplios y cubierta reflectiva."
    )
}


class EM110Evaluator:
    """Evaluador de cumplimiento de la Norma EM.110."""

    @staticmethod
    def evaluate(region: str, u_roof: float, u_wall: float, shgc_glass: float = 0.70) -> dict:
        limits = BIOCLIMATIC_ZONES_EM110.get(region, BIOCLIMATIC_ZONES_EM110["Costa"])

        roof_ok = (u_roof <= limits.max_u_roof)
        wall_ok = (u_wall <= limits.max_u_wall)
        glass_ok = (shgc_glass <= limits.max_shgc_glass)

        overall_ok = roof_ok and wall_ok

        recommendations = []
        if not roof_ok:
            recommendations.append(f"El techo actual (U = {u_roof:.2f}) supera el límite de {limits.max_u_roof:.2f} W/m²K. Se recomienda Termotecho, cielo raso con fibra mineral o UPVC con extractor eólico.")
        else:
            recommendations.append("El techo cumple con creces el aislamiento térmico exigido por la Norma EM.110.")

        if not wall_ok:
            recommendations.append(f"Los muros (U = {u_wall:.2f}) superan el límite de {limits.max_u_wall:.2f} W/m²K. Se sugiere incorporar Termomuro o placas con lana de vidrio.")
        else:
            recommendations.append("Los muros perimetrales cumplen la transmitancia térmica máxima de la norma.")

        return {
            "zone": limits.zone_name,
            "overall_compliance": overall_ok,
            "roof_status": {
                "current_u": round(u_roof, 2),
                "limit_u": limits.max_u_roof,
                "compliant": roof_ok
            },
            "wall_status": {
                "current_u": round(u_wall, 2),
                "limit_u": limits.max_u_wall,
                "compliant": wall_ok
            },
            "recommendations": recommendations,
            "natural_vent_required": limits.natural_vent_required
        }
