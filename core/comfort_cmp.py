# -*- coding: utf-8 -*-
"""
Módulo de Cálculo del Confort Medio Predicho (CMP / PMV) y Porcentaje de Personas Descontentas (PPD).
Basado en el modelo biofísico de Fanger según las normas internacionales ISO 7730 y ASHRAE 55,
y en cumplimiento de la Norma Técnica Peruana EM.110 ("Confort Térmico y Lumínico con Eficiencia Energética").
"""

import math
from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class CMPResult:
    """Resultado del índice de Confort Medio Predicho (CMP / PMV)."""
    cmp_value: float          # Escala de -3 (Muy frío) a +3 (Muy caluroso), 0 = Confort óptimo
    ppd_percent: float        # Porcentaje de personas insatisfechas (5% a 100%)
    sensation_text: str       # Descripción en español ('Confortable', 'Ligeramente caluroso', etc.)
    compliance_em110: bool    # Conforme con límites de confort EM.110 / ISO 7730 Cat B (-0.5 <= CMP <= +0.5)
    t_operative_c: float      # Temperatura operativa (°C)


class ComfortCMPCalculator:
    """Calculador de Confort Térmico según el modelo de Fanger (ISO 7730 / ASHRAE 55)."""

    @staticmethod
    def calculate_saturated_vapor_pressure_pa(temp_c: float) -> float:
        """Calcula la presión de saturación de vapor de agua en Pascales (Ecuación de Antoine / Magnus)."""
        return 1000.0 * 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))

    @classmethod
    def calculate_cmp_ppd(
        cls,
        ta: float,                    # Temperatura del aire interior (°C)
        tr: float,                    # Temperatura radiante media de muros y techo (°C)
        vel: float = 0.20,            # Velocidad del aire interior (m/s)
        rh: float = 55.0,             # Humedad relativa interior (%)
        met: float = 1.0,             # Tasa metabólica (1.0 = sentado/auditorio, 1.2 = oficina ligera)
        clo: float = 0.50             # Aislamiento de vestimenta (0.5 = verano/ligero, 1.0 = invierno)
    ) -> CMPResult:
        """
        Calcula el Confort Medio Predicho (CMP / PMV) y PPD.
        """
        # Presión parcial de vapor en Pa
        p_sat = cls.calculate_saturated_vapor_pressure_pa(ta)
        pa = (rh / 100.0) * p_sat

        # Parámetros del balance térmico humano
        m = met * 58.15  # W/m² (tasa metabólica)
        w = 0.0          # Trabajo mecánico útil externo (cero para actividades cotidianas)
        mw = m - w

        # Resistencia térmica de la ropa
        icl = clo * 0.155  # m²·K/W
        fcl = 1.0 + 0.2 * clo if clo <= 0.5 else 1.05 + 0.1 * clo

        # Temperatura de la superficie del vestido (Tcl) por iteración física directa (ISO 7730)
        tcl = ta
        hc = 12.1 * math.sqrt(max(0.05, vel))
        rad = 0.0
        conv = 0.0
        for _ in range(100):
            hcf = 12.1 * math.sqrt(max(0.05, vel))
            hcn = 2.38 * (abs(tcl - ta) ** 0.25)
            hc = max(hcf, hcn)
            rad = 3.96 * 1e-8 * fcl * (((tcl + 273.15) ** 4) - ((tr + 273.15) ** 4))
            conv = fcl * hc * (tcl - ta)
            tcl_new = 35.7 - 0.028 * mw - icl * (rad + conv)
            if abs(tcl_new - tcl) < 0.0001:
                tcl = tcl_new
                break
            tcl = 0.7 * tcl + 0.3 * tcl_new

        # 1. Pérdidas de calor corporales hacia el ambiente (W/m²)
        # Difusión de vapor a través de la piel
        hl1 = 3.05 * 0.001 * (5733.0 - 6.99 * mw - pa)
        # Sudoración reguladora
        hl2 = 0.42 * (mw - 58.15) if mw > 58.15 else 0.0
        # Calor latente respiratorio
        hl3 = 1.7 * 0.00001 * m * (5867.0 - pa)
        # Calor sensible respiratorio
        hl4 = 0.0014 * m * (34.0 - ta)
        # Radiación hacia cerramientos
        hl5 = rad
        # Convección hacia el aire
        hl6 = conv

        # Carga térmica total sobre el cuerpo humano
        heat_load = mw - (hl1 + hl2 + hl3 + hl4 + hl5 + hl6)

        # Factor de sensibilidad térmica corporal
        ts = 0.3032 * math.exp(-0.036 * m) + 0.028
        cmp_raw = ts * heat_load
        cmp_val = max(-3.0, min(3.0, cmp_raw))

        # 2. Porcentaje de Personas Descontentas (PPD) según Fanger
        ppd = 100.0 - 95.0 * math.exp(-0.03353 * (cmp_val ** 4) - 0.2179 * (cmp_val ** 2))
        ppd = max(5.0, min(100.0, ppd))

        # 3. Temperatura operativa combinada (aire + radiante)
        t_oper = 0.5 * ta + 0.5 * tr

        # 4. Clasificación bioclimática cualitativa
        if cmp_val <= -2.5:
            sens = "Muy Frío (Inconfort Severo)"
        elif -2.5 < cmp_val <= -1.5:
            sens = "Frío"
        elif -1.5 < cmp_val <= -0.5:
            sens = "Ligeramente Fresco"
        elif -0.5 < cmp_val <= 0.5:
            sens = "Confort Térmico Óptimo (Neutro)"
        elif 0.5 < cmp_val <= 1.5:
            sens = "Ligeramente Caluroso"
        elif 1.5 < cmp_val <= 2.5:
            sens = "Caluroso"
        else:
            sens = "Muy Caluroso (Inconfort Severo)"

        # Cumplimiento según Categoría B de ISO 7730 / RNE EM.110 (-0.5 <= CMP <= +0.5, PPD <= 10%)
        compliance = (-0.5 <= cmp_val <= 0.5)

        return CMPResult(
            cmp_value=round(cmp_val, 2),
            ppd_percent=round(ppd, 1),
            sensation_text=sens,
            compliance_em110=compliance,
            t_operative_c=round(t_oper, 1)
        )
