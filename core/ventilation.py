"""
Módulo de Ventilación Mecánica, Extractores Eólicos, Ventiladores de Confort y A/C.
Calcula caudales de aire (m³/h), renovaciones por hora (ACH) y balances de calor transportado.
"""

import math
from dataclasses import dataclass
from typing import Optional


# Densidad del aire estándar y calor específico (a nivel de mar / 25°C)
RHO_AIR = 1.204   # kg/m³
CP_AIR = 1005.0   # J/kg·K (0.28 W·h/kg·K)


@dataclass
class WindTurbineVentilator:
    """Extractor Eólico de Cubierta (Turbina Giratoria por viento y tiro térmico)."""
    name: str = "Extractor Eólico 24\""
    enabled: bool = True
    throat_diameter_inches: float = 24.0  # Diámetro de garganta (14", 20", 24", 30")
    quantity: int = 1
    discharge_coefficient: float = 0.65

    @property
    def throat_area_m2(self) -> float:
        """Área de paso por extractor en m²."""
        diameter_m = self.throat_diameter_inches * 0.0254
        return math.pi * ((diameter_m / 2.0) ** 2)

    def calculate_airflow_m3_h(self, wind_speed_m_s: float, delta_t_c: float, height_m: float = 3.5) -> float:
        """
        Calcula el caudal de extracción en m³/h combinando:
        1. Acción del viento sobre la turbina (Efecto Bernoulli).
        2. Tiro térmico (Stack effect / flotabilidad por delta T interior-exterior).
        """
        if not self.enabled or self.quantity <= 0:
            return 0.0

        # Flujo por viento: Q_viento = A * C_d * v_viento
        q_wind = self.throat_area_m2 * self.discharge_coefficient * wind_speed_m_s

        # Flujo por tiro térmico: Q_term = A * C_d * sqrt(2 * g * h * delta_T / T_prom)
        delta_t_safe = max(0.1, delta_t_c)
        t_avg_k = 298.15
        g = 9.81
        q_thermal = self.throat_area_m2 * 0.45 * math.sqrt(2 * g * height_m * (delta_t_safe / t_avg_k))

        # Flujo total combinado en cuadratura (estándar ASHRAE Handbook of Fundamentals)
        q_total_m3_s = math.sqrt((q_wind ** 2) + (q_thermal ** 2))
        q_total_m3_h = q_total_m3_s * 3600.0 * self.quantity

        return max(150.0 * self.quantity, q_total_m3_h)


@dataclass
class MechanicalVentilation:
    """Sistemas de ventilación mecánica forzada (Extractores e Inyectores)."""
    # Extracción
    has_exhaust_fan: bool = False
    exhaust_flow_m3_h: float = 1200.0  # Caudal por extractor (m³/h)
    exhaust_quantity: int = 1          # Cantidad de extractores

    # Inyección / Incorporador de aire
    has_supply_fan: bool = False
    supply_flow_m3_h: float = 1200.0   # Caudal por inyector (m³/h)
    supply_quantity: int = 1           # Cantidad de inyectores
    supply_temp_delta_c: float = 0.0   # Alivio por toma de aire en sombra (-2.5°C, -3.5°C, -5.0°C)

    @property
    def total_exhaust_flow_m3_h(self) -> float:
        return (self.exhaust_flow_m3_h * self.exhaust_quantity) if self.has_exhaust_fan else 0.0

    @property
    def total_supply_flow_m3_h(self) -> float:
        return (self.supply_flow_m3_h * self.supply_quantity) if self.has_supply_fan else 0.0

    @property
    def net_forced_flow_m3_h(self) -> float:
        """Caudal efectivo de renovación mecánica."""
        return max(self.total_exhaust_flow_m3_h, self.total_supply_flow_m3_h)


