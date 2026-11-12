"""
Módulo Climático y Solar para Perú.
Cálculo de trayectoria solar (azimut, elevación cenital) hora a hora,
radiación solar directa y difusa, perfiles de temperatura y viento para ciudades peruanas.
Soporte para "Clima Personalizado".
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class PeruCityClimate:
    """Perfil meteorológico y geográfico de una ciudad del Perú."""
    name: str
    region: str  # 'Costa', 'Sierra', 'Selva'
    latitude: float   # Grados (negativo en hemisferio sur)
    longitude: float  # Grados (negativo al oeste de Greenwich)
    altitude_m: float
    summer_t_max: float  # °C
    summer_t_min: float  # °C
    winter_t_max: float  # °C
    winter_t_min: float  # °C
    peak_solar_radiation_w_m2: float  # W/m² en plano horizontal despejado
    avg_wind_speed_m_s: float          # m/s
    humidity_percent: float            # %
    description: str = ""


# Catálogo oficial de ciudades del Perú representativas
PERU_CITIES: Dict[str, PeruCityClimate] = {
    "Lima (Costa Central)": PeruCityClimate(
        name="Lima (Costa Central)",
        region="Costa",
        latitude=-12.0464,
        longitude=-77.0428,
        altitude_m=150.0,
        summer_t_max=29.5,
        summer_t_min=20.5,
        winter_t_max=19.0,
        winter_t_min=14.0,
        peak_solar_radiation_w_m2=880.0,
        avg_wind_speed_m_s=3.2,
        humidity_percent=82.0,
        description="Clima templado-cálido desértico con alta nubosidad y humedad marina en invierno."
    ),
    "Piura (Costa Norte - Cálido Extremo)": PeruCityClimate(
        name="Piura (Costa Norte - Cálido Extremo)",
        region="Costa",
        latitude=-5.1945,
        longitude=-80.6328,
        altitude_m=35.0,
        summer_t_max=36.5,
        summer_t_min=23.0,
        winter_t_max=28.0,
        winter_t_min=18.0,
        peak_solar_radiation_w_m2=1020.0,
        avg_wind_speed_m_s=3.8,
        humidity_percent=60.0,
        description="Clima cálido seco desértico con altísima insolación y veranos sofocantes."
    ),
    "Ica (Costa Sur Cálida)": PeruCityClimate(
        name="Ica (Costa Sur Cálida)",
        region="Costa",
        latitude=-14.0678,
        longitude=-75.7286,
        altitude_m=406.0,
        summer_t_max=34.0,
        summer_t_min=18.5,
        winter_t_max=25.0,
        winter_t_min=10.0,
        peak_solar_radiation_w_m2=990.0,
        avg_wind_speed_m_s=4.0,
        humidity_percent=55.0,
        description="Clima muy soleado con vientos regulares (paracas) y gran calor diurno."
    ),
    "Arequipa (Sierra Sur)": PeruCityClimate(
        name="Arequipa (Sierra Sur)",
        region="Sierra",
        latitude=-16.4090,
        longitude=-71.5375,
        altitude_m=2335.0,
        summer_t_max=25.0,
        summer_t_min=11.0,
        winter_t_max=23.0,
        winter_t_min=5.5,
        peak_solar_radiation_w_m2=1050.0,
        avg_wind_speed_m_s=3.5,
        humidity_percent=45.0,
        description="Cielo despejado casi todo el año, radiación UV extrema y alta oscilación térmica día/noche."
    ),
    "Cusco (Sierra Andina)": PeruCityClimate(
        name="Cusco (Sierra Andina)",
        region="Sierra",
        latitude=-13.5319,
        longitude=-71.9675,
        altitude_m=3399.0,
        summer_t_max=21.5,
        summer_t_min=8.0,
        winter_t_max=20.0,
        winter_t_min=0.5,
        peak_solar_radiation_w_m2=1080.0,
        avg_wind_speed_m_s=2.8,
        humidity_percent=52.0,
        description="Gran radiación solar al mediodía y frío seco marcado en madrugadas e invierno."
    ),
    "Huancayo (Sierra Central)": PeruCityClimate(
        name="Huancayo (Sierra Central)",
        region="Sierra",
        latitude=-12.0651,
        longitude=-75.2049,
        altitude_m=3271.0,
        summer_t_max=22.0,
        summer_t_min=7.0,
        winter_t_max=19.5,
        winter_t_min=1.0,
        peak_solar_radiation_w_m2=1060.0,
        avg_wind_speed_m_s=2.6,
        humidity_percent=55.0,
        description="Valle interandino con marcadas heladas nocturnas y días de fuerte radiación."
    ),
    "Puno (Altiplano Frío)": PeruCityClimate(
        name="Puno (Altiplano Frío)",
        region="Sierra",
        latitude=-15.8422,
        longitude=-70.0199,
        altitude_m=3827.0,
        summer_t_max=16.5,
        summer_t_min=4.0,
        winter_t_max=15.0,
        winter_t_min=-4.0,
        peak_solar_radiation_w_m2=1100.0,
        avg_wind_speed_m_s=3.6,
        humidity_percent=50.0,
        description="Altiplano frío, vientos constantes del Titicaca y requerimiento de ganancia solar pasiva."
    ),
    "Iquitos (Selva Tropical Húmeda)": PeruCityClimate(
        name="Iquitos (Selva Tropical Húmeda)",
        region="Selva",
        latitude=-3.7437,
        longitude=-73.2516,
        altitude_m=106.0,
        summer_t_max=33.5,
        summer_t_min=23.5,
        winter_t_max=31.5,
        winter_t_min=22.0,
        peak_solar_radiation_w_m2=920.0,
        avg_wind_speed_m_s=2.0,
        humidity_percent=88.0,
        description="Clima ecuatorial cálido húmedo todo el año. La ventilación cruzada y de techos es crítica."
    ),
    "Tarapoto (Selva Alta Cálida)": PeruCityClimate(
        name="Tarapoto (Selva Alta Cálida)",
        region="Selva",
        latitude=-6.4862,
        longitude=-76.3686,
        altitude_m=333.0,
        summer_t_max=35.0,
        summer_t_min=22.5,
        winter_t_max=32.0,
        winter_t_min=20.5,
        peak_solar_radiation_w_m2=950.0,
        avg_wind_speed_m_s=2.2,
        humidity_percent=78.0,
        description="Altas temperaturas sostenidas y fuerte radiación solar en techos."
    ),
}


class SolarEngine:
    """Motor de cálculo de posición solar y radiación horaria."""

    @staticmethod
    def calculate_solar_position(latitude_deg: float, day_of_year: int, hour_float: float) -> Tuple[float, float]:
        """
        Calcula la elevación solar (grados sobre el horizonte) y el azimut solar (grados desde el Norte, sentido horario).
        hour_float: Hora solar decimal (ej. 13.5 = 13:30)
        Retorna (elevation_deg, azimuth_deg).
        """
        lat_rad = math.radians(latitude_deg)

        # Declinación solar (fórmula de Cooper)
        delta_deg = 23.45 * math.sin(math.radians((360.0 / 365.0) * (284 + day_of_year)))
        delta_rad = math.radians(delta_deg)

        # Ángulo horario solar (H = 15° por hora antes/después del mediodía solar a las 12:00)
        h_deg = (hour_float - 12.0) * 15.0
        h_rad = math.radians(h_deg)

        # Seno de la elevación (altitud solar)
        sin_elev = math.sin(lat_rad) * math.sin(delta_rad) + math.cos(lat_rad) * math.cos(delta_rad) * math.cos(h_rad)
        sin_elev = max(-1.0, min(1.0, sin_elev))
        elevation_rad = math.asin(sin_elev)
        elevation_deg = math.degrees(elevation_rad)

        if elevation_deg <= 0.0:
            return 0.0, 0.0  # El sol está bajo el horizonte (noche)

        # Coseno del azimut
        cos_azimuth = (math.sin(delta_rad) - math.sin(lat_rad) * math.sin(elevation_rad)) / (
            math.cos(lat_rad) * math.cos(elevation_rad) + 1e-6
        )
        cos_azimuth = max(-1.0, min(1.0, cos_azimuth))
        azimuth_rad = math.acos(cos_azimuth)
        azimuth_deg = math.degrees(azimuth_rad)

        # Ajuste de cuadrante (mañana vs tarde)
        if math.sin(h_rad) > 0:
            azimuth_deg = 360.0 - azimuth_deg

        return elevation_deg, azimuth_deg

    @staticmethod
    def get_hourly_profile(climate: PeruCityClimate, season: str = "summer") -> List[Dict]:
        """
        Genera el perfil horario (00:00 a 23:00) de temperatura exterior, radiación solar y viento.
        """
        t_max = climate.summer_t_max if season == "summer" else climate.winter_t_max
        t_min = climate.summer_t_min if season == "summer" else climate.winter_t_min
        day_of_year = 15 if season == "summer" else 196  # Enero vs Julio

        profile = []
        for hour in range(24):
            # Perfil sinusoidal de temperatura con mínimo a las 06:00 y máximo a las 15:00
            hour_angle = (hour - 6.0) / 18.0 * math.pi
            if 6 <= hour <= 15:
                t_ext = t_min + (t_max - t_min) * math.sin((hour - 6.0) / 9.0 * (math.pi / 2.0))
            elif hour > 15:
                t_ext = t_min + (t_max - t_min) * math.cos((hour - 15.0) / 15.0 * (math.pi / 2.0))
            else:
                t_ext = t_min + (t_max - t_min) * 0.1 * math.cos(hour / 6.0 * (math.pi / 2.0))

            elev, azim = SolarEngine.calculate_solar_position(climate.latitude, day_of_year, float(hour))

            # Radiación incidente en plano horizontal
            if elev > 0:
                rad_factor = math.sin(math.radians(elev))
                solar_rad = climate.peak_solar_radiation_w_m2 * (rad_factor ** 1.1)
                direct_rad = solar_rad * 0.85
                diffuse_rad = solar_rad * 0.15
            else:
                solar_rad = 0.0
                direct_rad = 0.0
                diffuse_rad = 0.0

            # Viento suele ser menor en la madrugada y mayor en la tarde
            wind_factor = 0.7 if (hour < 8 or hour > 20) else 1.25
            wind_speed = climate.avg_wind_speed_m_s * wind_factor

            profile.append({
                "hour": hour,
                "t_ext": round(t_ext, 1),
                "solar_elevation": round(elev, 1),
                "solar_azimuth": round(azim, 1),
                "total_radiation": round(solar_rad, 1),
                "direct_radiation": round(direct_rad, 1),
                "diffuse_radiation": round(diffuse_rad, 1),
                "wind_speed": round(wind_speed, 1),
            })

        return profile
