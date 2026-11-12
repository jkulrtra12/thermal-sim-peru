"""
Motor Térmico Dinámico Multinivel.
Calcula el balance de energía por zonas térmicas (Nivel 1 y Nivel 2 acoplados)
hora a hora a lo largo de un ciclo diario de 24 horas.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from core.materials import Material, PREDEFINED_WALLS, PREDEFINED_WINDOWS
from core.assemblies import RoofCeilingAssembly
from core.climate import PeruCityClimate, SolarEngine
from core.ventilation import (
    WindTurbineVentilator,
    MechanicalVentilation,
    CeilingComfortFan,
    AirConditioningSystem,
    RHO_AIR,
    CP_AIR,
)
from core.solar_shading import NeighborObstacle, SolarShadingCalculator
from core.comfort_cmp import ComfortCMPCalculator


@dataclass
class ThermalZoneConfig:
    """Configuración física de una zona térmica o nivel."""
    name: str = "Nivel 1"
    level_number: int = 1  # 1 o 2
    length_m: float = 8.0   # Longitud (m)
    width_m: float = 5.0    # Ancho (m)
    height_m: float = 2.8   # Altura de piso a techo (m)
    wall_material: Material = field(default_factory=lambda: PREDEFINED_WALLS["Ladrillo King Kong 18 huecos (Tarrajeado 15 cm)"])
    window_material: Material = field(default_factory=lambda: PREDEFINED_WINDOWS["Vidrio Simple Claro 4 mm"])
    window_area_m2: float = 4.0  # Área total acristalada
    window_open_ratio: float = 0.0  # Apertura de 0.0 a 0.50 (0% a 50% de área útil abierta)
    occupants: int = 2           # Ganancia interna humana (~100W por persona)
    occupant_heat_w: float = 100.0  # W por persona (75W reposo, 100W oficina, 130W actividad)
    equipment_w: float = 200.0   # Iluminación y computadoras/electrodomésticos

    # Sistemas de acondicionamiento por zona
    mechanical_vent: MechanicalVentilation = field(default_factory=MechanicalVentilation)
    comfort_fan: CeilingComfortFan = field(default_factory=CeilingComfortFan)
    ac_system: AirConditioningSystem = field(default_factory=AirConditioningSystem)

    @property
    def floor_area_m2(self) -> float:
        return self.length_m * self.width_m

    @property
    def volume_m3(self) -> float:
        return self.floor_area_m2 * self.height_m

    @property
    def gross_wall_area_m2(self) -> float:
        return 2.0 * (self.length_m + self.width_m) * self.height_m

    @property
    def net_wall_area_m2(self) -> float:
        return max(5.0, self.gross_wall_area_m2 - self.window_area_m2)

    @property
    def thermal_capacitance_j_k(self) -> float:
        """Capacitancia térmica de la zona (aire + masa de muros interiores/mobiliario)."""
        # Aire interior
        c_air = self.volume_m3 * RHO_AIR * CP_AIR
        # Masa efectiva de muros interiores (~20% del volumen del muro participa en la inercia diaria)
        muro_eff_vol = self.net_wall_area_m2 * self.wall_material.thickness * 0.25
        c_walls = muro_eff_vol * self.wall_material.density * self.wall_material.specific_heat
        return c_air + c_walls


class MultiLevelThermalSimulator:
    """Simulador térmico dinámico para edificaciones de 1 o 2 niveles."""

    def __init__(
        self,
        zone_1: ThermalZoneConfig,
        zone_2: Optional[ThermalZoneConfig] = None,
        roof_assembly: Optional[RoofCeilingAssembly] = None,
        wind_turbine: Optional[WindTurbineVentilator] = None,
        climate: Optional[PeruCityClimate] = None,
        obstacles: Optional[List[NeighborObstacle]] = None,
        north_orientation_deg: float = 0.0,
        slab_material: Optional[Material] = None,
    ):
        self.zone_1 = zone_1
        self.zone_2 = zone_2
        self.roof_assembly = roof_assembly
        self.wind_turbine = wind_turbine
        self.climate = climate
        self.obstacles = obstacles or []
        self.north_orientation_deg = north_orientation_deg
        self.slab_material = slab_material

    def _compute_damping_and_lag(self, mat: Optional[Material]) -> tuple:
        """Calcula el factor de amortiguamiento (f) y el desfase térmico (phi en horas) según ISO 13790 / ASHRAE."""
        if not mat or mat.thickness <= 0.001:
            return 0.95, 0.2
        rho_c = max(100.0, mat.density * mat.specific_heat)
        diffusivity = max(1e-9, mat.conductivity / rho_c)
        # Profundidad de penetración delta para ciclo diario (86400 s)
        delta = math.sqrt((diffusivity * 86400.0) / math.pi)
        xi = mat.thickness / max(0.005, delta)
        f = max(0.05, min(1.0, math.exp(-xi)))
        phi = max(0.0, min(12.0, xi * (24.0 / (2.0 * math.pi))))
        return f, phi

    def simulate_24h(self, season: str = 'summer', custom_ambient_t: Optional[float] = None) -> List[Dict]:
        """
        Simulación dinámica horaria acoplada conforme a ISO 13790, ASHRAE Fundamentals y RNE EM.110.
        Integra:
        1. Temperatura Sol-Aire por fachada y cubierta.
        2. Inercia térmica con amortiguamiento (f) y desfase horario (phi).
        3. Ganancia solar directa a través de vidrio (SHGC).
        4. Intercambio pasivo con el terreno natural.
        5. Balance convectivo de ventilación y climatización en equilibrio real.
        """
        hourly_weather = SolarEngine.get_hourly_profile(self.climate, season=season)

        # Ajuste de temperatura ambiental personalizada si fue solicitada
        if custom_ambient_t is not None:
            nominal_14 = hourly_weather[14]["t_ext"]
            offset = custom_ambient_t - nominal_14
            for s in hourly_weather:
                s["t_ext"] = round(s["t_ext"] + offset, 1)

        # -------------------------------------------------------------
        # 1. PARÁMETROS DE INERCIA, AMORTIGUAMIENTO Y DESFASE TÉRMICO
        # -------------------------------------------------------------
        f_w1, phi_w1 = self._compute_damping_and_lag(self.zone_1.wall_material)
        if self.zone_2:
            f_w2, phi_w2 = self._compute_damping_and_lag(self.zone_2.wall_material)
        else:
            f_w2, phi_w2 = f_w1, phi_w1

        roof_mat = self.roof_assembly.roof_material if (self.roof_assembly and self.roof_assembly.roof_material) else None
        f_roof, phi_roof = self._compute_damping_and_lag(roof_mat)
        if self.roof_assembly and self.roof_assembly.ceiling_material:
            f_roof = max(0.08, f_roof * 0.70)
            phi_roof = min(10.0, phi_roof + 1.5)

        # SHGC según tipo de vidrio
        win_name = self.zone_1.window_material.name if self.zone_1.window_material else ""
        if "Control Solar" in win_name or "Tintado" in win_name:
            shgc_val = 0.50
        elif "Doble" in win_name:
            shgc_val = 0.60
        else:
            shgc_val = 0.78  # Vidrio simple claro típico

        # -------------------------------------------------------------
        # 2. PRE-CÁLCULO DE TEMPERATURAS SOL-AIRE Y GANANCIA POR VENTANAS
        # -------------------------------------------------------------
        t_sa_roof = []
        t_sa_walls_1 = []
        t_sa_walls_2 = []
        q_sol_win_1_list = []
        q_sol_win_2_list = []

        roof_alpha = self.roof_assembly.effective_solar_absorptance if self.roof_assembly else 0.6
        wall_alpha_1 = self.zone_1.wall_material.solar_absorptance if self.zone_1.wall_material else 0.6
        wall_alpha_2 = self.zone_2.wall_material.solar_absorptance if (self.zone_2 and self.zone_2.wall_material) else wall_alpha_1

        facades = ["Norte", "Sur", "Este", "Oeste"]
        w_area_facade_1 = self.zone_1.net_wall_area_m2 / 4.0
        wi_area_facade_1 = self.zone_1.window_area_m2 / 4.0

        if self.zone_2:
            w_area_facade_2 = self.zone_2.net_wall_area_m2 / 4.0
            wi_area_facade_2 = self.zone_2.window_area_m2 / 4.0
        else:
            w_area_facade_2 = wi_area_facade_2 = 0.0

        for step in hourly_weather:
            t_ext = step["t_ext"]
            sol_elev = step["solar_elevation"]
            sol_azim = (step["solar_azimuth"] + self.north_orientation_deg) % 360.0
            dir_rad = step["direct_radiation"]
            dif_rad = step["diffuse_radiation"]

            # Techo
            sin_elev = math.sin(math.radians(max(0.0, sol_elev))) if sol_elev > 0 else 0.0
            rad_roof = (dir_rad * sin_elev) + (dif_rad if sol_elev > 0 else 0.0)
            # Enfriamiento radiativo hacia el cielo (-4 °C día/noche)
            t_sa_r = t_ext + (roof_alpha * rad_roof / 20.0) - (4.0 if sol_elev <= 0 else 2.5)
            t_sa_roof.append(t_sa_r)

            # Fachadas Nivel 1 y Nivel 2
            t_facades_1 = []
            t_facades_2 = []
            q_win_1 = 0.0
            q_win_2 = 0.0

            for f in facades:
                faz = SolarShadingCalculator.DIRECTION_AZIMUTHS.get(f, 0.0)
                adiff = abs(sol_azim - faz)
                if adiff > 180.0: adiff = 360.0 - adiff
                cos_inc = max(0.0, math.cos(math.radians(sol_elev)) * math.cos(math.radians(adiff))) if sol_elev > 0 else 0.0

                sh_1 = SolarShadingCalculator.calculate_facade_shading_factor(
                    facade_direction=f, level=1, level_height_m=self.zone_1.height_m,
                    solar_elevation_deg=sol_elev, solar_azimuth_deg=sol_azim, obstacles=self.obstacles
                )
                rad_f1 = (dif_rad * 0.5) + (dir_rad * (1.0 - sh_1) * cos_inc if sol_elev > 0 else 0.0)
                t_facades_1.append(t_ext + (wall_alpha_1 * rad_f1 / 20.0))
                q_win_1 += rad_f1 * shgc_val * wi_area_facade_1

                if self.zone_2:
                    sh_2 = SolarShadingCalculator.calculate_facade_shading_factor(
                        facade_direction=f, level=2, level_height_m=self.zone_1.height_m,
                        solar_elevation_deg=sol_elev, solar_azimuth_deg=sol_azim, obstacles=self.obstacles
                    )
                    rad_f2 = (dif_rad * 0.5) + (dir_rad * (1.0 - sh_2) * cos_inc if sol_elev > 0 else 0.0)
                    t_facades_2.append(t_ext + (wall_alpha_2 * rad_f2 / 20.0))
                    q_win_2 += rad_f2 * shgc_val * wi_area_facade_2

            t_sa_walls_1.append(sum(t_facades_1) / 4.0)
            q_sol_win_1_list.append(q_win_1)
            if self.zone_2:
                t_sa_walls_2.append(sum(t_facades_2) / 4.0)
                q_sol_win_2_list.append(q_win_2)

        # Temperaturas sol-aire medias de 24 horas
        mean_sa_roof = sum(t_sa_roof) / 24.0
        mean_sa_w1 = sum(t_sa_walls_1) / 24.0
        mean_sa_w2 = sum(t_sa_walls_2) / 24.0 if self.zone_2 else mean_sa_w1

        def _get_lagged(arr: list, h: int, phi: float) -> float:
            h_lag = (h - phi) % 24.0
            idx = int(h_lag)
            frac = h_lag - idx
            return arr[idx] * (1.0 - frac) + arr[(idx + 1) % 24] * frac

        # Temperaturas equivalentes amortiguadas y retardadas por inercia térmica
        t_eq_roof = [mean_sa_roof + f_roof * (_get_lagged(t_sa_roof, h, phi_roof) - mean_sa_roof) for h in range(24)]
        t_eq_w1 = [mean_sa_w1 + f_w1 * (_get_lagged(t_sa_walls_1, h, phi_w1) - mean_sa_w1) for h in range(24)]
        t_eq_w2 = [mean_sa_w2 + f_w2 * (_get_lagged(t_sa_walls_2, h, phi_w2) - mean_sa_w2) for h in range(24)] if self.zone_2 else t_eq_w1

        # Temperatura del terreno natural en subsuelo (estable todo el año)
        t_ground = (sum(s["t_ext"] for s in hourly_weather) / 24.0) - 2.0

        # Transmitancias U de envolventes
        u_wall_1 = self.zone_1.wall_material.u_value
        u_win_1 = self.zone_1.window_material.u_value
        u_roof = self.roof_assembly.u_value if self.roof_assembly else 1.5

        if self.zone_2:
            u_wall_2 = self.zone_2.wall_material.u_value
            u_win_2 = self.zone_2.window_material.u_value
            u_slab = self.slab_material.u_value if self.slab_material else 1.8
        else:
            u_wall_2 = u_win_2 = u_slab = 1.8

        # Condiciones iniciales de temperatura interior
        t_int_1 = sum(s["t_ext"] for s in hourly_weather) / 24.0
        t_int_2 = t_int_1

        results = []

        # Ejecutamos 3 ciclos para estabilizar plenamente la inercia térmica periódica
        for cycle in range(3):
            for step in hourly_weather:
                hour = step["hour"]
                t_ext = step["t_ext"]
                wind_spd = step["wind_speed"]

                teq_r = t_eq_roof[hour]
                teq_w1 = t_eq_w1[hour]
                teq_w2 = t_eq_w2[hour]
                q_sol_win_1 = q_sol_win_1_list[hour]
                q_sol_win_2 = q_sol_win_2_list[hour] if self.zone_2 else 0.0

                # -------------------------------------------------------------
                # GANANCIAS INTERNAS POR OCUPACIÓN Y EQUIPOS (ASHRAE Ch. 18)
                # -------------------------------------------------------------
                occ_factor = 1.0 if (8 <= hour <= 21) else 0.0
                heat_sensible_person = self.zone_1.occupant_heat_w * 0.65
                q_human_sensible_1 = self.zone_1.occupants * heat_sensible_person * occ_factor
                q_internal_1 = q_human_sensible_1 + (self.zone_1.equipment_w * (1.0 if (7 <= hour <= 22) else 0.15))

                if self.zone_2:
                    q_human_sensible_2 = self.zone_2.occupants * heat_sensible_person * occ_factor
                    q_internal_2 = q_human_sensible_2 + (self.zone_2.equipment_w * (1.0 if (7 <= hour <= 22) else 0.15))
                else:
                    q_internal_2 = 0.0

                # -------------------------------------------------------------
                # VENTILACIÓN E INFILTRACIÓN (EM.110 Art. 8 / ASHRAE 62.1)
                # -------------------------------------------------------------
                q_vent_m3_h_1 = 0.35 * self.zone_1.volume_m3
                if self.zone_1.occupants > 0 and occ_factor > 0:
                    q_vent_m3_h_1 += self.zone_1.occupants * 18.0
                open_area_1 = self.zone_1.window_area_m2 * min(0.50, max(0.0, self.zone_1.window_open_ratio))
                if open_area_1 > 0.0:
                    q_vent_m3_h_1 += 0.40 * open_area_1 * max(0.5, wind_spd) * 3600.0
                if self.zone_1.mechanical_vent.has_exhaust_fan or self.zone_1.mechanical_vent.has_supply_fan:
                    q_vent_m3_h_1 += self.zone_1.mechanical_vent.net_forced_flow_m3_h

                t_inlet_1 = t_ext
                if self.zone_1.mechanical_vent.has_supply_fan and self.zone_1.mechanical_vent.total_supply_flow_m3_h > 0:
                    sup_ratio_1 = min(1.0, self.zone_1.mechanical_vent.total_supply_flow_m3_h / max(1.0, q_vent_m3_h_1))
                    t_inlet_1 += self.zone_1.mechanical_vent.supply_temp_delta_c * sup_ratio_1
                m_dot_1 = (q_vent_m3_h_1 / 3600.0) * RHO_AIR

                # Extractores eólicos en cubierta
                eolic_reduction_factor = 1.0
                q_eolic_m3_h = 0.0
                if self.wind_turbine and self.wind_turbine.quantity > 0:
                    delta_t_eolic = max(0.5, (t_int_2 if self.zone_2 else t_int_1) - t_ext)
                    q_eolic_m3_h = self.wind_turbine.calculate_airflow_m3_h(
                        wind_speed_m_s=wind_spd, delta_t_c=delta_t_eolic,
                        height_m=self.zone_1.height_m * (2.0 if self.zone_2 else 1.0)
                    )
                    vol_ref = (self.zone_2.volume_m3 if self.zone_2 else self.zone_1.volume_m3)
                    eolic_reduction_factor = max(0.40, 1.0 - (q_eolic_m3_h / (vol_ref * 20.0)))

                if self.zone_2:
                    q_vent_m3_h_2 = 0.35 * self.zone_2.volume_m3 + q_eolic_m3_h
                    if self.zone_2.occupants > 0 and occ_factor > 0:
                        q_vent_m3_h_2 += self.zone_2.occupants * 18.0
                    open_area_2 = self.zone_2.window_area_m2 * min(0.50, max(0.0, self.zone_2.window_open_ratio))
                    if open_area_2 > 0.0:
                        q_vent_m3_h_2 += 0.40 * open_area_2 * max(0.5, wind_spd) * 3600.0
                    if self.zone_2.mechanical_vent.has_exhaust_fan or self.zone_2.mechanical_vent.has_supply_fan:
                        q_vent_m3_h_2 += self.zone_2.mechanical_vent.net_forced_flow_m3_h
                    t_inlet_2 = t_ext
                    if self.zone_2.mechanical_vent.has_supply_fan and self.zone_2.mechanical_vent.total_supply_flow_m3_h > 0:
                        sup_ratio_2 = min(1.0, self.zone_2.mechanical_vent.total_supply_flow_m3_h / max(1.0, q_vent_m3_h_2))
                        t_inlet_2 += self.zone_2.mechanical_vent.supply_temp_delta_c * sup_ratio_2
                    m_dot_2 = (q_vent_m3_h_2 / 3600.0) * RHO_AIR
                else:
                    q_vent_m3_h_1 += q_eolic_m3_h
                    m_dot_1 = (q_vent_m3_h_1 / 3600.0) * RHO_AIR

                # -------------------------------------------------------------
                # 3. AVANCE TEMPORAL FINO (SUB-PASOS DE 60 SEGUNDOS)
                # -------------------------------------------------------------
                sub_steps = 60
                dt_sub = 3600.0 / sub_steps

                if self.zone_2:
                    for _ in range(sub_steps):
                        q_cond_w1 = u_wall_1 * self.zone_1.net_wall_area_m2 * (teq_w1 - t_int_1)
                        q_cond_wi1 = u_win_1 * self.zone_1.window_area_m2 * (t_ext - t_int_1)
                        q_ground = 1.2 * self.zone_1.floor_area_m2 * (t_ground - t_int_1)
                        q_v1 = m_dot_1 * CP_AIR * (t_inlet_1 - t_int_1)

                        q_cond_w2 = u_wall_2 * self.zone_2.net_wall_area_m2 * (teq_w2 - t_int_2)
                        q_cond_wi2 = u_win_2 * self.zone_2.window_area_m2 * (t_ext - t_int_2)
                        q_cond_r2 = u_roof * self.zone_2.floor_area_m2 * (teq_r - t_int_2) * eolic_reduction_factor
                        q_v2 = m_dot_2 * CP_AIR * (t_inlet_2 - t_int_2)

                        q_slab = u_slab * self.zone_1.floor_area_m2 * (t_int_1 - t_int_2)

                        q_net_1 = q_cond_w1 + q_cond_wi1 + q_ground + q_v1 + q_sol_win_1 + q_internal_1 - q_slab
                        q_net_2 = q_cond_w2 + q_cond_wi2 + q_cond_r2 + q_v2 + q_sol_win_2 + q_internal_2 + q_slab

                        # A/C Nivel 1
                        if self.zone_1.ac_system.enabled and t_int_1 > self.zone_1.ac_system.target_temperature_c:
                            if self.zone_1.ac_system.is_auto_capacity:
                                t_int_1 = self.zone_1.ac_system.target_temperature_c
                            else:
                                max_cool_w_1 = self.zone_1.ac_system.total_nominal_cooling_w
                                q_cool_needed_1 = max(0.0, q_net_1 + (self.zone_1.thermal_capacitance_j_k * (t_int_1 - self.zone_1.ac_system.target_temperature_c) / dt_sub))
                                q_del_1 = min(q_cool_needed_1, max_cool_w_1)
                                t_int_1 = max(self.zone_1.ac_system.target_temperature_c, t_int_1 + ((q_net_1 - q_del_1) * dt_sub) / self.zone_1.thermal_capacitance_j_k)
                        else:
                            t_int_1 += (q_net_1 * dt_sub) / self.zone_1.thermal_capacitance_j_k

                        # A/C Nivel 2
                        if self.zone_2.ac_system.enabled and t_int_2 > self.zone_2.ac_system.target_temperature_c:
                            if self.zone_2.ac_system.is_auto_capacity:
                                t_int_2 = self.zone_2.ac_system.target_temperature_c
                            else:
                                max_cool_w_2 = self.zone_2.ac_system.total_nominal_cooling_w
                                q_cool_needed_2 = max(0.0, q_net_2 + (self.zone_2.thermal_capacitance_j_k * (t_int_2 - self.zone_2.ac_system.target_temperature_c) / dt_sub))
                                q_del_2 = min(q_cool_needed_2, max_cool_w_2)
                                t_int_2 = max(self.zone_2.ac_system.target_temperature_c, t_int_2 + ((q_net_2 - q_del_2) * dt_sub) / self.zone_2.thermal_capacitance_j_k)
                        else:
                            t_int_2 += (q_net_2 * dt_sub) / self.zone_2.thermal_capacitance_j_k

                    # Demanda frigorífica ASHRAE exacta a la temperatura de consigna (setpoint)
                    sp_1 = self.zone_1.ac_system.target_temperature_c
                    q_demand_1 = max(0.0,
                        u_wall_1 * self.zone_1.net_wall_area_m2 * (teq_w1 - sp_1) +
                        u_win_1 * self.zone_1.window_area_m2 * (t_ext - sp_1) +
                        1.2 * self.zone_1.floor_area_m2 * (t_ground - sp_1) +
                        m_dot_1 * CP_AIR * (t_inlet_1 - sp_1) +
                        q_sol_win_1 + q_internal_1
                    )
                    ac_data_1 = self.zone_1.ac_system.calculate_cooling_power_required(q_demand_1)

                    sp_2 = self.zone_2.ac_system.target_temperature_c
                    q_demand_2 = max(0.0,
                        u_wall_2 * self.zone_2.net_wall_area_m2 * (teq_w2 - sp_2) +
                        u_win_2 * self.zone_2.window_area_m2 * (t_ext - sp_2) +
                        u_roof * self.zone_2.floor_area_m2 * (teq_r - sp_2) * eolic_reduction_factor +
                        m_dot_2 * CP_AIR * (t_inlet_2 - sp_2) +
                        q_sol_win_2 + q_internal_2
                    )
                    ac_data_2 = self.zone_2.ac_system.calculate_cooling_power_required(q_demand_2)

                else:
                    # Edificación de 1 solo piso: el techo actúa directamente sobre Nivel 1
                    for _ in range(sub_steps):
                        q_cond_w1 = u_wall_1 * self.zone_1.net_wall_area_m2 * (teq_w1 - t_int_1)
                        q_cond_wi1 = u_win_1 * self.zone_1.window_area_m2 * (t_ext - t_int_1)
                        q_cond_r1 = u_roof * self.zone_1.floor_area_m2 * (teq_r - t_int_1) * eolic_reduction_factor
                        q_ground = 1.2 * self.zone_1.floor_area_m2 * (t_ground - t_int_1)
                        q_v1 = m_dot_1 * CP_AIR * (t_inlet_1 - t_int_1)

                        q_net_1 = q_cond_w1 + q_cond_wi1 + q_cond_r1 + q_ground + q_v1 + q_sol_win_1 + q_internal_1

                        if self.zone_1.ac_system.enabled and t_int_1 > self.zone_1.ac_system.target_temperature_c:
                            if self.zone_1.ac_system.is_auto_capacity:
                                t_int_1 = self.zone_1.ac_system.target_temperature_c
                            else:
                                max_cool_w_1 = self.zone_1.ac_system.total_nominal_cooling_w
                                q_cool_needed_1 = max(0.0, q_net_1 + (self.zone_1.thermal_capacitance_j_k * (t_int_1 - self.zone_1.ac_system.target_temperature_c) / dt_sub))
                                q_del_1 = min(q_cool_needed_1, max_cool_w_1)
                                t_int_1 = max(self.zone_1.ac_system.target_temperature_c, t_int_1 + ((q_net_1 - q_del_1) * dt_sub) / self.zone_1.thermal_capacitance_j_k)
                        else:
                            t_int_1 += (q_net_1 * dt_sub) / self.zone_1.thermal_capacitance_j_k

                    sp_1 = self.zone_1.ac_system.target_temperature_c
                    q_demand_1 = max(0.0,
                        u_wall_1 * self.zone_1.net_wall_area_m2 * (teq_w1 - sp_1) +
                        u_win_1 * self.zone_1.window_area_m2 * (t_ext - sp_1) +
                        u_roof * self.zone_1.floor_area_m2 * (teq_r - sp_1) * eolic_reduction_factor +
                        1.2 * self.zone_1.floor_area_m2 * (t_ground - sp_1) +
                        m_dot_1 * CP_AIR * (t_inlet_1 - sp_1) +
                        q_sol_win_1 + q_internal_1
                    )
                    ac_data_1 = self.zone_1.ac_system.calculate_cooling_power_required(q_demand_1)
                    t_int_2 = t_int_1
                    ac_data_2 = {"active": False, "cooling_btu_h": 0.0, "electrical_power_kw": 0.0}

                # Ajuste de confort adaptativo por ventilador de techo (sensación percibida)
                apparent_t_1 = t_int_1 - self.zone_1.comfort_fan.apparent_temperature_reduction_c
                apparent_t_2 = t_int_2 - (self.zone_2.comfort_fan.apparent_temperature_reduction_c if self.zone_2 else 0.0)

                # Cálculo de Confort Medio Predicho (CMP / PMV - ISO 7730 / ASHRAE 55) y PPD
                vel_1 = self.zone_1.comfort_fan.air_speed_m_s if self.zone_1.comfort_fan.enabled else 0.20
                vel_2 = (self.zone_2.comfort_fan.air_speed_m_s if self.zone_2 and self.zone_2.comfort_fan.enabled else 0.20)
                rh = getattr(self.climate, "humidity_percent", 55.0) if self.climate else 55.0
                clo_val = 0.50 if season == "summer" else 0.90
                met_val = 1.0 if self.zone_1.occupant_heat_w <= 100 else 1.2

                cmp_1 = ComfortCMPCalculator.calculate_cmp_ppd(
                    ta=apparent_t_1,
                    tr=(apparent_t_1 + t_ext) / 2.0,
                    vel=vel_1,
                    rh=rh,
                    met=met_val,
                    clo=clo_val
                )
                cmp_2 = ComfortCMPCalculator.calculate_cmp_ppd(
                    ta=apparent_t_2,
                    tr=(apparent_t_2 + t_ext) / 2.0,
                    vel=vel_2,
                    rh=rh,
                    met=met_val,
                    clo=clo_val
                ) if self.zone_2 else cmp_1

                # Guardamos únicamente en el 3° ciclo cuando la periodicidad diaria está en equilibrio exacto
                if cycle == 2:
                    direct_rad_h = step["direct_radiation"]
                    diffuse_rad_h = step["diffuse_radiation"]
                    results.append({
                        "hour": hour,
                        "t_ext": round(t_ext, 1),
                        "t_int_level_1": round(t_int_1, 1),
                        "t_apparent_level_1": round(apparent_t_1, 1),
                        "t_int_level_2": round(t_int_2, 1) if self.zone_2 else round(t_int_1, 1),
                        "t_apparent_level_2": round(apparent_t_2, 1) if self.zone_2 else round(apparent_t_1, 1),
                        "solar_radiation": round(direct_rad_h + diffuse_rad_h, 1),
                        "solar_elevation": step["solar_elevation"],
                        "solar_azimuth": (step["solar_azimuth"] + self.north_orientation_deg) % 360.0,
                        "t_sol_air_roof": round(t_sa_roof[hour], 1),
                        "t_sol_air_walls": round(t_sa_walls_1[hour], 1),
                        "t_eq_roof": round(teq_r, 1),
                        "t_eq_walls": round(teq_w1, 1),
                        "phi_wall_hours": round(phi_w1, 1),
                        "f_wall_decrement": round(f_w1, 2),
                        "phi_roof_hours": round(phi_roof, 1),
                        "f_roof_decrement": round(f_roof, 2),
                        "ac_btu_h_1": ac_data_1.get("cooling_btu_h", 0.0),
                        "ac_btu_h_2": ac_data_2.get("cooling_btu_h", 0.0) if self.zone_2 else 0.0,
                        "ac_nominal_btu_1": ac_data_1.get("nominal_btu_h", 0.0),
                        "ac_demand_btu_1": ac_data_1.get("demand_btu_h", 0.0),
                        "ac_deficit_btu_1": ac_data_1.get("deficit_btu_h", 0.0),
                        "ac_is_sufficient_1": ac_data_1.get("is_sufficient", True),
                        "ac_kw_1": ac_data_1.get("electrical_power_kw", 0.0),
                        "ac_kw_2": ac_data_2.get("electrical_power_kw", 0.0) if self.zone_2 else 0.0,
                        "cmp_level_1": cmp_1.cmp_value,
                        "ppd_level_1": cmp_1.ppd_percent,
                        "cmp_sensation_1": cmp_1.sensation_text,
                        "cmp_compliance_1": cmp_1.compliance_em110,
                        "cmp_level_2": cmp_2.cmp_value,
                        "ppd_level_2": cmp_2.ppd_percent,
                        "cmp_sensation_2": cmp_2.sensation_text,
                        "cmp_compliance_2": cmp_2.compliance_em110,
                    })

        return results
