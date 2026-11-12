# -*- coding: utf-8 -*-
"""
Widget de Memoria de Cálculo Detallada (RNE Norma EM.110 y ASHRAE 55).
Permite visualizar la memoria explicativa con fórmulas, copiarla y exportarla a HTML / PDF.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QLabel,
    QFileDialog,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QTextDocument


class CalculationMemoryWidget(QWidget):
    """Pestaña central para visualización y exportación de la Memoria de Cálculo."""

    request_refresh = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_markdown: str = ""
        self.current_html: str = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Barra Superior de Herramientas
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_refresh = QPushButton("🔄 Recalcular y Actualizar")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #0288d1;
                color: #ffffff;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #039be5; }
        """)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        toolbar.addWidget(self.btn_refresh)

        self.btn_copy = QPushButton("📋 Copiar Texto (Markdown)")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #ffffff;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        toolbar.addWidget(self.btn_copy)

        self.btn_export_html = QPushButton("💾 Guardar Informe HTML...")
        self.btn_export_html.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: #ffffff;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #388e3c; }
        """)
        self.btn_export_html.clicked.connect(self._on_export_html_clicked)
        toolbar.addWidget(self.btn_export_html)

        self.btn_print = QPushButton("🖨️ Exportar a PDF...")
        self.btn_print.setStyleSheet("""
            QPushButton {
                background-color: #5e35b1;
                color: #ffffff;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #673ab7; }
        """)
        self.btn_print.clicked.connect(self._on_export_pdf_clicked)
        toolbar.addWidget(self.btn_print)

        toolbar.addStretch()

        self.lbl_status = QLabel("Norma Técnica EM.110 - Confort Térmico y Lumínico")
        self.lbl_status.setStyleSheet("color: #9ca3af; font-size: 12px; font-style: italic;")
        toolbar.addWidget(self.lbl_status)

        layout.addLayout(toolbar)

        # Visor de Documento HTML enriquecido
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #15151e;
                color: #d1d5db;
                border: 1px solid #282838;
                border-radius: 6px;
                padding: 16px;
                selection-background-color: #0288d1;
                selection-color: #ffffff;
            }
        """)
        layout.addWidget(self.browser)

    def set_content(self, md_text: str, html_text: str):
        """Actualiza el contenido de la memoria de cálculo."""
        self.current_markdown = md_text
        self.current_html = html_text
        self.browser.setHtml(html_text)

    def _on_refresh_clicked(self):
        self.request_refresh.emit()

    def _on_copy_clicked(self):
        if not self.current_markdown:
            QMessageBox.information(self, "Memoria de Cálculo", "No hay memoria generada para copiar.")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self.current_markdown)
        QMessageBox.information(
            self,
            "Copiado Exitoso",
            "La Memoria de Cálculo completa en formato Markdown ha sido copiada al portapapeles.\n"
            "Puedes pegarla directamente en Word, Notion, Obsidian o tu editor preferido."
        )

    def _on_export_html_clicked(self):
        if not self.current_html:
            QMessageBox.information(self, "Memoria de Cálculo", "No hay memoria generada para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Memoria de Cálculo HTML",
            "Memoria_Calculo_Termica_EM110.html",
            "Archivos Web HTML (*.html *.htm)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.current_html)
                QMessageBox.information(
                    self,
                    "Exportación Exitosa",
                    f"La memoria ha sido guardada exitosamente en:\n{file_path}\nPuedes abrirla en cualquier navegador o imprimirla a PDF."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")

    def _on_export_pdf_clicked(self):
        if not self.browser.toPlainText().strip():
            QMessageBox.information(self, "Memoria de Cálculo", "No hay contenido para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Memoria a Formato PDF",
            "Memoria_Calculo_Termica_EM110.pdf",
            "Documento PDF (*.pdf)"
        )
        if not file_path:
            return

        try:
            # Intento de exportar con QPrinter / QtPrintSupport si está disponible
            try:
                from PyQt6.QtPrintSupport import QPrinter
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(file_path)
                self.browser.document().print(printer)
                QMessageBox.information(
                    self,
                    "PDF Generado",
                    f"El documento PDF se generó exitosamente en:\n{file_path}"
                )
            except ImportError:
                # Si QtPrintSupport no está en el entorno binario, guardamos HTML listo para imprimir
                html_path = file_path.replace(".pdf", ".html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(self.current_html)
                QMessageBox.information(
                    self,
                    "Informe Guardado",
                    f"Se guardó el informe HTML imprimible en:\n{html_path}\nÁbrelo con tu navegador y pulsa Ctrl+P para guardar como PDF."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar PDF", f"Ocurrió un error:\n{e}")
