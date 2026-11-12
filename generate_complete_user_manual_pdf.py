# -*- coding: utf-8 -*-
"""
Generador del Manual de Operación y Usuario Oficial en PDF para el
Simulador Térmico Bioclimático Perú (RNE EM.110 / A.010 / ASHRAE 55 / ISO 13790).

Documento exhaustivo paso a paso: ingreso de datos, importación 3D, inspector de planos,
inserción de ventanas, configuración de materiales, climatización/ventilación multi-aparato,
mapa térmico 2D/3D y exportación de memorias de cálculo.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas que dibuja encabezados y numeración 'Página X de Y' en dos pasadas."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Portada sin encabezado ni pie

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Encabezado superior
        self.drawString(54, letter[1] - 36, "MANUAL DE OPERACIÓN Y USUARIO — SIMULADOR TÉRMICO BIOCLIMÁTICO PERÚ")
        self.setFont("Helvetica", 8)
        self.drawRightString(letter[0] - 54, letter[1] - 36, "RNE EM.110 / A.010 / ASHRAE 55")
        
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Pie de página
        self.line(54, 44, letter[0] - 54, 44)
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Guía Paso a Paso de Interfaz y Modelado • Versión 2.5 Standalone")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_text)
        self.restoreState()


def generate_manual_pdf(filename="Manual_de_Usuario_Simulador_Termico_Peru.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Paleta Corporativa / Técnica
    C_PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    C_SECONDARY = colors.HexColor("#1E3A8A")  # Blue 900
    C_ACCENT = colors.HexColor("#0284C7")     # Sky 600
    C_TEXT = colors.HexColor("#1E293B")       # Slate 800
    C_MUTED = colors.HexColor("#64748B")      # Slate 500
    C_LIGHT_BG = colors.HexColor("#F8FAFC")   # Slate 50
    C_BORDER = colors.HexColor("#E2E8F0")     # Slate 200
    C_SUCCESS_BG = colors.HexColor("#ECFDF5") # Emerald 50
    C_SUCCESS_BORDER = colors.HexColor("#059669")
    C_WARN_BG = colors.HexColor("#FEF3C7")    # Amber 50
    C_WARN_BORDER = colors.HexColor("#D97706")
    C_INFO_BG = colors.HexColor("#EFF6FF")    # Blue 50
    C_INFO_BORDER = colors.HexColor("#3B82F6")

    # Estilos de Párrafo
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=29,
        textColor=C_PRIMARY,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=C_ACCENT,
        spaceAfter=16
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=C_PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=C_SECONDARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=C_TEXT,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    step_num_style = ParagraphStyle(
        'StepNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=C_SECONDARY
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=C_TEXT
    )

    td_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=C_PRIMARY
    )

    story = []

    # =========================================================================
    # PORTADA
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("MANUAL DE OPERACIÓN Y GUÍA DE USUARIO", title_style))
    story.append(Paragraph("Simulador Térmico Bioclimático del Perú — Versión 2.5 Standalone", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2.5, color=C_ACCENT, spaceBefore=0, spaceAfter=14))

    box_summary = [
        [
            Paragraph(
                "<b>OBJETIVO DE ESTA GUÍA:</b><br/>"
                "Proporcionar una explicación paso a paso y detallada sobre la operación completa del software: "
                "cómo ingresar datos geométricos y climáticos, cómo importar modelos 3D desde SketchUp, "
                "el funcionamiento y propósito de cada pestaña de la interfaz, cómo añadir y reclasificar muros, "
                "techos y vanos de ventanas, la gestión multi-aparato de ventilación y climatización HVAC "
                "(activar, desactivar, regular caudales y potencias), y la interpretación de los mapas térmicos 2D/3D "
                "junto con la exportación formal de la Memoria de Cálculo según la <b>Norma RNE EM.110</b>.",
                body_style
            )
        ]
    ]
    t_box_sum = Table(box_summary, colWidths=[letter[0] - 108])
    t_box_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_box_sum)
    story.append(Spacer(1, 14))

    # Ficha técnica
    meta_data = [
        [Paragraph("<b>Nombre de la Aplicación:</b>", td_bold), Paragraph("Simulador Térmico Bioclimático Perú", td_style)],
        [Paragraph("<b>Modalidad Ejecutable:</b>", td_bold), Paragraph("Portable 100% Autónomo (No requiere Python ni librerías)", td_style)],
        [Paragraph("<b>Soporte de Sistema Operativo:</b>", td_bold), Paragraph("Microsoft Windows 10 y Windows 11 (64-bit)", td_style)],
        [Paragraph("<b>Formatos Compatibles:</b>", td_bold), Paragraph("SketchUp (.skp vía plugin .rbz), Wavefront 3D (.obj), JSON Térmico (.json)", td_style)],
        [Paragraph("<b>Marco Normativo Integrado:</b>", td_bold), Paragraph("RNE EM.110 (Térmico/Lumínico) • RNE A.010 (Aforo) • ASHRAE 55 • ISO 13790", td_style)],
        [Paragraph("<b>Fecha de Versión:</b>", td_bold), Paragraph("Noviembre 2026", td_style)]
    ]
    t_meta = Table(meta_data, colWidths=[150, letter[0] - 108 - 150])
    t_meta.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('BACKGROUND', (0,0), (0,-1), C_LIGHT_BG),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_meta)

    story.append(PageBreak())

    # =========================================================================
    # CAPÍTULO 1: FLUJO DE TRABAJO RÁPIDO (5 PASOS)
    # =========================================================================
    story.append(Paragraph("1. Flujo de Trabajo Rápido: De Cero a la Simulación", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Para realizar el análisis bioclimático y verificar el confort térmico de un recinto, "
        "el software sigue un flujo lógico y ordenado en cinco etapas consecutivas:",
        body_style
    ))

    flow_data = [
        [
            Paragraph("Paso", th_style),
            Paragraph("Acción Requerida", th_style),
            Paragraph("Pestaña / Herramienta", th_style),
            Paragraph("Resultado Obtenido", th_style)
        ],
        [
            Paragraph("<b>Paso 1</b>", step_num_style),
            Paragraph("Definir o Importar la Geometría del Auditorio/Edificio", td_style),
            Paragraph("Botón <i>'Importar Modelo 3D'</i> o Pestaña <i>'📐 Planos'</i>", td_style),
            Paragraph("Modelo 3D y áreas envolventes cargadas.", td_style)
        ],
        [
            Paragraph("<b>Paso 2</b>", step_num_style),
            Paragraph("Asignar Materiales a Techos, Muros y Ventanas", td_style),
            Paragraph("Pestañas <i>'🏠 Techo'</i>, <i>'🧱 Fachadas'</i> e Inspector", td_style),
            Paragraph("Transmitancias U, espesores y factores de amortiguamiento.", td_style)
        ],
        [
            Paragraph("<b>Paso 3</b>", step_num_style),
            Paragraph("Fijar Condiciones Climáticas y Aforo de Ocupación", td_style),
            Paragraph("Pestañas <i>'☀️ Clima'</i> y <i>'👥 Ocupación'</i>", td_style),
            Paragraph("Radiación solar horaria y carga térmica metabólica (W).", td_style)
        ],
        [
            Paragraph("<b>Paso 4</b>", step_num_style),
            Paragraph("Configurar Aparatos de Ventilación / HVAC", td_style),
            Paragraph("Pestaña <i>'💨 Ventilación'</i>", td_style),
            Paragraph("Inyectores, extractores, ventiladores y/o A/C posicionados.", td_style)
        ],
        [
            Paragraph("<b>Paso 5</b>", step_num_style),
            Paragraph("Ejecutar Simulación y Exportar Memoria Técnica", td_style),
            Paragraph("Botón <i>'Ejecutar Simulación Térmica 24h'</i>", td_style),
            Paragraph("Mapa térmico en planta 2D y PDF oficial EM.110 generado.", td_style)
        ]
    ]
    t_flow = Table(flow_data, colWidths=[40, 150, 140, letter[0] - 108 - 330])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG])
    ]))
    story.append(t_flow)

    # =========================================================================
    # CAPÍTULO 2: IMPORTACIÓN DE MODELOS 3D Y PLANOS
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("2. Importación de Modelos 3D y Gestión de Planos", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("A. Flujo de Exportación Directa desde SketchUp:", h2_style))
    story.append(Paragraph(
        "La aplicación incluye en su directorio raíz el plugin <b>thermal_exporter.rbz</b>. "
        "Para utilizarlo:",
        body_style
    ))
    story.append(Paragraph("1. En SketchUp, diríjase al menú <b>Extensiones &gt; Administrador de Extensiones</b> y haga clic en <b>'Instalar Extensión'</b>.", bullet_style))
    story.append(Paragraph("2. Seleccione el archivo <code>thermal_exporter.rbz</code> ubicado en la carpeta del simulador.", bullet_style))
    story.append(Paragraph("3. Una vez instalado, aparecerá la opción en el menú: <b>Extensiones &gt; Simulador Térmico Perú &gt; Exportar Modelo Térmico</b>.", bullet_style))
    story.append(Paragraph("4. Guarde el archivo resultante con extensión <code>.json</code> o <code>.obj</code> en su computadora.", bullet_style))

    story.append(Paragraph("B. Carga de Archivos en el Simulador:", h2_style))
    story.append(Paragraph(
        "En la barra de herramientas superior del Simulador, haga clic en el botón <b>'📁 Importar Modelo 3D'</b>. "
        "Seleccione el archivo exportado (soporta formatos <code>.obj</code> y <code>.json</code>). "
        "El modelo se dibujará de inmediato en el <b>Visor 3D Interactivo</b> y poblará la base de datos de superficies.",
        body_style
    ))

    story.append(Paragraph("C. Inspector de Planos y Reclasificación en 1 Clic (Pestaña '📐 Planos'):", h2_style))
    story.append(Paragraph(
        "La pestaña <b>📐 Planos</b> permite auditar cada cara geométrica individualmente:",
        body_style
    ))
    story.append(Paragraph("• <b>Selector de Componentes:</b> Lista desplegable con todas las superficies del proyecto, indicando su nombre y área en m² (ej. <i>'[Wall] Muro_Sur_01 (88.0 m²)'</i>). Al seleccionar una cara, se resalta automáticamente en color contrastante en el Visor 3D.", bullet_style))
    story.append(Paragraph("• <b>Botones de Asignación Rápida de Rol:</b>", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>🟦 Muro N1:</b> Asigna la superficie como muro perimétrico de la planta baja (Nivel 1 / Sala).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>🟥 Muro N2:</b> Asigna la superficie como muro de la planta alta (Nivel 2 / Mezzanine).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>🪟 Ventana:</b> Convierte la cara en paño acristalado, activando el cálculo de ganancia solar directa.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>⬜ Vecino:</b> Marca la superficie como obstáculo o edificación colindante (solo proyecta sombra exterior, no genera carga térmica interna).", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # CAPÍTULO 3: CÓMO AÑADIR ELEMENTOS, VENTANAS Y MATERIALES
    # =========================================================================
    story.append(Paragraph("3. Adición de Elementos, Ventanas y Asignación de Materiales", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("A. Cómo Insertar Ventanas en Fachadas:", h2_style))
    story.append(Paragraph(
        "Si importó un modelo sin vanos o desea perforar una nueva ventana en un muro:",
        body_style
    ))
    story.append(Paragraph("1. Vaya a la pestaña <b>'📐 Planos'</b> y presione el botón celeste <b>'➕ Insertar Ventana en Vano de Fachada...'</b>.", bullet_style))
    story.append(Paragraph("2. En el cuadro de diálogo emergente, seleccione:", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;a) <b>Fachada Receptora:</b> Muro Sur (Frontal), Muro Norte (Posterior), Muro Este o Muro Oeste.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;b) <b>Dimensiones del Vano:</b> Ancho (m), Altura (m) y Altura de Alféizar sobre el piso terminado.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;c) <b>Tipo de Vidrio:</b> Vidrio Simple Claro 4 mm, Doble Vidrio Hermético (DVH con cámara de aire) o Vidrio con Control Solar Reflectivo (Low-E).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;d) <b>Protección Solar:</b> Porcentaje de sombra por persianas interiores o aleros exteriores (0% a 100%).", bullet_style))
    story.append(Paragraph("3. Presione <b>'Insertar Ventana'</b>. La ventana se generará en el modelo 3D y en el cálculo térmico automáticamente.", bullet_style))

    story.append(Paragraph("B. Asignación de Materiales y Visualización de Propiedades:", h2_style))
    story.append(Paragraph(
        "En las pestañas <b>'🏠 Techo'</b> y <b>'🧱 Fachadas'</b>, al hacer clic en el botón de material se abre la ventana "
        "<b>'Configuración de Material'</b>:",
        body_style
    ))

    prop_box = [
        [
            Paragraph(
                "<b>PROPIEDADES FÍSICAS MOSTRADAS EN EL SELECTOR DE MATERIALES:</b><br/>"
                "• <b>Espesor (d en m):</b> Grosor del elemento constructivo.<br/>"
                "• <b>Conductividad térmica (&lambda; en W/m·K):</b> Capacidad intrínseca de conducir calor (valores bajos = mayor aislamiento).<br/>"
                "• <b>Transmitancia térmica (U en W/m²K):</b> Flujo de calor por m² ante una diferencia de 1 °C. El RNE EM.110 exige techos con $U \\le 0.83\\text{ W/m}^2\\text{K}$ en climas cálidos.<br/>"
                "• <b>Absortancia solar (&alpha;):</b> Fracción de calor solar que la superficie exterior absorbe (colores claros = 0.25 - 0.35, oscuros = 0.80 - 0.90).<br/>"
                "• <b>Desfase Térmico (&phi; en horas) y Amortiguamiento (f):</b> Cuántas horas retarda el muro la onda térmica exterior antes de que entre al auditorio.",
                body_style
            )
        ]
    ]
    t_prop_box = Table(prop_box, colWidths=[letter[0] - 108])
    t_prop_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_INFO_BG),
        ('BOX', (0,0), (-1,-1), 1, C_INFO_BORDER),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_prop_box)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Consejo Práctico:</b> Para evitar configurar cada muro uno por uno, utilice el botón verde "
        "<b>'⚡ Aplicar este Material y Espesor a Todos los Muros/Techos'</b> dentro de la pestaña Planos.",
        body_style
    ))

    # =========================================================================
    # CAPÍTULO 4: INGRESO DE DATOS DE CLIMA Y OCUPACIÓN
    # =========================================================================
    story.append(Spacer(1, 8))
    story.append(Paragraph("4. Configuración de Clima, Aforo y Ocupación Humana", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("A. Pestaña '☀️ Clima':", h2_style))
    story.append(Paragraph("• <b>Zonas Climáticas Predefinidas:</b> Elija entre Costa Cálida (ej. Piura, Ica, Lima Verano), Sierra Fría (Cusco, Puno), Selva Alta o Selva Baja. Los valores de temperatura y radiación solar se cargan automáticamente según datos históricos del SENAMHI.", bullet_style))
    story.append(Paragraph("• <b>Modo Clima Personalizado:</b> Marque la casilla para habilitar los campos manuales e introduzca la Temperatura Máxima de Diseño (°C), la Mínima Nocturna (°C) y la Radiación Solar Pico (W/m²) correspondientes a su localidad específica.", bullet_style))

    story.append(Paragraph("B. Pestaña '👥 Ocupación' (Conforme a RNE A.010):", h2_style))
    story.append(Paragraph("• <b>Cálculo Automático de Aforo:</b> El software calcula el área en planta del auditorio (ej. $23\\text{ m} \\times 16\\text{ m} = 368\\text{ m}^2$) y aplica el índice normativo del <b>RNE A.010 para auditorios y teatros (1.0 m² por persona)</b>.", bullet_style))
    story.append(Paragraph("• <b>Número de Ocupantes Manual:</b> Puede ajustar libremente la cantidad real de asistentes (ej. 150 personas).", bullet_style))
    story.append(Paragraph("• <b>Carga Metabólica:</b> Seleccione el nivel de actividad (120 W por persona sentada en reposo, 150 W actividad ligera de pie). Cada ocupante aporta 75 W de calor sensible (aumenta la temperatura) y 45 W de calor latente (humedad).", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # CAPÍTULO 5: GUÍA MAESTRA DE VENTILACIÓN Y HVAC
    # =========================================================================
    story.append(Paragraph("5. Guía Maestra de la Pestaña '💨 Ventilación y Climatización'", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Esta pestaña es el centro de control ambiental del edificio. Dispone de un panel deslizante vertical "
        "con cuatro tecnologías que pueden operar de manera independiente o combinada:",
        body_style
    ))

    # Sub-sección 1: Extractores Mecánicos
    story.append(Paragraph("5.1. Extractores Mecánicos de Aire (Pared Alta o Techo)", h2_style))
    story.append(Paragraph("• <b>Interruptor General:</b> Casilla <i>'Activar Extracción Mecánica'</i> (enciende o apaga todos los extractores).", bullet_style))
    story.append(Paragraph("• <b>Gestión de Múltiples Unidades:</b> Use el botón verde <b>'＋ Añadir'</b> para crear extractores adicionales (Extractor #1, #2, #3, etc.) o el botón rojo <b>'🗑️ Retirar'</b> para eliminar la unidad seleccionada en el combo.", bullet_style))
    story.append(Paragraph("• <b>Casilla 'Activar este extractor seleccionado':</b> Permite apagar un extractor en particular sin borrarlo, ideal para probar escenarios de ahorro energético o comparar 1 vs 3 extractores.", bullet_style))
    story.append(Paragraph("• <b>Ubicación y Desplazamiento:</b> Elija la pared de montaje (Norte, Sur, Este, Oeste o Techo) y regule con la <b>barra deslizante (slider)</b> la posición porcentual a lo largo del muro (ej. 25%, 50%, 75%).", bullet_style))
    story.append(Paragraph("• <b>Regulación de Caudal:</b> Ingrese el caudal de extracción en m³/h (ej. 2,400 m³/h por extractor) o use los botones de paso <b>[ - ]</b> y <b>[ + ]</b>.", bullet_style))

    # Sub-sección 2: Inyectores de Aire
    story.append(Paragraph("5.2. Inyectores de Aire Exterior (Presurización)", h2_style))
    story.append(Paragraph("• <b>Función:</b> Introducen aire exterior fresco hacia la zona baja de permanencia de los ocupantes.", bullet_style))
    story.append(Paragraph("• <b>Añadir / Retirar / Activar:</b> Misma lógica multi-unidad que los extractores (permite balancear caudales inyectados vs extraídos).", bullet_style))
    story.append(Paragraph("• <b>Selector de Origen del Aire Inyectado (Clave Bioclimática):</b> Permite seleccionar de dónde toma el aire el inyector:", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>'☀️ Calle / Fachada Soleada':</i> Toma aire a la temperatura ambiental exterior plena ($T_{\\text{ext}}$).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>'🌳 Patio Sombreado / Área Verde (-2.5 °C)':</i> Modela la toma de aire en un jardín protegido con vegetación, inyectando aire 2.5 °C más fresco.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>'🌿 Retiro Protegido / Sombra Fresca (-3.5 °C)':</i> Para tomas bajo galerías o patios interiores profundos.", bullet_style))

    # Sub-sección 3: Ventiladores de Confort
    story.append(Paragraph("5.3. Ventiladores Interiores de Confort (Sensación de Brisa ASHRAE 55)", h2_style))
    story.append(Paragraph("• <b>Efecto Físico de Brisa:</b> Los ventiladores NO alteran la temperatura de bulbo seco del termómetro, pero incrementan la velocidad del aire sobre la piel humana, acelerando la pérdida de calor por convección y evaporación del sudor.", bullet_style))
    story.append(Paragraph("• <b>Tipo de Montaje:</b>", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>'Techo':</i> Cono descendente amplio sobre las butacas (100% de efectividad).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>'Pared Alta / Mural':</i> Chorro longitudinal orientado al centro del salón (88% efectividad según distancia).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <i>'Pedestal / Suelo':</i> Brisa horizontal directa (95% efectividad).", bullet_style))
    story.append(Paragraph("• <b>Régimen de Velocidad y Datos de Fabricante:</b> Puede seleccionar velocidades predefinidas (0.5, 1.0, 1.8 m/s) o activar <i>'⚙️ Personalizado'</i> para digitar la velocidad de salida del catálogo del fabricante en m/s y el consumo eléctrico en Watts.", bullet_style))
    story.append(Paragraph("• <b>Lectura en Vivo del Alivio Térmico:</b> La etiqueta inferior muestra en tiempo real el enfriamiento percibido (ej. <i>'❄️ Alivio Térmico ASHRAE 55: -2.3 °C aparente'</i>).", bullet_style))

    # Sub-sección 4: Aire Acondicionado Split
    story.append(Paragraph("5.4. Aire Acondicionado Split (Climatización Activa)", h2_style))
    story.append(Paragraph("• <b>Temperatura Objetivo (Setpoint):</b> Temperatura deseada en el auditorio (ej. 24.0 °C).", bullet_style))
    story.append(Paragraph("• <b>Capacidad Frigorífica Nominal:</b> Elija entre capacidades comerciales estándar (12k, 18k, 24k, 36k, 48k, 60k BTU/h), <i>'⚡ Auto-dimensionar'</i> (calcula la demanda teórica sin límite) o <i>'⚙️ Personalizado'</i> para ingresar la capacidad exacta en BTU/h.", bullet_style))
    story.append(Paragraph("• <b>Diagnóstico de Balance Térmico:</b> El sistema evalúa si las unidades split instaladas logran abastecer las cargas por sol, personas e infiltraciones. Si la capacidad es insuficiente, indicará el déficit frigorífico en BTU/h.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # CAPÍTULO 6: VISUALIZACIÓN Y RESULTADOS (2D Y 3D)
    # =========================================================================
    story.append(Paragraph("6. Visualización Gráfica: Mapa Térmico 2D y Visor 3D", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("A. Mapa Térmico en Planta 2D (Corte Z = 1.10 m):", h2_style))
    story.append(Paragraph(
        "Al ubicarse en la pestaña central <b>'🗺️ Mapa de Calor por Planta'</b>, se observa el corte horizontal del auditorio "
        "a la altura del pecho y cabeza de las personas sentadas ($Z = 1.10\\text{ m}$):",
        body_style
    ))
    story.append(Paragraph("• <b>Degradado Cromático e Isotermas:</b> Líneas de contorno que muestran zonas frías (tonos claros/amarillos) alrededor de los inyectores de aire y focos cálidos (tonos rojos) junto a muros soleados o zonas con poca circulación.", bullet_style))
    story.append(Paragraph("• <b>Iconografía de Equipos en el Plano:</b>", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>[Iny] Rombos Cian:</b> Ubicación exacta de los inyectores de aire fresco.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>[Ext] Pentágonos Magenta:</b> Ubicación de los extractores mecánicos de pared alta.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>Aspas Verdes:</b> Cobertura de los ventiladores de confort.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>Rectángulos Azules:</b> Unidades evaporadoras de Aire Acondicionado Split.", bullet_style))
    story.append(Paragraph("• <b>Etiquetas de Resumen:</b> Indican en tiempo real la <b>Temperatura Mínima</b>, <b>Temperatura Promedio</b> y <b>Punto Más Cálido (Sol)</b> del recinto.", bullet_style))

    story.append(Paragraph("B. Visor 3D Interactivo:", h2_style))
    story.append(Paragraph(
        "La pestaña <b>'🧊 Visor 3D Interactivo'</b> permite auditar la geometría y el asoleamiento:",
        body_style
    ))
    story.append(Paragraph("• <b>Navegación del Mouse:</b>", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>Clic Izquierdo + Arrastrar:</b> Rota y orbita la cámara alrededor del modelo.", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>Clic Derecho + Arrastrar:</b> Desplaza la cámara en el plano (Paneo).", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;- <b>Rueda del Ratón:</b> Acerca o aleja la vista (Zoom in / Zoom out).", bullet_style))
    story.append(Paragraph("• <b>Barra de Hora Solar:</b> Deslice el control de hora (de 06:00 a 18:00) para ver en vivo cómo se mueven las sombras arrojadas por aleros y edificios vecinos sobre las fachadas del auditorio.", bullet_style))

    # =========================================================================
    # CAPÍTULO 7: EXPORTACIÓN DE LA MEMORIA DE CÁLCULO
    # =========================================================================
    story.append(Spacer(1, 8))
    story.append(Paragraph("7. Exportación de Informes y Memoria de Cálculo (RNE EM.110)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Al finalizar el diseño bioclimático, diríjase a la pestaña <b>'📑 Memoria de Cálculo'</b>. "
        "Encontrará el documento técnico formal previsualizado con:",
        body_style
    ))
    story.append(Paragraph("1. Base legal y normativa aplicable (RNE EM.110 Art. 5 a 14, RNE A.010, ASHRAE 55 e ISO 13790).", bullet_style))
    story.append(Paragraph("2. Cuadro de superficies, orientación, transmitancias térmicas individuales y transmitancia ponderada del recinto ($U_{\\text{prom}}$).", bullet_style))
    story.append(Paragraph("3. Balance de cargas horarias: conducción por envolvente con temperatura sol-aire amortiguada, radiación en ventanas, aporte metabólico de ocupantes y equipos.", bullet_style))
    story.append(Paragraph("4. Justificación del caudal de ventilación mecánica en renovaciones por hora (ACH) y L/s por ocupante.", bullet_style))
    story.append(Paragraph("• <b>Botón '📄 Exportar Memoria en PDF':</b> Genera un expediente listo para firmar e ingresar a municipalidades, colegios profesionales o entidades supervisoras.", bullet_style))
    story.append(Paragraph("• <b>Botón '🌐 Exportar Memoria en HTML':</b> Genera un informe web navegable e interactivo.", bullet_style))

    story.append(Spacer(1, 12))

    # Recuadro de soporte y cierre
    support_box = [
        [
            Paragraph(
                "<b>SOPORTE TÉCNICO Y DIAGNÓSTICO EN ERROR.LOG:</b><br/>"
                "El software cuenta con un registrador de diagnóstico automático. Si en alguna computadora "
                "ocurre una falla inesperada, se generará o actualizará automáticamente un archivo denominado "
                "<code>error.log</code> en la misma carpeta donde esté ubicado el ejecutable.<br/>"
                "Para solicitar asistencia o soporte de ingeniería, adjunte ese archivo para resolver la incidencia de forma inmediata.",
                body_style
            )
        ]
    ]
    t_sup = Table(support_box, colWidths=[letter[0] - 108])
    t_sup.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sup)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Manual de Operación generado exitosamente: {filename}")


if __name__ == "__main__":
    generate_manual_pdf()
