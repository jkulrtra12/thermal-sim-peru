# ==============================================================================
# Plugin de Exportación Térmica con Asignación de Componentes para SketchUp
# ==============================================================================
require 'sketchup.rb'
require 'json'

module ThermalSimulator
  module Exporter

    def self.export_model
      model = Sketchup.active_model
      if model.nil?
        UI.messagebox("No hay ningún modelo activo en SketchUp.")
        return
      end

      # 1. Obtener lista de componentes y grupos existentes en el modelo
      component_names = []
      model.entities.each do |e|
        if e.is_a?(Sketchup::Group)
          component_names << e.name unless e.name.empty?
        elsif e.is_a?(Sketchup::ComponentInstance)
          component_names << e.definition.name unless e.definition.name.empty?
        end
      end
      component_names.uniq!

      # Diálogo interactivo para asignar materiales y roles rápidos si existen componentes
      materials_list = [
        "Techo: UPVC 2.5 mm",
        "Techo: Termotecho 5 cm",
        "Techo: Termotecho 10 cm",
        "Techo: Aluzinc Simple",
        "Muro: Bloques de Concreto 14 cm",
        "Muro: Termomuro 5 cm",
        "Muro: Termomuro 10 cm",
        "Muro: Ladrillo King Kong 15 cm",
        "Muro: Fibrocemento con Aislante",
        "Edificio Vecino (Solo Sombra)"
      ].join("|")

      filepath = UI.savepanel("Guardar Modelo para Simulador Térmico", "", "modelo_bioclimatico.json")
      return if filepath.nil?

      surfaces_data = []
      obstacles_data = []

      # Función de extracción
      process_entities = lambda do |entities, transformation, parent_name|
        entities.each do |entity|
          if entity.is_a?(Sketchup::Face)
            pts = entity.vertices.map do |v|
              pt = v.position.transform(transformation)
              [pt.x.to_m.round(3), pt.y.to_m.round(3), pt.z.to_m.round(3)]
            end

            normal = entity.normal.transform(transformation)
            layer_name = (entity.layer ? entity.layer.name : "").upcase
            full_tag = "#{parent_name}_#{layer_name}".upcase

            mat = entity.material
            mat_name = mat ? mat.name.upcase : ""
            mat_alpha = mat ? mat.alpha : 1.0

            is_window = (mat_alpha < 0.88) ||
                        mat_name.include?("VIDRIO") ||
                        mat_name.include?("GLASS") ||
                        mat_name.include?("CRISTAL") ||
                        mat_name.include?("TRANSLUCENT") ||
                        full_tag.include?("VENTANA") ||
                        full_tag.include?("WINDOW") ||
                        full_tag.include?("VANO")

            is_neighbor = full_tag.include?("VECINO") || 
                          full_tag.include?("SOMBRA") || 
                          full_tag.include?("COLINDANTE")

            if is_neighbor
              obstacles_data << {
                "name" => (parent_name.empty? ? "Obstaculo_Vecino" : parent_name),
                "direction" => self.determine_direction(normal),
                "vertices" => pts
              }
            else
              is_roof = normal.z > 0.60
              avg_z = pts.map { |p| p[2] }.sum / pts.length.to_f
              level = (avg_z > 3.2) ? 2 : 1

              if is_window
                surf_type = "window"
                suggested_mat = "Vidrio Simple Claro 4 mm"
                thickness_m = 0.004
              elsif is_roof
                surf_type = "roof"
                if full_tag.include?("TERMOTECHO")
                  suggested_mat = "Termotecho 5 cm (PUR 50mm)"
                  thickness_m = 0.05
                else
                  suggested_mat = "UPVC 2.5 mm"
                  thickness_m = 0.0025
                end
              else
                surf_type = (normal.z < -0.60) ? "floor" : "wall"
                if full_tag.include?("TERMOMURO")
                  suggested_mat = "Termomuro 5 cm (PUR 50mm)"
                  thickness_m = 0.05
                elsif full_tag.include?("BLOQUE")
                  suggested_mat = "Bloques de Concreto Alveolares (Parcialmente Rellenos 14 cm)"
                  thickness_m = 0.14
                else
                  suggested_mat = "Ladrillo King Kong 18 huecos (Tarrajeado 15 cm)"
                  thickness_m = 0.15
                end
              end

              surfaces_data << {
                "name" => (parent_name.empty? ? "Cara_#{surf_type}_N#{level}" : parent_name),
                "type" => surf_type,
                "level" => level,
                "vertices" => pts,
                "orientation" => self.determine_direction(normal),
                "material_name" => suggested_mat,
                "thickness_m" => thickness_m
              }
            end

          elsif entity.is_a?(Sketchup::Group)
            g_name = entity.name.empty? ? parent_name : entity.name
            process_entities.call(entity.entities, transformation * entity.transformation, g_name)
          elsif entity.is_a?(Sketchup::ComponentInstance)
            c_name = entity.definition.name.empty? ? parent_name : entity.definition.name
            process_entities.call(entity.definition.entities, transformation * entity.transformation, c_name)
          end
        end
      end

      process_entities.call(model.active_entities, Geom::Transformation.new, "")

      # Las superficies pertenecen a la edificación a menos que su grupo/etiqueta indique vecino
      export_hash = {
        "app" => "Simulador Térmico Bioclimático Perú",
        "version" => "1.2",
        "units" => "meters",
        "surfaces" => surfaces_data,
        "obstacles" => obstacles_data
      }

      File.open(filepath, "w:UTF-8") do |f|
        f.write(JSON.pretty_generate(export_hash))
      end

      UI.messagebox("¡Exportación Completada!\n\nSuperficies de la Edificación: #{surfaces_data.length}\nObstáculos Vecinos (Sombras): #{obstacles_data.length}\n\nArchivo listo para cargar en el Simulador Térmico.")
    end

    def self.determine_direction(normal)
      if normal.z.abs > 0.65
        return (normal.z > 0) ? "Techo" : "Piso"
      elsif normal.y.abs >= normal.x.abs
        return (normal.y > 0) ? "Norte" : "Sur"
      else
        return (normal.x > 0) ? "Este" : "Oeste"
      end
    end

    def self.auto_separate_neighbors(surfaces)
      bld = []
      obs = []
      surfaces.each do |s|
        max_z = s["vertices"].map { |v| v[2] }.max || 0
        if max_z > 5.5
          obs << {
            "name" => "Edificio_Colindante",
            "direction" => s["orientation"],
            "vertices" => s["vertices"]
          }
        else
          bld << s
        end
      end
      [bld, obs]
    end

  end

  unless file_loaded?(__FILE__)
    menu = UI.menu('Extensions')
    menu.add_item('Exportar a Simulador Térmico (.json)...') {
      Exporter.export_model
    }
    file_loaded?(__FILE__)
  end
end
