# ==============================================================================
# Registro de Extensión para SketchUp
# ==============================================================================
require 'sketchup.rb'
require 'extensions.rb'

module ThermalSimulator
  unless file_loaded?(__FILE__)
    ext = SketchupExtension.new("Simulador Térmico Bioclimático", "thermal_exporter/main.rb")
    ext.description = "Exporta modelos 3D y obstáculos vecinos para el Simulador Térmico de Windows."
    ext.version     = "1.0.0"
    ext.creator     = "Antigravity Engineering"
    ext.copyright   = "2026"

    Sketchup.register_extension(ext, true)
    file_loaded?(__FILE__)
  end
end
