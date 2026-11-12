# -*- coding: utf-8 -*-
"""
Test de verificación para las nuevas funcionalidades de Ventiladores (Techo vs Pared Alta y Datos de Fabricante)
y Climatización A/C (Capacidad Nominal BTU/h, Auto-dimensionamiento y Diagnóstico de Déficit).
"""
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.ventilation import CeilingComfortFan, AirConditioningSystem

def test_fan_and_ac():
    app = QApplication.instance() or QApplication(sys.argv)
    print("=" * 70)
    print("INICIANDO PRUEBAS DE VENTILADORES Y CAPACIDADES NOMINALES A/C")
    print("=" * 70)

    # 1. Test unitario de modelos físicos en core/ventilation.py
    print("\n[TEST 1] Verificación física de montaje de ventiladores (ASHRAE 55)...")
    fan_techo = CeilingComfortFan(enabled=True, quantity=1, mount_type="techo", air_speed_m_s=1.0)
    fan_mural = CeilingComfortFan(enabled=True, quantity=1, mount_type="pared_alta", air_speed_m_s=1.0)
    fan_pedestal = CeilingComfortFan(enabled=True, quantity=1, mount_type="pedestal", air_speed_m_s=1.0)

    dt_techo = fan_techo.apparent_temperature_reduction_c
    dt_mural = fan_mural.apparent_temperature_reduction_c
    dt_ped = fan_pedestal.apparent_temperature_reduction_c

    print(f"   - Alivio Ventilador Techo (100% efectividad): -{dt_techo:.2f} °C")
    print(f"   - Alivio Ventilador Mural Alta (88% efectividad): -{dt_mural:.2f} °C")
    print(f"   - Alivio Ventilador Pedestal (95% efectividad): -{dt_ped:.2f} °C")

    assert dt_techo > dt_mural, "El ventilador de techo debe tener mayor efectividad sobre ocupantes que el mural a distancia"
    assert dt_ped > dt_mural, "El ventilador pedestal debe tener mayor efectividad local que el mural a distancia"
    print("✓ Modelado físico de tipos de montaje de ventilador verificado con éxito.")

    # 2. Test unitario de Aire Acondicionado y equilibrio térmico
    print("\n[TEST 2] Verificación de A/C con capacidad limitada vs demanda...")
    # Demanda de 10,000 W = 34,121 BTU/h
    heat_load_w = 10000.0
    ac_subdimensionado = AirConditioningSystem(enabled=True, quantity=1, is_auto_capacity=False, nominal_cooling_btu_h=12000.0)
    res_sub = ac_subdimensionado.calculate_cooling_power_required(heat_load_w)

    print(f"   - Demanda requerida: {res_sub['demand_btu_h']:,.0f} BTU/h")
    print(f"   - Capacidad instalada: {res_sub['nominal_btu_h']:,.0f} BTU/h")
    print(f"   - Potencia entregada: {res_sub['cooling_btu_h']:,.0f} BTU/h ({res_sub['thermal_power_w']:,.0f} W)")
    print(f"   - Déficit detectado: {res_sub['deficit_btu_h']:,.0f} BTU/h")
    print(f"   - Suficiencia: {res_sub['is_sufficient']}")

    assert not res_sub['is_sufficient'], "Debe alertar insuficiencia de capacidad"
    assert res_sub['deficit_btu_h'] > 20000, "El déficit debe ser mayor a 20,000 BTU/h"
    assert res_sub['cooling_btu_h'] == 12000.0, "La potencia entregada no puede exceder la capacidad nominal de la máquina"
    print("✓ Restricción física de capacidad frigorífica nominal y cálculo de déficit verificados.")

    # 3. Test integrado en MainWindow
    print("\n[TEST 3] Verificación integrada en MainWindow...")
    win = MainWindow()
    win.show()

    # Comprobar presencia de widgets
    assert hasattr(win, "combo_fan_mount"), "Falta combo_fan_mount en MainWindow"
    assert hasattr(win, "spin_fan_speed_custom"), "Falta spin_fan_speed_custom en MainWindow"
    assert hasattr(win, "spin_fan_power_w"), "Falta spin_fan_power_w en MainWindow"
    assert hasattr(win, "combo_ac_cap"), "Falta combo_ac_cap en MainWindow"
    assert hasattr(win, "spin_ac_nominal_btu"), "Falta spin_ac_nominal_btu en MainWindow"
    assert hasattr(win, "lbl_ac_diag"), "Falta lbl_ac_diag en MainWindow"
    assert hasattr(win, "lbl_fan_relief"), "Falta lbl_fan_relief en MainWindow"
    print("✓ Todos los controles UI de fabricante y montaje están presentes.")

    # Simular cambio a montaje de Pared Alta y velocidad 2.0 m/s
    win.combo_fan_mount.setCurrentIndex(1)  # Pared Alta
    win.spin_fan_speed_custom.setValue(2.0)
    win.spin_fan_power_w.setValue(110.0)
    assert win.fan_units[0]["mount"] == "pared_alta"
    assert win.fan_units[0]["air_speed_m_s"] == 2.0
    print(f"✓ Ventilador configurado: {win.fan_units[0]['name']} en {win.fan_units[0]['mount']} a {win.fan_units[0]['air_speed_m_s']} m/s.")

    # Simular A/C activo con 1 unidad de 12,000 BTU/h para 150 ocupantes
    win.chk_ac.setChecked(True)
    win.spin_floors.setValue(1)
    win.spin_occ_l1.setValue(150)
    win.combo_ac_cap.setCurrentIndex(0)  # 12,000 BTU/h
    win.run_simulation()

    peak_r = max(win.last_results, key=lambda x: x.get("t_int_level_1", 0.0))
    t1_undersized = peak_r["t_int_level_1"]
    deficit = peak_r.get("ac_deficit_btu_1", 0.0)
    is_suff = peak_r.get("ac_is_sufficient_1", True)

    print(f"   - T. Interior con A/C subdimensionado (12k BTU para 150 pers): {t1_undersized:.1f} °C")
    print(f"   - Déficit horario pico: {deficit:,.0f} BTU/h")
    print(f"   - Suficiencia: {is_suff}")
    print(f"   - Texto Tarjeta KPI A/C: {win.card_ac.findChild(win.card_ac.__class__, 'val_lbl') or 'OK'}")

    assert not is_suff, "Para 150 personas, 12,000 BTU/h debe marcar déficit"
    assert t1_undersized > 24.5, "La temperatura no puede llegar mágicamente a 24.0 °C con máquina insuficiente"
    print("✓ Simulación en déficit térmico verificada (la temperatura flota según balance real).")

    # Simular A/C con auto-dimensionado
    win.combo_ac_cap.setCurrentIndex(6)  # Auto-dimensionar
    win.run_simulation()
    peak_r_auto = max(win.last_results, key=lambda x: x.get("t_int_level_1", 0.0))
    t1_auto = peak_r_auto["t_int_level_1"]
    demand_auto = peak_r_auto.get("ac_btu_h_1", 0.0)
    print(f"   - T. Interior con A/C Auto-dimensionado: {t1_auto:.1f} °C (Demanda satisfecha: {demand_auto:,.0f} BTU/h)")
    assert abs(t1_auto - 24.0) < 0.2, "Con auto-dimensionado debe alcanzar la temperatura de setpoint de 24.0 °C"
    print("✓ Modo Auto-dimensionado verificado con éxito.")

    # 4. Verificar Memoria de Cálculo con los nuevos datos
    print("\n[TEST 4] Verificando Memoria de Cálculo enriquecida...")
    md_text = win.calc_memory_widget.current_markdown
    assert "Ventiladores de Confort" in md_text
    assert "Climatización A/C Split" in md_text
    assert "BTU/h" in md_text
    print("✓ Memoria de Cálculo documenta capacidades y montajes con rigor técnico.")

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE VENTILADORES Y A/C COMPLETADAS SATISFACTORIAMENTE!")
    print("=" * 70)

if __name__ == "__main__":
    test_fan_and_ac()
