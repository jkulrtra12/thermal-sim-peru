"""
Paquete core del simulador térmico bioclimático.
"""
from core.materials import (
    Material,
    PREDEFINED_ROOFS,
    PREDEFINED_CEILINGS,
    PREDEFINED_WALLS,
    PREDEFINED_WINDOWS,
    create_custom_material,
)
from core.assemblies import RoofCeilingAssembly, WallAssembly
from core.climate import PeruCityClimate, PERU_CITIES, SolarEngine
from core.ventilation import (
    WindTurbineVentilator,
    MechanicalVentilation,
    CeilingComfortFan,
    AirConditioningSystem,
)
from core.solar_shading import NeighborObstacle, SolarShadingCalculator
from core.thermal_engine import ThermalZoneConfig, MultiLevelThermalSimulator
from core.compliance_em110 import EM110Evaluator, BIOCLIMATIC_ZONES_EM110
from core.reports import ThermalReportGenerator
from core.calculation_memory import CalculationMemoryGenerator
from core.comfort_cmp import ComfortCMPCalculator, CMPResult
