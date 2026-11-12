"""
Diálogo para selección y creación de Materiales Constructivos (RNE EM.110 Perú).
Permite elegir entre el catálogo predefinido para Perú o definir un material a medida,
mostrando en tiempo real todas las propiedades termofísicas (Espesor, λ, U, α, R).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QDoubleSpinBox, QPushButton, QGroupBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from core.materials import Material, create_custom_material


class MaterialSelectionDialog(QDialog):
    """Diálogo emergente para seleccionar o personalizar un material con inspección en tiempo real."""

    def __init__(self, category: str, predefined_dict: dict, current_material: Material = None, parent=None):
        super().__init__(parent)
        self.category = category  # 'techo', 'cielo_raso', 'muro', 'ventana', 'piso'
        self.predefined_dict = predefined_dict or {}
        self.selected_material: Material = current_material

        cat_names = {
            "techo": "Techo / Cubierta",
            "cielo_raso": "Cielo Raso",
            "muro": "Muros / Fachadas",
            "ventana": "Ventanas / Vidrios",
            "piso": "Pisos / Losas"
        }
        title_cat = cat_names.get(category.lower(), category.capitalize())
        self.setWindowTitle(f"Configuración de Material: {title_cat}")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Selector de Predefinidos o Personalizado
        combo_layout = QHBoxLayout()
        lbl_sel = QLabel("Seleccionar Material:")
        lbl_sel.setStyleSheet("font-weight: bold; font-size: 12px; color: #00e5ff;")
        combo_layout.addWidget(lbl_sel)

        self.combo_options = QComboBox()
        self.combo_options.setStyleSheet("font-size: 12px; font-weight: bold; padding: 4px;")
        for name in self.predefined_dict.keys():
            self.combo_options.addItem(name)
        self.combo_options.addItem("--- Personalizado (Definir Propiedades a Medida) ---")

        if self.selected_material and self.selected_material.name in self.predefined_dict:
            self.combo_options.setCurrentText(self.selected_material.name)
        elif self.selected_material and getattr(self.selected_material, "is_custom", False):
            self.combo_options.setCurrentText("--- Personalizado (Definir Propiedades a Medida) ---")

        self.combo_options.currentIndexChanged.connect(self._on_option_changed)
        combo_layout.addWidget(self.combo_options, 1)
        layout.addLayout(combo_layout)

        # 2. Grupo de Propiedades Termofísicas (RNE EM.110 / ISO 6946)
        self.group_props = QGroupBox("Propiedades Termofísicas y Térmicas (RNE EM.110)")
        self.group_props.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3d3d5c;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #1a1a24;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #ffb74d;
            }
            QLineEdit, QDoubleSpinBox {
                background-color: #262636;
                color: #ffffff;
                border: 1px solid #4a4a68;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 11px;
            }
            QLineEdit:disabled, QDoubleSpinBox:disabled {
                background-color: #1e1e2a;
                color: #80deea;
                border: 1px solid #33334d;
            }
        """)
        form = QFormLayout(self.group_props)
        form.setSpacing(8)

        self.txt_name = QLineEdit("Mi Material")
        form.addRow("Nombre del Material:", self.txt_name)

        self.spin_thickness = QDoubleSpinBox()
        self.spin_thickness.setRange(0.0001, 2.0)
        self.spin_thickness.setDecimals(4)
        self.spin_thickness.setSingleStep(0.005)
        self.spin_thickness.setSuffix(" m")
        self.spin_thickness.valueChanged.connect(self._on_custom_values_edited)
        form.addRow("Espesor (d):", self.spin_thickness)

        self.spin_conductivity = QDoubleSpinBox()
        self.spin_conductivity.setRange(0.001, 250.0)
        self.spin_conductivity.setDecimals(3)
        self.spin_conductivity.setSingleStep(0.02)
        self.spin_conductivity.setSuffix(" W/m·K")
        self.spin_conductivity.valueChanged.connect(self._on_custom_values_edited)
        form.addRow("Conductividad térmica (λ):", self.spin_conductivity)

        self.spin_u_direct = QDoubleSpinBox()
        self.spin_u_direct.setRange(0.05, 50.0)
        self.spin_u_direct.setDecimals(2)
        self.spin_u_direct.setSingleStep(0.1)
        self.spin_u_direct.setSuffix(" W/m²·K")
        form.addRow("Transmitancia térmica (U):", self.spin_u_direct)

        self.spin_absorptance = QDoubleSpinBox()
        self.spin_absorptance.setRange(0.05, 0.98)
        self.spin_absorptance.setDecimals(2)
        self.spin_absorptance.setSingleStep(0.05)
        form.addRow("Absortancia Solar (α, 0.1 claro - 0.9 oscuro):", self.spin_absorptance)

        # Indicador de Resistencia Térmica R y Estado
        self.lbl_r_value = QLabel("Resistencia Térmica Total: R = -- m²·K/W")
        self.lbl_r_value.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 11px;")
        form.addRow("Resistencia Térmica:", self.lbl_r_value)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #b0bec5; font-size: 10px; font-style: italic; padding: 4px;")
        form.addRow("Descripción / Norma:", self.lbl_desc)

        layout.addWidget(self.group_props)

        # 3. Botones Aceptar / Cancelar
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Aplicar Material")
        self.btn_ok.setStyleSheet("background-color: #0288d1; color: #ffffff; font-weight: bold; padding: 6px 16px;")
        self.btn_ok.clicked.connect(self._on_apply)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        # Cargar valores iniciales en los campos
        self._on_option_changed()

    def _on_option_changed(self):
        """Actualiza instantáneamente todos los campos del formulario según el material seleccionado."""
        text = self.combo_options.currentText()
        is_custom = "Personalizado" in text

        if not is_custom and text in self.predefined_dict:
            mat = self.predefined_dict[text]
            if mat is not None:
                self.txt_name.blockSignals(True)
                self.spin_thickness.blockSignals(True)
                self.spin_conductivity.blockSignals(True)
                self.spin_u_direct.blockSignals(True)
                self.spin_absorptance.blockSignals(True)

                self.txt_name.setText(mat.name)
                self.spin_thickness.setValue(mat.thickness)
                self.spin_conductivity.setValue(mat.conductivity)
                self.spin_u_direct.setValue(mat.u_value)
                self.spin_absorptance.setValue(mat.solar_absorptance)

                r_surf = 0.14 if self.category in ("techo", "cielo_raso") else 0.17
                r_tot = mat.thermal_resistance + r_surf
                self.lbl_r_value.setText(
                    f"R_material = {mat.thermal_resistance:.3f} m²·K/W  |  R_total = {r_tot:.3f} m²·K/W  |  U = {mat.u_value:.2f} W/m²·K"
                )
                self.lbl_desc.setText(
                    f"Normativa RNE / Catálogo Perú: {mat.description or 'Material certificado estándar.'}"
                )

                self.txt_name.blockSignals(False)
                self.spin_thickness.blockSignals(False)
                self.spin_conductivity.blockSignals(False)
                self.spin_u_direct.blockSignals(False)
                self.spin_absorptance.blockSignals(False)

            # En modo predefinido, los campos muestran el valor exacto pero bloqueados para proteger el estándar
            self.txt_name.setEnabled(False)
            self.spin_thickness.setEnabled(False)
            self.spin_conductivity.setEnabled(False)
            self.spin_u_direct.setEnabled(False)
            self.spin_absorptance.setEnabled(False)
        else:
            # En modo personalizado, los campos se desbloquean y se pueden editar
            self.txt_name.setEnabled(True)
            self.spin_thickness.setEnabled(True)
            self.spin_conductivity.setEnabled(True)
            self.spin_u_direct.setEnabled(True)
            self.spin_absorptance.setEnabled(True)
            if self.txt_name.text() in self.predefined_dict:
                self.txt_name.setText(f"{self.txt_name.text()} (Personalizado)")
            self.lbl_desc.setText("Modo personalizado: Modifica libremente el espesor, conductividad λ, U o absortancia solar.")
            self._on_custom_values_edited()

    def _on_custom_values_edited(self):
        """Recalcula en tiempo real U y R cuando el usuario modifica espesor o conductividad en modo custom."""
        if "Personalizado" not in self.combo_options.currentText():
            return
        d = self.spin_thickness.value()
        lam = self.spin_conductivity.value()
        if lam > 0.0 and d > 0.0:
            r_mat = d / lam
            r_surf = 0.14 if self.category in ("techo", "cielo_raso") else 0.17
            r_tot = r_mat + r_surf
            u_calc = 1.0 / r_tot if r_tot > 0 else 99.0
            self.spin_u_direct.blockSignals(True)
            self.spin_u_direct.setValue(u_calc)
            self.spin_u_direct.blockSignals(False)
            self.lbl_r_value.setText(f"R_material = {r_mat:.3f} m²·K/W  |  R_total = {r_tot:.3f} m²·K/W  |  U = {u_calc:.2f} W/m²·K")

    def _on_apply(self):
        text = self.combo_options.currentText()
        if "Personalizado" in text:
            name = self.txt_name.text().strip() or "Material Personalizado"
            d = self.spin_thickness.value()
            lam = self.spin_conductivity.value()
            alfa = self.spin_absorptance.value()
            u_val = self.spin_u_direct.value()

            self.selected_material = create_custom_material(
                name=name,
                category=self.category,
                thickness_m=d,
                conductivity_w_mk=lam,
                solar_absorptance=alfa,
                description=f"Material personalizado por el usuario (U = {u_val:.2f} W/m²K, d = {d*1000:.1f} mm)"
            )
        else:
            self.selected_material = self.predefined_dict.get(text)

        self.accept()
