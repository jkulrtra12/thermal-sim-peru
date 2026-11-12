# 🌡️ ThermalSim Peru | 3D Bioclimatic Building Simulation & SketchUp Plugin

A dynamic 3D building thermal simulation and bioclimatic performance engine with integrated **Trimble SketchUp** plugin (`.rbz`), developed in accordance with the Peruvian National Building Code (**Norma Técnica EM.110 Confort Térmico y Lumínico con Eficiencia Energética**).

---

## ✨ Key Features

- **3D Thermal & Shadow Engine:**
  - Hour-by-hour solar position calculation and shadow projection from neighboring structures.
  - Multi-zone and multi-level envelope heat transmission (walls, roofs, glass fenestrations, intermediate slabs).
- **Floor Heatmap Simulation (2D / 3D):**
  - Continuous floor temperature gradient mapping showing warm spots near sunlit windows and cool dispersion zones around AC units and fans.
  - Interactive temperature probes (`Min`, `Average`, `Max`).
- **HVAC & Bioclimatic Systems:**
  - Split AC units with spatial (X, Y, Z) positioning on interior/exterior walls.
  - Ceiling circulation fans and rooftop wind turbine extractors.
  - Natural cross-ventilation modeling with configurable door and window opening percentages (0% to 50%).
- **Automated Technical Reports & EM.110 Compliance:**
  - One-click HTML / PDF technical memory generation with heat balance breakdown, hourly comfort curves, and official EM.110 compliance verification.
- **SketchUp Integration (`thermal_exporter.rbz`):**
  - Direct 3D geometry exporter plugin for SketchUp to transfer architectural volumes and surface properties to the simulation engine.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.9+** (for source execution)
- **Windows 64-bit**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/jkulrtra12/thermal-sim-peru.git
cd thermal-sim-peru

# 2. Run the application
python main.py
```

Or execute directly using `iniciar_app.bat`.

---

## 📐 SketchUp Plugin Installation

1. In Trimble SketchUp, go to: `Extensions > Extension Manager > Install Extension...`
2. Select the `thermal_exporter.rbz` package.
3. Access the exporter from: `Extensions > Export to Thermal Simulator (.json)...`

---

## 🛠️ Architecture

- **`core/`**: Thermodynamic solver, solar angles, heat balance, and hourly climate models.
- **`geometry/`**: 3D geometric transformations, polygon mesh processing, and shadow projection.
- **`ui/`**: 3D OpenGL viewport, controls, building inspector, and thermal heatmap visualizer.
- **`sketchup_plugin/`**: Ruby extension for SketchUp export.
