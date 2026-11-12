"""
Generador de modelos 3D de prueba en JSON y OBJ para probar la aplicación.
"""

import os
import json
from geometry.building_model import BuildingGeometry3D


def generate_samples():
    os.makedirs("modelos_sketchup", exist_ok=True)

    # 1. Modelo que coincide exactamente con la imagen de SketchUp del usuario:
    # 1 piso con 2 ventanas frontales, puerta, y muros vecinos colindantes altos (6 metros)
    bld_1 = BuildingGeometry3D.create_default_building(
        length=9.0,
        width=5.5,
        height_piso=2.8,
        num_floors=1,
        neighbor_east_height=6.0,
        neighbor_west_height=5.5
    )

    data_1 = {
        "app": "Simulador Térmico Bioclimático Perú",
        "name": "Edificación 1 Piso con Muros Vecinos Altos (SketchUp)",
        "surfaces": [
            {
                "name": s.name,
                "type": s.surface_type,
                "level": s.level,
                "vertices": s.vertices,
                "orientation": s.orientation
            }
            for s in bld_1.surfaces
        ],
        "obstacles": [
            {
                "name": obs.name,
                "direction": obs.orientation,
                "vertices": obs.vertices
            }
            for obs in bld_1.neighbor_obstacles
        ]
    }

    with open("modelos_sketchup/edificio_1_piso_con_vecinos.json", "w", encoding="utf-8") as f:
        json.dump(data_1, f, indent=2)

    # 2. Modelo de 2 niveles (con Nivel 2 expuesto a radiación solar sobrecubierta)
    bld_2 = BuildingGeometry3D.create_default_building(
        length=8.0,
        width=5.0,
        height_piso=2.8,
        num_floors=2,
        neighbor_east_height=4.5,
        neighbor_west_height=4.0
    )

    data_2 = {
        "app": "Simulador Térmico Bioclimático Perú",
        "name": "Edificación 2 Niveles - Nivel 2 Expuesto (SketchUp)",
        "surfaces": [
            {
                "name": s.name,
                "type": s.surface_type,
                "level": s.level,
                "vertices": s.vertices,
                "orientation": s.orientation
            }
            for s in bld_2.surfaces
        ],
        "obstacles": [
            {
                "name": obs.name,
                "direction": obs.orientation,
                "vertices": obs.vertices
            }
            for obs in bld_2.neighbor_obstacles
        ]
    }

    with open("modelos_sketchup/edificio_2_pisos_con_vecinos.json", "w", encoding="utf-8") as f:
        json.dump(data_2, f, indent=2)

    print("Modelos de prueba generados en carpeta 'modelos_sketchup/'")


if __name__ == "__main__":
    generate_samples()
