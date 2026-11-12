"""
Cargador Inteligente de Modelos 3D de SketchUp (OBJ, STL, JSON térmico).
Incluye corrección automática de ejes (Y-up vs Z-up), detección de escala (mm a m)
y separación automática de edificios vecinos colindantes.
"""

import os
import json
import numpy as np
from typing import Optional, List, Tuple
from geometry.building_model import BuildingGeometry3D, Surface3D


class SketchUpLoader:
    """Lector y corrector de archivos 3D provenientes de SketchUp."""

    @staticmethod
    def load_from_json(filepath: str) -> Optional[BuildingGeometry3D]:
        """Carga un archivo JSON exportado por el plugin RBZ de SketchUp."""
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            model = BuildingGeometry3D()
            for surf_data in data.get("surfaces", []):
                sname = surf_data.get("name", "Superficie")
                stype = surf_data.get("type", "wall")
                level = surf_data.get("level", 1)
                verts = [tuple(v) for v in surf_data.get("vertices", [])]
                orient = surf_data.get("orientation", "Horizontal")
                mat = surf_data.get("material_name", "")
                thick = float(surf_data.get("thickness_m", 0.15))

                # Clasificación inteligente automática por nombre o material
                combined = f"{sname.lower()} {mat.lower()}"
                if any(k in combined for k in ["ventana", "window", "vidrio", "cristal", "glass", "vano", "translucent"]):
                    stype = "window"
                    if not mat:
                        mat = "Vidrio Simple Claro 4 mm"
                    thick = 0.004
                elif any(k in combined for k in ["puerta", "door"]):
                    stype = "door"
                    if not mat:
                        mat = "Puerta de Madera / Tablero"
                    thick = 0.04
                elif any(k in combined for k in ["piso", "floor", "suelo", "contrapiso"]):
                    stype = "floor"
                    if not mat:
                        mat = "Piso Concreto 15 cm"
                    thick = 0.15
                elif any(k in combined for k in ["techo", "roof", "cubierta", "aluzinc", "cielo"]):
                    if stype != "wall" or orient in ["Techo", "Horizontal"]:
                        stype = "roof"

                model.add_surface(Surface3D(
                    name=sname,
                    surface_type=stype,
                    level=level,
                    vertices=verts,
                    orientation=orient,
                    material_name=mat,
                    thickness_m=thick
                ))

            for obs_data in data.get("obstacles", []):
                model.add_surface(Surface3D(
                    name=obs_data.get("name", "Edificio Vecino"),
                    surface_type="neighbor_wall",
                    level=0,
                    vertices=[tuple(v) for v in obs_data.get("vertices", [])],
                    orientation=obs_data.get("direction", "Este")
                ))

            return model
        except Exception as e:
            print(f"Error al leer JSON de SketchUp: {e}")
            return None

    @staticmethod
    def load_from_obj(filepath: str) -> Optional[BuildingGeometry3D]:
        """
        Carga geometría 3D desde un archivo OBJ de SketchUp con:
        1. Auto-detección de unidades (mm/cm a metros).
        2. Auto-detección de orientación de ejes (Y-up a Z-up si es necesario).
        3. Separación inteligente de edificios vecinos por componentes conexos.
        """
        if not os.path.exists(filepath):
            return None

        try:
            import trimesh
            mesh = trimesh.load(filepath, force="mesh")
            if mesh.is_empty:
                return None

            vertices = np.array(mesh.vertices, dtype=np.float64)
            faces = np.array(mesh.faces)

            # 1. Corrección de unidades (si mide más de 100 unidades, está en mm o cm)
            bbox_span = np.ptp(vertices, axis=0)  # [dx, dy, dz]
            max_span = np.max(bbox_span)
            if max_span > 200.0:  # En milímetros
                vertices /= 1000.0
            elif max_span > 60.0:  # En centímetros
                vertices /= 100.0

            # 2. Corrección de orientación de ejes si se exportó con Y-up
            # En arquitectura, la altura vertical suele ser el menor o mediano eje respecto al suelo
            # Si Y tiene mayor elevación o normals apuntan en Y, rotamos para que Z sea arriba
            if bbox_span[1] < bbox_span[2] * 0.5:
                # Ya es Z arriba
                pass
            elif np.ptp(vertices[:, 1]) > np.ptp(vertices[:, 2]) * 1.5:
                # Probable Y es arriba: rotar 90 grados alrededor de X
                rot = np.array([
                    [1,  0, 0],
                    [0,  0, 1],
                    [0, -1, 0]
                ], dtype=np.float64)
                vertices = vertices @ rot.T

            # Llevar el piso al nivel Z = 0
            min_z = np.min(vertices[:, 2])
            vertices[:, 2] -= min_z

            # Actualizar malla corregida
            corrected_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

            # 3. Separación de cuerpos conexos (Casa central vs. Edificios vecinos)
            try:
                components = corrected_mesh.split(only_watertight=False)
            except Exception as e_split:
                print(f"Aviso en split(): {e_split}. Procesando malla como componente único.")
                components = [corrected_mesh]
            model = BuildingGeometry3D()

            if len(components) > 1:
                # Ordenamos componentes por volumen o área
                # El edificio de estudio suele ser el que tiene menor altura o está al centro
                centroids = [c.centroid for c in components]
                heights = [np.ptp(c.vertices[:, 2]) for c in components]

                # El edificio central suele tener menor altura (ej. casa con techo a dos aguas)
                # respecto a las medianeras altas de 2 o 3 pisos
                main_idx = int(np.argmin(heights))

                for idx, comp in enumerate(components):
                    is_neighbor = (idx != main_idx)
                    for f_idx, face in enumerate(comp.faces):
                        tri_pts = [tuple(comp.vertices[i]) for i in face]
                        norm = comp.face_normals[f_idx]
                        avg_z = sum(p[2] for p in tri_pts) / 3.0

                        if is_neighbor:
                            model.add_surface(Surface3D(
                                name=f"Vecino_{idx}_Cara_{f_idx}",
                                surface_type="neighbor_wall",
                                level=0,
                                vertices=tri_pts
                            ))
                        else:
                            is_roof = norm[2] > 0.50
                            level = 2 if avg_z > 3.0 else 1
                            stype = "roof" if is_roof else ("floor" if norm[2] < -0.50 else "wall")
                            model.add_surface(Surface3D(
                                name=f"Casa_Cara_{f_idx}",
                                surface_type=stype,
                                level=level,
                                vertices=tri_pts
                            ))
            else:
                # Componente único: clasificar por orientación y altura relativa
                max_model_z = np.max(vertices[:, 2])
                mid_model_z = max_model_z * 0.5

                for f_idx, face in enumerate(corrected_mesh.faces):
                    tri_pts = [tuple(corrected_mesh.vertices[i]) for i in face]
                    norm = corrected_mesh.face_normals[f_idx]
                    avg_z = sum(p[2] for p in tri_pts) / 3.0

                    is_roof = norm[2] > 0.45
                    is_floor = norm[2] < -0.45
                    level = 2 if avg_z > mid_model_z else 1
                    stype = "roof" if is_roof else ("floor" if is_floor else "wall")

                    model.add_surface(Surface3D(
                        name=f"Casa_Cara_{f_idx}",
                        surface_type=stype,
                        level=level,
                        vertices=tri_pts
                    ))

            return model
        except Exception as e:
            print(f"Error procesando OBJ inteligente: {e}")
            return None