@dataclass
class CeilingComfortFan:
    """Ventiladores interiores de confort (Techo, Pared Alta o Pedestal - ASHRAE 55)."""
    enabled: bool = False
    quantity: int = 1
    mount_type: str = "techo"          # 'techo', 'pared_alta', 'pedestal'
    fan_speed: str = "media"           # 'baja', 'media', 'alta', 'industrial', 'personalizado'
    air_speed_m_s: float = 0.8         # Velocidad del aire sobre ocupantes (m/s)
    motor_power_w: float = 75.0        # Potencia eléctrica del motor (Watts)
    airflow_m3_h: float = 4500.0       # Caudal de aire nominal

    def __post_init__(self):
        if self.fan_speed == "baja":
            self.air_speed_m_s = 0.5
            self.motor_power_w = 45.0
        elif self.fan_speed == "media":
            self.air_speed_m_s = 1.0
            self.motor_power_w = 75.0
        elif self.fan_speed == "alta":
            self.air_speed_m_s = 1.8
            self.motor_power_w = 120.0
        elif self.fan_speed == "industrial":
            self.air_speed_m_s = 2.4
            self.motor_power_w = 180.0

    @property
    def apparent_temperature_reduction_c(self) -> float:
        """
        Enfriamiento fisiológico percibido en °C según ASHRAE 55 (Cooling Effect of Air Movement).
        - Techo: Cono descendente directo sobre cabeza/torso (eficiencia 100%).
        - Pared Alta: Chorro longitudinal direccional con alcance (eficiencia 88% por distancia).
        - Pedestal: Brisa horizontal directa (eficiencia 95%).
        """
        if not self.enabled or self.quantity <= 0 or self.air_speed_m_s <= 0.15:
            return 0.0
        dt = 1.25 * math.log(1.0 + (self.air_speed_m_s / 0.15))
        eff = 1.0 if self.mount_type == "techo" else (0.88 if self.mount_type == "pared_alta" else 0.95)
        coverage_boost = min(1.40, 1.0 + 0.10 * (self.quantity - 1))
        return min(4.8, max(0.4, dt * eff * coverage_boost))


@dataclass
class AirConditioningSystem:
    """Sistema de Aire Acondicionado (A/C) con capacidad nominal real de fabricante o auto-dimensionamiento."""
    enabled: bool = False
    quantity: int = 1
    target_temperature_c: float = 24.0      # Setpoint deseado
    cop_efficiency: float = 3.2              # Coeficiente de rendimiento energético (COP / EER)
    is_auto_capacity: bool = False          # False = Capacidad nominal fija, True = Auto-dimensionamiento
    nominal_cooling_btu_h: float = 24000.0  # Capacidad nominal por unidad (BTU/h)

    @property
    def total_nominal_btu_h(self) -> float:
        """Capacidad frigorífica nominal total instalada (BTU/h)."""
        return (self.nominal_cooling_btu_h * self.quantity) if self.enabled else 0.0

    @property
    def total_nominal_cooling_w(self) -> float:
        """Capacidad frigorífica nominal total en Watts (1 W = 3.41214 BTU/h)."""
        return self.total_nominal_btu_h / 3.41214

    def calculate_cooling_power_required(self, heat_load_watts: float) -> dict:
        """
        Calcula la potencia frigorífica requerida y el balance real frente a la capacidad instalada.
        """
        if not self.enabled or heat_load_watts <= 0.0 or self.quantity <= 0:
            return {
                "active": False,
                "thermal_power_w": 0.0,
                "cooling_btu_h": 0.0,
                "cooling_ton_ref": 0.0,
                "electrical_power_kw": 0.0,
                "nominal_btu_h": 0.0,
                "demand_btu_h": 0.0,
                "deficit_btu_h": 0.0,
                "is_sufficient": True,
            }

        # 1 Watt = 3.41214 BTU/h
        demand_btu_h = heat_load_watts * 3.41214
        cap_btu_h = self.total_nominal_btu_h

        if self.is_auto_capacity:
            delivered_btu_h = demand_btu_h
            delivered_w = heat_load_watts
            deficit_btu = 0.0
            is_suff = True
        else:
            delivered_btu_h = min(demand_btu_h, cap_btu_h)
            delivered_w = delivered_btu_h / 3.41214
            deficit_btu = max(0.0, demand_btu_h - cap_btu_h)
            is_suff = deficit_btu <= 500.0

        elec_kw = (delivered_w / self.cop_efficiency) / 1000.0

        return {
            "active": True,
            "thermal_power_w": round(delivered_w, 1),
            "cooling_btu_h": round(delivered_btu_h, 0),
            "cooling_ton_ref": round(delivered_btu_h / 12000.0, 2),
            "electrical_power_kw": round(elec_kw, 2),
            "nominal_btu_h": round(cap_btu_h, 0),
            "demand_btu_h": round(demand_btu_h, 0),
            "deficit_btu_h": round(deficit_btu, 0),
            "is_sufficient": is_suff,
        }
