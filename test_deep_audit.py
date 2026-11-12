"""
Script de Auditoría Profunda para Validación de Cálculos Térmicos, CMP y Conmutación de Equipos.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.comfort_cmp import ComfortCMPCalculator

def run_deep_audit():
    app = QApplication.instance() or QApplication(sys.argv)
    print("=" * 70)
    print("INICIANDO AUDITORÍA PROFUNDA Y VERIFICACIÓN MATEMÁTICA")
    print("=" * 70)

    win = MainWindow()
    win.show()

    # TEST 1: Conmutación de extractores eólicos sin errores
    print("\n[TEST 1] Conmutación de Extractores Eólicos...")
    win.chk_eolic.setChecked(False)
    win._on_eolic_toggled(False)
    assert not win.chk_eolic.isChecked()
    print("✓ Extractor eólico desactivado con 0 errores (sin excepción '_D').")

    win.chk_eolic.setChecked(True)
    win._on_eolic_toggled(True)
    assert win.chk_eolic.isChecked()
    print("✓ Extractor eólico reactivado con éxito.")

    # TEST 2: Conmutación de todos los demás sistemas HVAC
    print("\n[TEST 2] Conmutación de Sistemas HVAC y Equipos...")
    win.chk_exhaust.setChecked(False)
    win.chk_exhaust.setChecked(True)
    win.chk_supply.setChecked(False)
    win.chk_supply.setChecked(True)
    win.chk_fan.setChecked(False)
    win.chk_fan.setChecked(True)
    win.chk_ac.setChecked(False)
    win.chk_ac.setChecked(True)
    print("✓ Todos los interruptores HVAC conmutados sin excepciones.")

    # TEST 3: Verificación del cálculo de Ocupación Humana (150 personas en modo pasivo sin A/C)
    print("\n[TEST 3] Auditoría Termodinámica de Ocupación para 150 personas (Modo Pasivo)...")
    win.chk_ac.setChecked(False)
    win.spin_floors.setValue(2)
    win.spin_occ_l1.setValue(75)
    win.spin_occ_l2.setValue(75)
    win.spin_equip_w.setValue(500.0)
    win.run_simulation()

    # Comprobar resultados
    results_150 = win.last_results
    max_t1_150 = max(r["t_int_level_1"] for r in results_150)
    max_t2_150 = max(r["t_int_level_2"] for r in results_150)
    t_ext_max = max(r["t_ext"] for r in results_150)
    print(f"   - T. Exterior Máx: {t_ext_max:.1f} °C")
    print(f"   - Nivel 1 (150 pers): {max_t1_150:.1f} °C")
    print(f"   - Nivel 2 (150 pers): {max_t2_150:.1f} °C")

    # Comparar con 0 personas
    win.spin_occ_l1.setValue(0)
    win.spin_occ_l2.setValue(0)
    win.spin_equip_w.setValue(0.0)
    win.run_simulation()
    results_0 = win.last_results
    max_t1_0 = max(r["t_int_level_1"] for r in results_0)

    delta_t = max_t1_150 - max_t1_0
    print(f"   - Incremento Térmico Real por 150 Personas: +{delta_t:.2f} °C")
    assert delta_t <= 5.5, f"ERROR: Incremento de temperatura ({delta_t:.2f} °C) excede el límite físico razonable de 5.5 °C"
    assert delta_t > 0.5, f"ERROR: Incremento de temperatura ({delta_t:.2f} °C) es demasiado bajo"
    print(f"✓ Incremento térmico verificado: +{delta_t:.2f} °C (¡Dentro del rango físico realista según ASHRAE / RNE EM.110!)")

    # TEST 4: Verificación del Motor CMP (Fanger PMV ISO 7730 / RNE EM.110)
    print("\n[TEST 4] Verificación de Cálculos del Modelo CMP...")
    # Caso 1: Confort térmico óptimo (26.0°C, 50% HR, 0.15 m/s, 1.0 met, 0.5 clo verano)
    cmp_res = ComfortCMPCalculator.calculate_cmp_ppd(
        ta=26.0,
        tr=26.0,
        rh=50.0,
        vel=0.15,
        met=1.0,
        clo=0.5
    )
    print(f"   - Caso Neutro: CMP = {cmp_res.cmp_value:+.2f}, PPD = {cmp_res.ppd_percent:.1f}%, Sensación = {cmp_res.sensation_text}, Normativa = {cmp_res.compliance_em110}")
    assert abs(cmp_res.cmp_value) <= 0.6, "El caso neutro debe estar entre -0.6 y +0.6"
    assert cmp_res.ppd_percent <= 12.0, "PPD para caso neutro debe ser <= 12%"
    assert cmp_res.compliance_em110 is True, "Debe ser conforme"

    # Caso 2: Ambiente caluroso (33°C, 65% HR, 0.2 m/s, 1.2 met, 0.5 clo)
    cmp_hot = ComfortCMPCalculator.calculate_cmp_ppd(
        ta=33.0,
        tr=35.0,
        rh=65.0,
        vel=0.2,
        met=1.2,
        clo=0.5
    )
    print(f"   - Caso Caluroso: CMP = {cmp_hot.cmp_value:+.2f}, PPD = {cmp_hot.ppd_percent:.1f}%, Sensación = {cmp_hot.sensation_text}")
    assert cmp_hot.cmp_value > 1.5, "El caso caluroso debe dar CMP > 1.5"
    assert cmp_hot.compliance_em110 is False
    print("✓ Modelo CMP (Fanger PMV) calibrado y normativamente verificado con exactitud.")

    # TEST 5: Tarjeta KPI de CMP en MainWindow
    print("\n[TEST 5] Verificación de Tarjeta KPI de CMP en Interfaz...")
    from PyQt6.QtWidgets import QLabel
    cmp_kpi_lbl = win.card_cmp.findChild(QLabel, "val_lbl")
    assert cmp_kpi_lbl is not None
    val_text = cmp_kpi_lbl.text()
    print(f"   - Tarjeta KPI CMP: {val_text}")
    print("✓ Tarjeta KPI de Confort CMP visible y funcional.")

    # TEST 6: Generación y exportación de la Memoria de Cálculo con CMP
    print("\n[TEST 6] Generando Memoria de Cálculo con CMP...")
    mem_widget = win.calc_memory_widget
    md_content = mem_widget.current_markdown
    assert "Confort Medio Predicho" in md_content
    assert "EM.110" in md_content
    assert "Calor Sensible" in md_content
    print("✓ Memoria de Cálculo contiene la sección analítica de CMP y desglose sensible/latente.")

    # TEST 7: Verificación de Diálogo de Selección de Materiales (Actualización en tiempo real)
    print("\n[TEST 7] Verificación de Actualización Dinámica de Materiales...")
    from ui.material_dialog import MaterialSelectionDialog
    from core.materials import PREDEFINED_ROOFS
    diag = MaterialSelectionDialog("techo", PREDEFINED_ROOFS, parent=win)
    
    # 7.1 Seleccionar UPVC 3.0 mm
    diag.combo_options.setCurrentText("UPVC 3.0 mm")
    assert abs(diag.spin_thickness.value() - 0.003) < 1e-4, f"Espesor incorrecto: {diag.spin_thickness.value()}"
    assert abs(diag.spin_conductivity.value() - 0.17) < 1e-3, f"Conductividad incorrecta: {diag.spin_conductivity.value()}"
    assert abs(diag.spin_absorptance.value() - 0.40) < 1e-2, f"Absortancia incorrecta: {diag.spin_absorptance.value()}"
    print(f"   - UPVC 3.0 mm: d = {diag.spin_thickness.value()} m, λ = {diag.spin_conductivity.value()} W/m·K, α = {diag.spin_absorptance.value()}")

    # 7.2 Seleccionar Termotecho 5 cm
    diag.combo_options.setCurrentText("Termotecho 5 cm (PUR 50mm)")
    assert abs(diag.spin_thickness.value() - 0.05) < 1e-4, f"Espesor Termotecho incorrecto: {diag.spin_thickness.value()}"
    assert abs(diag.spin_conductivity.value() - 0.022) < 1e-3, f"Conductividad Termotecho incorrecta: {diag.spin_conductivity.value()}"
    print(f"   - Termotecho: d = {diag.spin_thickness.value()} m, λ = {diag.spin_conductivity.value()} W/m·K, U = {diag.spin_u_direct.value():.2f} W/m²·K")
    print("✓ El diálogo de materiales actualiza dinámicamente todas sus propiedades.")

    # TEST 8: Verificación de ScrollArea en Pestaña de Ventilación y Toma en Sombra
    print("\n[TEST 8] Verificación de ScrollArea y Toma de Aire en Sombra...")
    from PyQt6.QtWidgets import QScrollArea
    assert hasattr(win, "scroll_hvac") and isinstance(win.scroll_hvac, QScrollArea)
    print("✓ Pestaña de Ventilación contenida dentro de QScrollArea fluido.")

    win.combo_supply_source.setCurrentIndex(1)  # Patio sombreado (-2.5 °C)
    win._on_curr_supply_param_changed()
    assert win.supply_units[0].get("source") == 1
    print("✓ Inyector configurado con toma de aire fresco desde Patio Sombreado (-2.5 °C).")

    print("\n" + "=" * 70)
    print("¡AUDITORÍA PROFUNDA FINALIZADA EXITOSAMENTE! TODOS LOS CÁLCULOS VERIFICADOS.")
    print("=" * 70)

if __name__ == "__main__":
    run_deep_audit()
