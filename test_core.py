from core import (
    PERU_CITIES,
    PREDEFINED_ROOFS,
    PREDEFINED_CEILINGS,
    PREDEFINED_WALLS,
    create_custom_material,
    RoofCeilingAssembly,
    ThermalZoneConfig,
    NeighborObstacle,
    WindTurbineVentilator,
    MultiLevelThermalSimulator,
)

def run_test():
    city = PERU_CITIES["Piura (Costa Norte - Cálido Extremo)"]
    print(f"--- Ciudad: {city.name} ---")

    # 1. Ensamble de Techo + Cielo Raso
    roof_upvc = PREDEFINED_ROOFS["UPVC 2.5 mm"]
    ceiling_min = PREDEFINED_CEILINGS["Fibra Mineral (15 mm / 5/8\")"]
    assembly = RoofCeilingAssembly(
        name="UPVC + Fibra Mineral",
        roof_material=roof_upvc,
        ceiling_material=ceiling_min,
        cavity_ventilated=True
    )
    print(f"Ensamble Cubierta: {assembly.description}")

    # 2. Material personalizado
    custom_wall = create_custom_material(
        name="Mi Muro Ecológico",
        category="muro",
        thickness_m=0.12,
        conductivity_w_mk=0.15,
        solar_absorptance=0.35,
        description="Muro de quincha mejorada con cal"
    )
    print(f"Material Personalizado: {custom_wall.name}, U = {custom_wall.u_value:.2f} W/m2K")

    # 3. Zonas Térmicas (Nivel 1 y Nivel 2)
    z1 = ThermalZoneConfig(name="Nivel 1", level_number=1, wall_material=custom_wall)
    z2 = ThermalZoneConfig(name="Nivel 2", level_number=2, wall_material=PREDEFINED_WALLS["Termomuro 5 cm (PUR 50mm)"])

    # 4. Obstáculo vecino alto (muro de 6m en lado Este que da sombra en la mañana)
    obs = [NeighborObstacle(name="Muro Vecino Este", direction="Este", height_m=6.0, distance_to_wall_m=0.3)]

    # 5. Extractor eólico en techo
    turbine = WindTurbineVentilator(name="Extractor Eólico 24\"", throat_diameter_inches=24.0, quantity=2)

    # 6. Simulación 24 Horas
    sim = MultiLevelThermalSimulator(
        zone_1=z1,
        zone_2=z2,
        roof_assembly=assembly,
        wind_turbine=turbine,
        climate=city,
        obstacles=obs
    )
    results = sim.simulate_24h(season="summer")

    print("\n--- Resultados Horarios Muestra (Verano en Piura) ---")
    print(f"{'Hora':<6} | {'T_Ext (°C)':<10} | {'T_Nivel 1 (°C)':<15} | {'T_Nivel 2 (°C)':<15} | {'Rad (W/m2)':<10}")
    print("-" * 65)
    for h in [8, 11, 14, 17, 21]:
        r = results[h]
        print(f"{r['hour']:02d}:00  | {r['t_ext']:<10.1f} | {r['t_int_level_1']:<15.1f} | {r['t_int_level_2']:<15.1f} | {r['solar_radiation']:<10.1f}")

if __name__ == "__main__":
    run_test()
