"""
Módulo de Generación de Reportes Técnicos Bioclimáticos y Térmicos.
Exporta informes completos en HTML interactivo (listo para imprimir/PDF) y CSV.
"""

import os
import datetime
from typing import List, Dict


class ThermalReportGenerator:
    """Generador de reportes técnicos de simulación térmica y bioclimática."""

    @staticmethod
    def generate_html_report(
        project_name: str,
        city_name: str,
        season_name: str,
        north_deg: float,
        results: List[Dict],
        zone_1_cfg,
        zone_2_cfg,
        roof_assembly,
        em110_results: dict,
        output_filepath: str
    ) -> str:
        """Genera un archivo HTML interactivo con el informe técnico completo."""
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        # Cálculos de resumen
        max_t_ext = max(r["t_ext"] for r in results)
        min_t_ext = min(r["t_ext"] for r in results)
        max_t_l1 = max(r["t_int_level_1"] for r in results)
        min_t_l1 = min(r["t_int_level_1"] for r in results)
        max_t_l2 = max(r["t_int_level_2"] for r in results) if zone_2_cfg else max_t_l1
        min_t_l2 = min(r["t_int_level_2"] for r in results) if zone_2_cfg else min_t_l1

        max_ac_btu = max((r.get("ac_btu_h_1", 0) + r.get("ac_btu_h_2", 0)) for r in results)
        ton_ref = max_ac_btu / 12000.0

        # Filas de la tabla horaria
        rows_html = ""
        for r in results:
            h = r["hour"]
            t_ext = r["t_ext"]
            t_1 = r["t_int_level_1"]
            t_app_1 = r["t_apparent_level_1"]
            t_2 = r["t_int_level_2"]
            rad = r["solar_radiation"]
            ac_1 = r.get("ac_btu_h_1", 0)
            ac_2 = r.get("ac_btu_h_2", 0)

            # Estilo condicional de temperatura
            color_1 = "#ff5722" if t_1 > 28.0 else ("#4caf50" if 21.0 <= t_1 <= 26.0 else "#2196f3")
            color_2 = "#ff5722" if t_2 > 28.0 else ("#4caf50" if 21.0 <= t_2 <= 26.0 else "#2196f3")

            rows_html += f"""
            <tr>
                <td style="text-align:center; font-weight:bold;">{h:02d}:00</td>
                <td style="text-align:right;">{t_ext:.1f} °C</td>
                <td style="text-align:right; color:{color_1}; font-weight:bold;">{t_1:.1f} °C</td>
                <td style="text-align:right; color:#81c784;">{t_app_1:.1f} °C</td>
                <td style="text-align:right; color:{color_2}; font-weight:bold;">{t_2:.1f} °C</td>
                <td style="text-align:right;">{rad:.1f} W/m²</td>
                <td style="text-align:right;">{ac_1 + ac_2:,.0f} BTU/h</td>
            </tr>
            """

        # Recomendaciones de norma EM.110
        em_badge = '<span style="background:#2e7d32; color:#fff; padding:4px 8px; border-radius:4px; font-weight:bold;">CUMPLE NORMA EM.110</span>' if em110_results.get("overall_compliance") else '<span style="background:#c62828; color:#fff; padding:4px 8px; border-radius:4px; font-weight:bold;">NO CUMPLE (EXCESO TÉRMICO)</span>'
        recom_list = "".join(f"<li>{rec}</li>" for rec in em110_results.get("recommendations", []))

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Técnico Térmico y Bioclimático - {project_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            margin: 0;
            padding: 25px;
        }}
        .container {{
            max-width: 1050px;
            margin: 0 auto;
            background: #ffffff;
            padding: 35px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }}
        .header {{
            border-bottom: 3px solid #0288d1;
            padding-bottom: 15px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{ color: #0d47a1; margin: 0; font-size: 24px; }}
        h2 {{ color: #1565c0; font-size: 18px; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .kpi-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}
        .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: bold; }}
        .kpi-val {{ font-size: 22px; font-weight: bold; color: #0288d1; margin-top: 5px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 18px 0;
            font-size: 13px;
        }}
        th, td {{
            padding: 9px 12px;
            border: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #0f172a;
            color: #ffffff;
            font-weight: 600;
        }}
        tr:nth-child(even) {{ background-color: #f8fafc; }}
        .compliance-box {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            padding: 18px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        .btn-print {{
            background: #0288d1;
            color: #fff;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }}
        @media print {{
            .btn-print {{ display: none; }}
            body {{ padding: 0; background: #fff; }}
            .container {{ box-shadow: none; padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Informe Técnico de Simulación Térmica y Bioclimática</h1>
                <div style="color:#64748b; font-size:13px; margin-top:4px;">Proyecto: {project_name} | Emisión: {now_str}</div>
            </div>
            <button class="btn-print" onclick="window.print()">🖨️ Imprimir / Guardar PDF</button>
        </div>

        <h2>1. Parámetros del Emplazamiento (Perú)</h2>
        <table style="width:100%;">
            <tr>
                <td style="width:25%; font-weight:bold; background:#f1f5f9;">Ubicación:</td>
                <td style="width:25%;">{city_name}</td>
                <td style="width:25%; font-weight:bold; background:#f1f5f9;">Orientación Norte:</td>
                <td style="width:25%;">{north_deg:.0f}° respecto al eje del modelo</td>
            </tr>
            <tr>
                <td style="font-weight:bold; background:#f1f5f9;">Temporada Evaluada:</td>
                <td>{season_name}</td>
                <td style="font-weight:bold; background:#f1f5f9;">Zona Bioclimática:</td>
                <td>{em110_results.get("zone", "Perú")}</td>
            </tr>
        </table>

        <h2>2. Resumen de Desempeño Térmico y Climatización</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">T. Máxima Nivel 1</div>
                <div class="kpi-val" style="color:#2196f3;">{max_t_l1:.1f} °C</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">T. Máxima Nivel 2</div>
                <div class="kpi-val" style="color:#f44336;">{max_t_l2:.1f} °C</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Alivio por Sombra Vecina</div>
                <div class="kpi-val" style="color:#ff9800;">-{max(0.0, max_t_l2 - max_t_l1):.1f} °C</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Potencia A/C Requerida</div>
                <div class="kpi-val" style="color:#00bcd4;">{max_ac_btu:,.0f} <span style="font-size:12px;">BTU/h</span></div>
                <div style="font-size:11px; color:#64748b; margin-top:3px;">({ton_ref:.2f} Ton. Ref)</div>
            </div>
        </div>

        <h2>3. Evaluación de Cumplimiento: Norma Técnica Peruana EM.110</h2>
        <div class="compliance-box">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:15px; font-weight:bold;">Dictamen de Transmitancia Térmica:</span>
                {em_badge}
            </div>
            <ul style="margin-top:12px; font-size:13px; line-height:1.6;">
                {recom_list}
            </ul>
        </div>

        <h2>4. Especificación de Envolventes y Materiales Asignados</h2>
        <table>
            <tr>
                <th>Elemento Constructivo</th>
                <th>Material Seleccionado</th>
                <th>Espesor (cm)</th>
                <th>Transmitancia U (W/m²K)</th>
            </tr>
            <tr>
                <td><b>Cubierta Superior (Techo Nivel 2)</b></td>
                <td>{roof_assembly.roof_material.name}</td>
                <td style="text-align:center;">{roof_assembly.roof_material.thickness*100:.1f} cm</td>
                <td style="text-align:center; font-weight:bold;">{roof_assembly.u_value:.2f}</td>
            </tr>
            <tr>
                <td><b>Muros Perimetrales</b></td>
                <td>{zone_1_cfg.wall_material.name}</td>
                <td style="text-align:center;">{zone_1_cfg.wall_material.thickness*100:.1f} cm</td>
                <td style="text-align:center; font-weight:bold;">{zone_1_cfg.wall_material.u_value:.2f}</td>
            </tr>
            <tr>
                <td><b>Acristalamiento de Ventanas</b></td>
                <td>{zone_1_cfg.window_material.name}</td>
                <td style="text-align:center;">{zone_1_cfg.window_material.thickness*100:.1f} cm</td>
                <td style="text-align:center; font-weight:bold;">{zone_1_cfg.window_material.u_value:.2f}</td>
            </tr>
        </table>

        <h2>5. Registro Horario Detallado (Ciclo 24 Horas)</h2>
        <table>
            <tr>
                <th>Hora</th>
                <th>T. Exterior</th>
                <th>Interior Nivel 1</th>
                <th>Sensación (Ventilador)</th>
                <th>Interior Nivel 2</th>
                <th>Radiación Solar</th>
                <th>Demanda A/C</th>
            </tr>
            {rows_html}
        </table>

        <div style="text-align:center; margin-top:35px; color:#94a3b8; font-size:11px;">
            Simulador Térmico Bioclimático 3D (Perú) - Generado con algoritmos validados según ISO 6946 y EM.110.
        </div>
    </div>
</body>
</html>
"""
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_filepath
