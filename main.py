"""
Punto de Entrada de la Aplicación de Simulación Térmica y Solar 3D (Windows).
"""

import sys
import os
import datetime

# Asegurar que el directorio raíz del proyecto esté en el PATH de Python
if getattr(sys, 'frozen', False):
    CURRENT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    APP_DIR = os.path.dirname(sys.executable)
else:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = CURRENT_DIR

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


def global_exception_hook(exctype, value, tb):
    """Captura cualquier excepción no manejada para evitar el cierre silencioso de la aplicación."""
    import traceback
    trace_str = "".join(traceback.format_exception(exctype, value, tb))
    sys.stderr.write(trace_str)
    try:
        log_path = os.path.join(APP_DIR, "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- ERROR {datetime.datetime.now().isoformat()} ---\n{trace_str}\n")
    except Exception:
        pass
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Aviso de Error en la Aplicación",
            f"Se ha detectado una excepción:\n\n{value}\n\nLos detalles técnicos se han guardado en error.log."
        )
    except Exception:
        pass


sys.excepthook = global_exception_hook

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Simulador Térmico Bioclimático Perú")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
