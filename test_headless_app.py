# -*- coding: utf-8 -*-
"""
Script de Auditoría y Verificación Headless Completa de la Aplicación.
Verifica que no existan errores de cálculo, fallos de renderizado o excepciones no controladas.
"""

import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Configurar Qt en modo offscreen para ejecución sin pantalla / CI
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.calculation_memory import CalculationMemoryGenerator
from core.compliance_em110 import BIOCLIMATIC_ZONES_EM110


def run_full_audit():
    print("=" * 70)
    print("INICIANDO AUDITORÍA INTEGRAL DE LA APLICACIÓN TÉRMICA BIOCLIMÁTICA")
    print("=" * 70)

    app = QApplication(sys.argv)

    print("\n[TEST 1] Instanciando MainWindow y cargando estado inicial...")
    win = MainWindow()
    print("✓ MainWindow inicializada correctamente.")

    # 1. Verificar simulación inicial
    print("\n[TEST 2] Verificando simulación térmica inicial (24h)...")
    win.run_simulation()
    assert win.last_results is not None, "Error: last_results es None"
    assert len(win.last_results) == 24, f"Error: esperados 24 pasos horarios, obtenidos {len(win.last_results)}"

    max_t1 = max(r["t_int_level_1"] for r in win.last_results)
    min_t1 = min(r["t_int_level_1"] for r in win.last_results)
    max_t2 = max(r["t_int_level_2"] for r in win.last_results)
    min_t2 = min(r["t_int_level_2"] for r in win.last_results)

    print(f"✓ Simulación 2 niveles completada:")
    print(f"   - Nivel 1: T. Mín = {min_t1:.1f} °C, T. Máx = {max_t1:.1f} °C")
    print(f"   - Nivel 2: T. Mín = {min_t2:.1f} °C, T. Máx = {max_t2:.1f} °C")
    assert 10.0 <= min_t1 <= max_t1 <= 55.0, f"Temperaturas fuera de rango físico razonable: {min_t1} - {max_t1}"

    # 2. Verificar pestaña de Memoria de Cálculo
    print("\n[TEST 3] Verificando pestaña y generador de Memoria de Cálculo...")
    assert hasattr(win, "calc_memory_widget"), "MainWindow no tiene calc_memory_widget"
    md_content = win.calc_memory_widget.current_markdown
    html_content = win.calc_memory_widget.current_html
    assert len(md_content) > 500, f"Markdown de memoria de cálculo muy corto ({len(md_content)} chars)"
    assert len(html_content) > 1000, f"HTML de memoria de cálculo muy corto ({len(html_content)} chars)"
    assert "MEMORIA DE CÁLCULO TÉRMICA Y BIOCLIMÁTICA" in md_content
    assert "EM.110" in md_content
    assert "ISO 6946" in md_content
    print("✓ Memoria de Cálculo generada y renderizada con éxito (Markdown y HTML listos).")

    # 3. Probar cambio a 1 Nivel (Modo Planta Única)
    print("\n[TEST 4] Verificando modo de 1 solo piso (Planta Única)...")
    win.spin_floors.setValue(1)
    win.run_simulation()
    assert len(win.last_results) == 24
    max_t1_single = max(r["t_int_level_1"] for r in win.last_results)
    print(f"✓ Modo 1 nivel ejecutado con éxito: T. Máx Nivel 1 = {max_t1_single:.1f} °C")

    # Restaurar a 2 niveles
    win.spin_floors.setValue(2)
    win.run_simulation()

    # 4. Probar manipulación en pestaña Planta (FloorPlanWidget)
    print("\n[TEST 5] Verificando pestaña de Planta (Corte 2D y arrastre de equipos)...")
    fp = win.floor_plan_widget
    # Simular cambios de altura
    for z in [0.1, 1.1, 1.7, 2.3, 3.5, 4.6, 6.2]:
        fp.set_height(z)
        fp.render_plan()
    print("✓ Cambios de altura en planta ejecutados con 0 errores.")

    # Simular arrastre y snap magnético de equipos en planta
    fp.combo_move_tool.setCurrentIndex(1)  # A/C Split
    fp._handle_equipment_drag(4.0, 0.2, is_final=True)
    fp.combo_move_tool.setCurrentIndex(2)  # Extractor
    fp._handle_equipment_drag(4.0, 4.8, is_final=True)
    fp.combo_move_tool.setCurrentIndex(3)  # Inyector
    fp._handle_equipment_drag(7.5, 2.5, is_final=True)
    fp.combo_move_tool.setCurrentIndex(4)  # Ventilador de confort
    fp._handle_equipment_drag(4.0, 2.5, is_final=True)
    fp.combo_move_tool.setCurrentIndex(0)  # Navegar
    fp.render_plan()
    print("✓ Movimiento magnético de equipos en planta verificado.")

    # 5. Probar Climatización A/C Activa y cálculo de frigorías
    print("\n[TEST 6] Verificando cálculo de Potencia Frigorífica A/C Split...")
    win.chk_ac.setChecked(True)
    win.spin_ac_setpoint.setValue(24.0)
    win.run_simulation()
    max_ac_btu = max(r["ac_btu_h_1"] + r["ac_btu_h_2"] for r in win.last_results)
    print(f"✓ Potencia frigorífica A/C calculada: {max_ac_btu:,.0f} BTU/h ({max_ac_btu/12000.0:.2f} TR)")
    assert max_ac_btu > 0.0, "La potencia A/C debería ser mayor a 0 cuando está encendido en clima cálido"

    # 6. Probar diversas ciudades y zonas bioclimáticas del Perú
    print("\n[TEST 7] Evaluando ciudades de Costa, Sierra y Selva...")
    for city_name in ["Piura (Costa Norte - Cálido Extremo)", "Cusco (Sierra Andina)", "Iquitos (Selva Tropical Húmeda)"]:
        win.combo_city.setCurrentText(city_name)
        win.run_simulation()
        t1_max = max(r["t_int_level_1"] for r in win.last_results)
        print(f"   - {city_name[:25]}: T. Máx Nivel 1 = {t1_max:.1f} °C")

    # 7. Probar importación de modelo SketchUp JSON si existe
    print("\n[TEST 8] Verificando compatibilidad con modelos SketchUp...")
    test_json = "modelo_bioclimatico.json"
    if os.path.exists(test_json):
        win.load_model_file(test_json)
        win.run_simulation()
        print(f"✓ Modelo {test_json} importado y simulado con éxito.")

    print("\n" + "=" * 70)
    print("¡AUDITORÍA COMPLETADA CON ÉXITO! 0 ERRORES ENCONTRADOS.")
    print("=" * 70)


if __name__ == "__main__":
    run_full_audit()
