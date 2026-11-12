# -*- coding: utf-8 -*-
"""
Módulo Generador de la Memoria de Cálculo Completa y Detallada
según la Norma Técnica Peruana EM.110 (RNE - Confort Térmico y Lumínico con Eficiencia Energética)
y estándares internacionales ASHRAE 55 / ISO 6946.
"""

import math
import datetime
from typing import List, Dict, Optional
from core.compliance_em110 import BIOCLIMATIC_ZONES_EM110, BioclimaticLimitEM110


class CalculationMemoryGenerator:
    """Genera la memoria de cálculo explicativa, paso a paso y con todas las fórmulas matemáticas."""

    @staticmethod
    def generate_markdown(
        project_name: str,
        city_climate,
        season_name: str,
        north_deg: float,
        results: List[Dict],
        zone_1,
        zone_2,
        roof_assembly,
        slab_material,
        eolic_units: list,
        exhaust_units: list,
        supply_units: list,
        fan_units: list,
        ac_units: list,
        chk_ac_on: bool = False,
        chk_eolic_on: bool = True,
        chk_exhaust_on: bool = True,
        chk_supply_on: bool = True,
        chk_fan_on: bool = True
    ) -> str:
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        num_floors = 2 if zone_2 is not None else 1

        # 1. Datos Climáticos
        c_name = getattr(city_climate, "name", "Piura")
        c_region = getattr(city_climate, "region", "Costa")
        c_lat = getattr(city_climate, "latitude", -5.20)
        c_lon = getattr(city_climate, "longitude", -80.63)
        c_alt = getattr(city_climate, "altitude_m", 36.0)
        c_rad_peak = getattr(city_climate, "peak_solar_radiation_w_m2", 980.0)
        c_wind_avg = getattr(city_climate, "avg_wind_speed_m_s", 3.8)

        # 2. Resumen de Temperaturas de la Simulación
        if results:
            t_ext_max = max(r["t_ext"] for r in results)
            t_ext_min = min(r["t_ext"] for r in results)
            t_l1_max = max(r["t_int_level_1"] for r in results)
            t_l1_min = min(r["t_int_level_1"] for r in results)
            t_l1_avg = sum(r["t_int_level_1"] for r in results) / len(results)
            t_app1_max = max(r.get("t_apparent_level_1", r["t_int_level_1"]) for r in results)

            if zone_2:
                t_l2_max = max(r["t_int_level_2"] for r in results)
                t_l2_min = min(r["t_int_level_2"] for r in results)
                t_l2_avg = sum(r["t_int_level_2"] for r in results) / len(results)
                t_app2_max = max(r.get("t_apparent_level_2", r["t_int_level_2"]) for r in results)
            else:
                t_l2_max, t_l2_min, t_l2_avg, t_app2_max = t_l1_max, t_l1_min, t_l1_avg, t_app1_max

            ac_btu_max = max((r.get("ac_btu_h_1", 0.0) + r.get("ac_btu_h_2", 0.0)) for r in results)
        else:
            t_ext_max = t_ext_min = t_l1_max = t_l1_min = t_l1_avg = t_app1_max = 25.0
            t_l2_max = t_l2_min = t_l2_avg = t_app2_max = 25.0
            ac_btu_max = 0.0

        # 3. Datos Geométricos
        l = zone_1.length_m
        w = zone_1.width_m
        h = zone_1.height_m
        a_piso = zone_1.floor_area_m2
        v_l1 = zone_1.volume_m3
        v_total = v_l1 * (2 if zone_2 else 1)
        a_muros_net_l1 = zone_1.net_wall_area_m2
        a_vent_l1 = zone_1.window_area_m2
        wwr = (a_vent_l1 / zone_1.gross_wall_area_m2) * 100.0

        # 4. Propiedades de la Envolvente
        u_wall = zone_1.wall_material.u_value
        r_wall = zone_1.wall_material.thermal_resistance
        wall_name = zone_1.wall_material.name
        wall_thick_cm = zone_1.wall_material.thickness * 100.0

        u_roof = roof_assembly.u_value if roof_assembly else 1.5
        r_roof = roof_assembly.total_thermal_resistance if roof_assembly else (1.0 / 1.5)
        roof_name = roof_assembly.description if roof_assembly else "Cubierta Simple"
        roof_alpha = roof_assembly.effective_solar_absorptance if roof_assembly else 0.50

        u_win = zone_1.window_material.u_value
        win_name = zone_1.window_material.name

        u_slab = slab_material.u_value if slab_material else 1.8

        # 5. Límites Normativos EM.110
        lim_em110 = BIOCLIMATIC_ZONES_EM110.get(c_region, BIOCLIMATIC_ZONES_EM110["Costa"])
        cumple_muro = u_wall <= lim_em110.max_u_wall
        cumple_techo = u_roof <= lim_em110.max_u_roof
        cumple_global = cumple_muro and cumple_techo

        # 6. Balance de Cargas Internas
        occ_1 = zone_1.occupants
        occ_2 = zone_2.occupants if zone_2 else 0
        total_people = occ_1 + occ_2
        heat_per_person = zone_1.occupant_heat_w
        q_humana_total = total_people * heat_per_person
        q_humana_sensible = total_people * (heat_per_person * 0.65)
        q_humana_latente = total_people * (heat_per_person * 0.35)
        q_equip_total = zone_1.equipment_w + (zone_2.equipment_w if zone_2 else 0.0)
        q_int_total = q_humana_sensible + q_equip_total
        flow_occ_vent = total_people * 18.0

        # 7. Ventilación Forzada y HVAC Instalado
        ex_active = [u for u in exhaust_units if u.get("enabled", True)] if chk_exhaust_on else []
        sup_active = [u for u in supply_units if u.get("enabled", True)] if chk_supply_on else []
        eolic_active = [u for u in eolic_units if u.get("enabled", True)] if chk_eolic_on else []
        fan_active = [u for u in fan_units if u.get("enabled", True)] if chk_fan_on else []
        ac_active = [u for u in ac_units if u.get("enabled", True)] if chk_ac_on else []

        flow_ex_total = sum(u.get("flow", 1200.0) for u in ex_active)
        flow_sup_total = sum(u.get("flow", 1200.0) for u in sup_active)
        ach_ex = flow_ex_total / max(1.0, v_total)
        ach_sup = flow_sup_total / max(1.0, v_total)

        # 8. Generación del Documento
        md = []
        md.append(f"# MEMORIA DE CÁLCULO TÉRMICA Y BIOCLIMÁTICA")
        md.append(f"### Proyecto: **{project_name}**")
        md.append(f"**Norma de Referencia:** RNE - Norma Técnica EM.110 *'Confort Térmico y Lumínico con Eficiencia Energética'* / ASHRAE 55")
        md.append(f"**Fecha y Hora de Emisión:** {now_str}  \n**Estado:** {'✅ CONFORME CON EM.110' if cumple_global else '⚠️ NO CONFORME (REQUIERE AISLAMIENTO / VENTILACIÓN)'}")
        md.append("\n---\n")

        md.append("## 1. BASES DE CÁLCULO Y LOCALIZACIÓN GEOGRÁFICA")
        md.append("| Parámetro | Valor Evaluado | Unidad / Detalle |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Ciudad de Ubicación** | {c_name} | Región {c_region} |")
        md.append(f"| **Zona Bioclimática EM.110** | {lim_em110.zone_code} - {lim_em110.zone_name} | RNE Perú |")
        md.append(f"| **Coordenadas** | Lat: {c_lat:.4f}°, Lon: {c_lon:.4f}° | Altitud: {c_alt:.0f} m.s.n.m. |")
        md.append(f"| **Estación de Evaluación** | {season_name} (Condición crítica de diseño) | Solsticio / Mes representativo |")
        md.append(f"| **Orientación Norte** | {north_deg:.1f}° respecto al eje frontal | Ángulo azimutal de fachada |")
        md.append(f"| **Radiación Solar Pico** | {c_rad_peak:.1f} W/m² | Radiación global incidente horizontal |")
        md.append(f"| **Velocidad Media Viento** | {c_wind_avg:.1f} m/s | Dirección predominante según región |")
        md.append(f"| **Rango Térmico Exterior** | Mín: {t_ext_min:.1f} °C  |  Máx: {t_ext_max:.1f} °C (ΔT = {t_ext_max - t_ext_min:.1f} °C) |")

        md.append("\n## 2. GEOMETRÍA Y VOLUMETRÍA DE LA EDIFICACIÓN")
        md.append(f"- **Número de Plantas / Niveles:** {num_floors} piso(s)")
        md.append(f"- **Dimensiones en Planta:** Longitud $L = {l:.2f}\\text{{ m}}$, Ancho $W = {w:.2f}\\text{{ m}}$")
        md.append(f"- **Altura de Entrepiso:** $H = {h:.2f}\\text{{ m}}$ por piso (Altura total: ${h * num_floors:.2f}\\text{{ m}}$)")
        md.append(f"- **Área Techada por Planta:** $A_{{\\text{{piso}}}} = L \\times W = {a_piso:.2f}\\text{{ m}}^2$ (Área construida total: ${a_piso * num_floors:.2f}\\text{{ m}}^2$)")
        md.append(f"- **Volumen de Aire Interior Total:** $V_{{\\text{{total}}}} = {v_total:.2f}\\text{{ m}}^3$")
        md.append(f"- **Superficie de Muros Nivel 1:** Área bruta = ${zone_1.gross_wall_area_m2:.2f}\\text{{ m}}^2$, Área acristalada = ${a_vent_l1:.2f}\\text{{ m}}^2$, Área neta = ${a_muros_net_l1:.2f}\\text{{ m}}^2$")
        md.append(f"- **Ratio Ventana/Pared (WWR):** ${wwr:.1f}\\%$")

        # Ratios de Aforo según RNE A.010
        area_per_person = (a_piso * num_floors) / max(1, total_people) if total_people > 0 else 0.0
        vol_per_person = v_total / max(1, total_people) if total_people > 0 else 0.0
        cumple_a010 = area_per_person >= 1.0 if total_people > 0 else True
        md.append(f"\n### Justificación de Aforo y Habitabilidad (RNE Norma A.010):")
        md.append(f"- **Aforo de Diseño Considerado:** {total_people} personas ({occ_1} en Nivel 1" + (f", {occ_2} en Nivel 2" if num_floors == 2 else "") + ")")
        md.append(f"- **Índice de Ocupación por Superficie:** ${area_per_person:.2f}\\text{{ m}}^2\\text{{/persona}}$ (Exigencia RNE A.010 Art. 9: mínimo $1.00\\text{{ m}}^2\\text{{/persona}}$ en salas de reunión / auditorios con butacas fijas: {'✅ CONFORME' if cumple_a010 else '⚠️ DENSIDAD ELEVADA'})")
        md.append(f"- **Índice de Cubicaje Volumétrico:** ${vol_per_person:.2f}\\text{{ m}}^3\\text{{/persona}}$ (Criterio higiénico óptimo de ventilación: $\\ge 3.00\\text{{ m}}^3\\text{{/persona}}$)")

        md.append("\n## 3. PROPIEDADES TERMOFÍSICAS Y EVALUACIÓN NORMATIVA EM.110")
        md.append("La transmitancia térmica ($U$) de cada cerramiento multicapa se calcula según la norma ISO 6946:")
        md.append(r"$$R_{\text{total}} = R_{se} + \sum_{i=1}^{n} \frac{e_i}{\lambda_i} + R_{\text{cámara}} + R_{si} \quad \left[\frac{\text{m}^2\cdot\text{K}}{\text{W}}\right]$$")
        md.append(r"$$U = \frac{1}{R_{\text{total}}} \quad \left[\frac{\text{W}}{\text{m}^2\cdot\text{K}}\right]$$")
        md.append("\n### Matriz de Cumplimiento de Envolventes:")
        md.append("| Elemento Constructivo | Material Especificado | Espesor | $U_{\\text{calculado}}$ | $U_{\\text{máx}}$ EM.110 | Dictamen Normativo |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        md.append(f"| **Muros Exteriores** | {wall_name} | {wall_thick_cm:.1f} cm | **{u_wall:.2f} W/m²K** | {lim_em110.max_u_wall:.2f} W/m²K | {'✅ CUMPLE' if cumple_muro else '❌ EXCEDE LÍMITE'} |")
        md.append(f"| **Techo / Cubierta** | {roof_name} | {roof_assembly.total_thickness*100.0 if roof_assembly else 15.0:.1f} cm | **{u_roof:.2f} W/m²K** | {lim_em110.max_u_roof:.2f} W/m²K | {'✅ CUMPLE' if cumple_techo else '❌ EXCEDE LÍMITE'} |")
        md.append(f"| **Ventanas / Vanos** | {win_name} | {zone_1.window_material.thickness*1000.0:.1f} mm | **{u_win:.2f} W/m²K** | Referencial | {'✅ ADECUADO' if u_win <= 5.8 else '⚠️ REVISAR'} |")
        if num_floors == 2:
            md.append(f"| **Losa de Entrepiso** | Concreto / Losa aligerada | 20.0 cm | **{u_slab:.2f} W/m²K** | -- (Interior) | Acoplamiento térmico |")

        md.append(f"\n> [!NOTE]\n> **Diagnóstico Bioclimático de Envolvente:**  \n> {lim_em110.description}")

        md.append("\n## 4. METODOLOGÍA DEL BALANCE TÉRMICO DINÁMICO (24 HORAS)")
        md.append("El motor calcula de forma acoplada la ecuación diferencial de conservación de la energía en cada piso hora a hora:")
        md.append(r"$$C_{\text{zona}} \frac{dT_{\text{int}}}{dt} = \sum Q_{\text{conducción}} + \sum Q_{\text{solar}} + Q_{\text{internas}} + Q_{\text{ventilación}} - Q_{\text{HVAC}}$$")
        md.append("\n### Desglose de Ecuaciones Componentes:")
        md.append(f"1. **Capacitancia Térmica de la Zona ($C_{{\\text{{zona}}}}$):**")
        md.append(r"   $$C_{\text{zona}} = V_{\text{aire}} \rho_{\text{aire}} c_{p,\text{aire}} + 0.25 A_{\text{muro}} e \rho_{\text{muro}} c_{\text{muro}}$$")
        md.append(f"   - Zona Nivel 1: $C_{{\\text{{zona, 1}}}} = {zone_1.thermal_capacitance_j_k:,.0f}\\text{{ J/K}}$ (aporta alta inercia que amortigua la oscilación diurna).")
        md.append(f"2. **Cargas Internas de Calor ($Q_{{\\text{{internas}}}}$) y Fracción Sensible (ASHRAE Ch. 18):**")
        md.append(f"   - Ocupación total: ${total_people}\\text{{ personas}}$")
        md.append(f"   - Calor metabólico total: ${q_humana_total:,.0f}\\text{{ W}}$ (${heat_per_person:.0f}\\text{{ W/persona}}$)")
        md.append(f"   - **Calor Sensible (Calienta el aire - 65%):** $Q_{{\\text{{sensible}}}} = {q_humana_sensible:,.0f}\\text{{ W}}$")
        md.append(f"   - **Calor Latente (Humedad/Transpiración - 35%):** $Q_{{\\text{{latente}}}} = {q_humana_latente:,.0f}\\text{{ W}}$")
        md.append(f"   - Carga de equipos e iluminación: ${q_equip_total:,.0f}\\text{{ W}}$")
        md.append(f"   - Ganancia térmica sensible neta: $Q_{{\\text{{int, sensible}}}} = {q_int_total:,.0f}\\text{{ W}}$")
        md.append(f"   - Caudal de renovación respiratoria requerido (RNE EM.110 Art. 8 / ASHRAE 62.1): **{flow_occ_vent:,.0f} m³/h** ($18\\text{{ m}}^3\\text{{/h por persona}}$).")
        md.append(f"3. **Temperatura Sol-Aire, Amortiguamiento ($f$) y Desfase Térmico ($\\phi$) en Envolventes Opacas (ISO 13790 / ASHRAE Ch. 18):**")
        md.append(r"   - En muros y techos opacos, el calor solar no penetra directamente al aire interior; calienta la cara exterior generando la Temperatura Sol-Aire:")
        md.append(r"   $$T_{\\text{sol-aire}} = T_{\\text{ext}} + \\frac{\\alpha \\cdot I_{\\text{rad}}}{h_e} - \\Delta R$$")
        md.append(r"   - La masa térmica y el aislamiento atenúan y retardan la onda solar mediante el factor de decremento ($f$) y las horas de desfase ($\\phi$):")
        md.append(r"   $$T_{\\text{eq}}(t) = \\overline{T_{\\text{sol-aire}}} + f \\cdot \\left(T_{\\text{sol-aire}}(t - \\phi) - \\overline{T_{\\text{sol-aire}}}\\right)$$")
        md.append(r"   $$Q_{\\text{cond, envolvente}}(t) = U \\cdot A \\cdot \\left(T_{\\text{eq}}(t) - T_{\\text{int}}(t)\\right)$$")
        md.append(r"   - En muros de ladrillo o concreto ($15 - 20\\text{ cm}$), el desfase térmico es de $\\approx 5.0\\text{ a }6.5\\text{ horas}$ con amortiguamiento $f \\approx 0.25 - 0.35$, evitando que el calor solar del mediodía ingrese al recinto durante el día.")
        md.append(r"   - En cubiertas con aislamiento térmico (ej. Termotecho PUR), la transmitancia reducida ($U \\approx 0.41\\text{ W/m}^2\\text{K}$) bloquea más del $95\\%$ del flujo térmico hacia el interior.")
        md.append(f"4. **Ganancia Solar Directa por Ventanas / Vidrios (Efecto Invernadero):**")
        md.append(r"   - La radiación solar de onda corta ingresa únicamente a través de las superficies vidriadas según su coeficiente SHGC:")
        md.append(r"   $$Q_{\\text{solar, ventanas}} = \\sum I_{\\text{fachada}} \\cdot A_{\\text{vidrio}} \\cdot \\text{SHGC} \\cdot (1 - F_{\\text{sombra}})$$")
        md.append(f"5. **Acoplamiento Pasivo con el Terreno / Suelo ($T_{{\\text{{suelo}}}}$):**")
        md.append(r"   - El subsuelo profundo permanece fresco todo el año ($18\\text{ °C a }21\\text{ °C}$), drenando calor continuamente de forma natural:")
        md.append(r"   $$Q_{\\text{suelo}} = 1.2 \\cdot A_{\\text{piso}} \\cdot (T_{\\text{suelo}} - T_{\\text{int}})$$")
        md.append(f"6. **Ventilación e Infiltración de Aire ($Q_{{\\text{{vent}}}}$) y Balance Convectivo:**")
        md.append(r"   $$\dot{m} = \frac{Q_{\text{caudal}}}{3600} \cdot \rho_{\text{aire}} \quad [\text{kg/s}]$$")
        md.append(r"   $$Q_{\text{vent}} = \dot{m} \cdot c_{p,\text{aire}} \cdot (T_{\text{inyección}} - T_{\text{int}})$$")
        md.append(r"   - Capacidad de remoción de calor del caudal de aire: $C_{\text{vent}} = \dot{m} \cdot c_p$. Cuando la toma de aire proviene de patios sombreados o zonas verdes, el aire entra entre $-2.5\text{ °C y }-3.5\text{ °C}$ más fresco que el aire general de la calle.")

        md.append("\n## 5. SISTEMAS DE MITIGACIÓN Y VENTILACIÓN INSTALADOS")
        md.append("| Sistema / Tecnología | Unidades Activas | Capacidad / Parámetro Operativo | Efecto Bioclimático en el Proyecto |")
        md.append("| :--- | :---: | :--- | :--- |")
        md.append(f"| **Extractores Eólicos en Techo** | {len(eolic_active)} | Diámetro 24\" (Caudal inducido por viento) | Evacúa calor atrapado bajo la cubierta; factor alivio = 40% a 70% |")
        md.append(f"| **Extracción Mecánica Forzada** | {len(ex_active)} | Caudal total: **{flow_ex_total:,.0f} m³/h** ({ach_ex:.1f} ACH) | Despresuriza y evacúa aire caliente acumulado hacia el exterior |")
        md.append(f"| **Inyección de Aire Fresco** | {len(sup_active)} | Caudal total: **{flow_sup_total:,.0f} m³/h** ({ach_sup:.1f} ACH) | Renueva aire oxigenado e induce ventilación forzada |")
        fan_details = []
        for fu in fan_active:
            m_type = fu.get("mount", "techo")
            m_lbl = "Techo (Descendente)" if m_type == "techo" else ("Pared Alta (Longitudinal)" if m_type == "pared_alta" else "Pedestal (Horizontal)")
            v_val = fu.get("air_speed_m_s", 1.0)
            p_val = fu.get("power_w", 75.0)
            fan_details.append(f"{fu.get('name', 'Vent')} ({m_lbl}, {v_val:.1f} m/s, {p_val:.0f} W)")
        fan_param_str = "; ".join(fan_details) if fan_details else "Sensación de brisa: 0.8 a 1.2 m/s"
        md.append(f"| **Ventiladores de Confort** | {len(fan_active)} | {fan_param_str} | **Alivio de confort térmico ASHRAE 55: -{max(0.0, t_l1_max - t_app1_max):.1f} °C** |")

        tot_nominal_btu = sum(u.get("nominal_btu_h", 24000.0) for u in ac_active)
        is_auto_ac = any(u.get("is_auto", False) for u in ac_active)
        max_deficit = max((r.get("ac_deficit_btu_1", 0.0) + r.get("ac_deficit_btu_2", 0.0) for r in results), default=0.0)
        if not ac_active:
            ac_desc = "Inactivo (Simulación en modo pasivo)"
            ac_effect = "Sin climatización artificial activa"
        elif is_auto_ac:
            ac_desc = f"Auto-dimensionado ideal | Demanda pico: **{ac_btu_max:,.0f} BTU/h** ({ac_btu_max/12000.0:.2f} TR)"
            ac_effect = "Absorbe el 100% de la carga sensible manteniendo el setpoint"
        elif max_deficit > 500.0:
            ac_desc = f"Cap. Instalada: **{tot_nominal_btu:,.0f} BTU/h** ({tot_nominal_btu/12000.0:.2f} TR) vs Requerida: **{ac_btu_max:,.0f} BTU/h**"
            ac_effect = f"⚠️ **Déficit de -{max_deficit:,.0f} BTU/h** en hora pico (el recinto no alcanza el setpoint)"
        else:
            ac_desc = f"Cap. Instalada: **{tot_nominal_btu:,.0f} BTU/h** ({tot_nominal_btu/12000.0:.2f} TR) | Demanda pico: **{ac_btu_max:,.0f} BTU/h**"
            mod_pct = (ac_btu_max / max(1.0, tot_nominal_btu)) * 100.0
            ac_effect = f"✓ **Capacidad suficiente**. Modulación Inverter: {mod_pct:.0f}% en hora pico"
        md.append(f"| **Climatización A/C Split** | {len(ac_active)} | {ac_desc} | {ac_effect} |")

        md.append("\n## 6. RESULTADOS DEL COMPORTAMIENTO TÉRMICO HORARIO Y CONFORT MEDIO PREDICHO (24 HORAS)")
        md.append("| Hora | T. Ext (°C) | T. Nivel 1 (°C) | Sensación Confort | CMP (PMV) | PPD (%) | T. Nivel 2 (°C) | Rad. Solar (W/m²) | Potencia A/C (BTU/h) |")
        md.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for r in results:
            h_str = f"{r['hour']:02d}:00"
            t_ext = r["t_ext"]
            t1 = r["t_int_level_1"]
            t1_app = r.get("t_apparent_level_1", t1)
            cmp_val = r.get("cmp_level_1", 0.0)
            ppd_val = r.get("ppd_level_1", 5.0)
            t2 = r.get("t_int_level_2", t1)
            rad = r.get("solar_radiation", 0.0)
            ac = r.get("ac_btu_h_1", 0.0) + r.get("ac_btu_h_2", 0.0)
            md.append(f"| {h_str} | {t_ext:.1f} | {t1:.1f} | **{t1_app:.1f}** | **{cmp_val:+.2f}** | {ppd_val:.0f}% | {t2:.1f} | {rad:.0f} | {ac:,.0f} |")

        md.append("\n## 7. CONCLUSIONES Y RECOMENDACIONES TÉCNICAS")
        md.append(f"1. **Temperatura Máxima Interior en Nivel 1:** Alcanza **{t_l1_max:.1f} °C** a las horas de mayor insolación (confort percibido con ventilación activa: **{t_app1_max:.1f} °C**).")
        if num_floors == 2:
            md.append(f"2. **Comportamiento en Nivel 2:** Registra **{t_l2_max:.1f} °C** debido al contacto directo con la cubierta superior. La diferencia entre Nivel 1 y Nivel 2 es de **{abs(t_l2_max - t_l1_max):.1f} °C**.")
        avg_cmp = sum(r.get("cmp_level_1", 0.0) for r in results) / len(results) if results else 0.0
        avg_ppd = sum(r.get("ppd_level_1", 5.0) for r in results) / len(results) if results else 5.0
        md.append(f"3. **Cumplimiento EM.110:** {'La edificación satisface los parámetros máximos de transmitancia U exigidos por el RNE para esta zona bioclimática.' if cumple_global else 'Se recomienda incorporar cielo raso suspendido o panel con núcleo aislante en techos para reducir la transmitancia U al valor normativo.'}")
        md.append(f"4. **Índice de Confort Medio Predicho (CMP / PMV - ISO 7730 / ASHRAE 55):** El índice CMP promedio evaluado es **{avg_cmp:+.2f}** con un PPD de **{avg_ppd:.1f}%**. " +
                  ("El recinto cumple con la franja de confort admisible de la Norma EM.110 (-0.5 a +0.5, Categoría B)." if abs(avg_cmp) <= 0.5 else "El recinto presenta ligera sobrecarga térmica en horas de máxima ocupación; se recomienda ventilación forzada o climatización evaporativa/split."))
        if ac_active:
            if is_auto_ac:
                md.append(f"5. **Capacidad Frigorífica A/C Requerida (Auto-dimensionado):** Para mantener la temperatura interior a 24.0 °C, se requiere una potencia frigorífica de diseño de **{ac_btu_max:,.0f} BTU/h** ({ac_btu_max/12000.0:.2f} TR), con una potencia eléctrica consumida de **{ac_btu_max * 0.000293071 / 3.2:.2f} kW**.")
            elif max_deficit > 500.0:
                md.append(f"5. **Diagnóstico de Capacidad Frigorífica Instalada vs Requerida:** La potencia instalada de **{tot_nominal_btu:,.0f} BTU/h** ({tot_nominal_btu/12000.0:.2f} TR) resulta **insuficiente** para absorber la carga térmica extrema ({total_people} personas + radiación solar = **{ac_btu_max:,.0f} BTU/h** requeridos). Se genera un **déficit frigorífico de {max_deficit:,.0f} BTU/h**, ocasionando que la temperatura interior alcance {t_l1_max:.1f} °C en hora pico en vez de los 24.0 °C deseados. **Recomendación:** Aumentar la capacidad de los equipos a mínimo {int(math.ceil(ac_btu_max / 12000.0))} TR.")
            else:
                mod_peak = (ac_btu_max / max(1.0, tot_nominal_btu)) * 100.0
                md.append(f"5. **Diagnóstico de Capacidad Frigorífica Instalada:** La potencia instalada de **{tot_nominal_btu:,.0f} BTU/h** ({tot_nominal_btu/12000.0:.2f} TR) es **adecuada y suficiente** para vencer la ganancia térmica horaria máxima (**{ac_btu_max:,.0f} BTU/h**), operando al {mod_peak:.0f}% de su capacidad nominal máxima.")

        return "\n".join(md)

    @staticmethod
    def generate_html(md_text: str) -> str:
        """Convierte la memoria en HTML enriquecido con tema oscuro de alta legibilidad."""
        lines = md_text.splitlines()
        html_lines = []
        in_table = False

        html_lines.append("""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
    body {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        background-color: #15151e;
        color: #d1d5db;
        line-height: 1.6;
        padding: 24px;
        margin: 0;
    }
    h1 { color: #00e5ff; font-size: 22px; border-bottom: 2px solid #0288d1; padding-bottom: 8px; margin-top: 0; }
    h2 { color: #81d4fa; font-size: 16px; border-bottom: 1px solid #374151; padding-bottom: 5px; margin-top: 24px; }
    h3 { color: #ffffff; font-size: 14px; margin-top: 16px; }
    p, li { font-size: 13px; color: #e5e7eb; }
    strong { color: #ffffff; }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 14px 0;
        font-size: 12px;
        background-color: #1e1e2c;
        border-radius: 6px;
        overflow: hidden;
    }
    th, td {
        padding: 8px 12px;
        border: 1px solid #374151;
        text-align: left;
    }
    th {
        background-color: #27273a;
        color: #00e5ff;
        font-weight: bold;
    }
    tr:nth-child(even) { background-color: #171724; }
    tr:hover { background-color: #252538; }
    blockquote {
        background-color: #1e293b;
        border-left: 4px solid #00e5ff;
        padding: 10px 14px;
        margin: 12px 0;
        border-radius: 4px;
        color: #94a3b8;
    }
    hr { border: none; border-top: 1px solid #374151; margin: 20px 0; }
    .badge-ok { background-color: #1b5e20; color: #a5d6a7; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .badge-err { background-color: #7f0000; color: #ffcdd2; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
</style>
</head>
<body>
""")

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_table:
                    html_lines.append("</table>")
                    in_table = False
                html_lines.append("<br>")
                continue

            if line_str.startswith("# "):
                if in_table: html_lines.append("</table>"); in_table = False
                html_lines.append(f"<h1>{line_str[2:]}</h1>")
            elif line_str.startswith("## "):
                if in_table: html_lines.append("</table>"); in_table = False
                html_lines.append(f"<h2>{line_str[3:]}</h2>")
            elif line_str.startswith("### "):
                if in_table: html_lines.append("</table>"); in_table = False
                html_lines.append(f"<h3>{line_str[4:]}</h3>")
            elif line_str.startswith("|"):
                parts = [p.strip() for p in line_str.split("|")[1:-1]]
                if all(set(p).issubset({"-", ":", " "}) for p in parts):
                    continue  # Separator row
                if not in_table:
                    html_lines.append("<table>")
                    in_table = True
                    # First row is header
                    th_cells = "".join(f"<th>{CalculationMemoryGenerator._fmt_inline(p)}</th>" for p in parts)
                    html_lines.append(f"<tr>{th_cells}</tr>")
                else:
                    td_cells = "".join(f"<td>{CalculationMemoryGenerator._fmt_inline(p)}</td>" for p in parts)
                    html_lines.append(f"<tr>{td_cells}</tr>")
            else:
                if in_table:
                    html_lines.append("</table>")
                    in_table = False
                if line_str.startswith("- "):
                    html_lines.append(f"<li>{CalculationMemoryGenerator._fmt_inline(line_str[2:])}</li>")
                elif line_str.startswith("> "):
                    html_lines.append(f"<blockquote>{CalculationMemoryGenerator._fmt_inline(line_str[2:])}</blockquote>")
                elif line_str.startswith("$$") and line_str.endswith("$$"):
                    html_lines.append(f"<div style='text-align:center; font-family: monospace; background:#1e1e2c; padding:8px; border-radius:4px; margin:8px 0; color:#81d4fa;'>{line_str[2:-2]}</div>")
                elif line_str == "---":
                    html_lines.append("<hr>")
                else:
                    html_lines.append(f"<p>{CalculationMemoryGenerator._fmt_inline(line_str)}</p>")

        if in_table:
            html_lines.append("</table>")

        html_lines.append("</body></html>")
        return "\n".join(html_lines)

    @staticmethod
    def _fmt_inline(txt: str) -> str:
        t = txt
        # Badges
        t = t.replace("✅ CUMPLE", '<span class="badge-ok">✅ CUMPLE</span>')
        t = t.replace("✅ CONFORME CON EM.110", '<span class="badge-ok">✅ CONFORME CON EM.110</span>')
        t = t.replace("❌ EXCEDE LÍMITE", '<span class="badge-err">❌ EXCEDE LÍMITE</span>')
        t = t.replace("⚠️ NO CONFORME", '<span class="badge-err">⚠️ NO CONFORME</span>')
        # Bold
        while "**" in t:
            p1 = t.find("**")
            p2 = t.find("**", p1 + 2)
            if p2 == -1: break
            t = t[:p1] + "<strong>" + t[p1+2:p2] + "</strong>" + t[p2+2:]
        # Math dollars
        while "$" in t:
            p1 = t.find("$")
            p2 = t.find("$", p1 + 1)
            if p2 == -1: break
            math_code = t[p1+1:p2].replace("\\text{", "").replace("}", "")
            t = t[:p1] + f"<code style='color:#00e5ff; font-weight:bold;'>{math_code}</code>" + t[p2+1:]
        return t
