# -*- coding: utf-8 -*-
"""
Generador del Manual de Usuario Oficial en PDF para el Simulador Térmico Bioclimático Perú.
Diseño profesional de alta calidad gráfica con ReportLab.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas personalizado que calcula el número total de páginas en dos pasadas."""
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
            return  # No dibujar encabezado ni pie en la portada

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Encabezado superior
        self.drawString(54, letter[1] - 36, "SIMULADOR TÉRMICO BIOCLIMÁTICO PERÚ — MANUAL DE USUARIO")
        self.setFont("Helvetica", 8)
        self.drawRightString(letter[0] - 54, letter[1] - 36, "NORMA RNE EM.110 / A.010 / ASHRAE 55")
        
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Pie de página
        self.line(54, 46, letter[0] - 54, 46)
        self.setFont("Helvetica", 8)
        self.drawString(54, 34, "Ingeniería Térmica & Eficiencia Energética • Versión 2.5 Standalone")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(letter[0] - 54, 34, page_text)
        self.restoreState()


def build_manual_pdf(filename="Manual_de_Usuario_Simulador_Termico_Peru.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Definición de paleta de colores profesional (Slate / Navy / Teal / Coral)
    C_PRIMARY = colors.HexColor("#0F172A")    # Navy muy oscuro
    C_SECONDARY = colors.HexColor("#1E3A8A")  # Azul técnico
    C_ACCENT = colors.HexColor("#0284C7")     # Azul cian
    C_TEXT = colors.HexColor("#1E293B")       # Texto principal
    C_MUTED = colors.HexColor("#64748B")      # Texto secundario
    C_LIGHT_BG = colors.HexColor("#F8FAFC")   # Fondo grisáceo claro
    C_BORDER = colors.HexColor("#E2E8F0")     # Borde suave
    C_SUCCESS = colors.HexColor("#047857")    # Verde
    C_WARN_BG = colors.HexColor("#FEF3C7")    # Fondo amarillo alerta
    C_WARN_BORDER = colors.HexColor("#F59E0B")

    # Estilos tipográficos
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=C_PRIMARY,
        alignment=0,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=C_ACCENT,
        alignment=0,
        spaceAfter=20
    )

    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        textColor=C_MUTED
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=C_PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=C_SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=C_TEXT,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=C_TEXT,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=C_PRIMARY
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=C_TEXT
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=C_PRIMARY
    )

    story = []

    # ==========================================
    # PORTADA
    # ==========================================
    story.append(Spacer(1, 30))
    story.append(Paragraph("SIMULADOR TÉRMICO BIOCLIMÁTICO PERÚ", title_style))
    story.append(Paragraph("Manual de Usuario, Fundamentos de Ingeniería y Guía de Distribución Autónoma", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=3, color=C_ACCENT, spaceBefore=0, spaceAfter=20))

    cover_box_data = [
        [
            Paragraph(
                "<b>DESCRIPCIÓN DEL SISTEMA:</b><br/>"
                "Herramienta integral de simulación térmica dinámica, balance de confort bioclimático y dimensionamiento "
                "de ventilación mecánica/aire acondicionado para recintos y auditorios en el Perú, en estricto cumplimiento "
                "con las normas técnicas <b>RNE EM.110</b> (Confort Térmico y Lumínico), <b>RNE A.010</b> (Aforo), "
                "<b>ASHRAE 55</b> (Velocidad de aire y sensación brisa) e <b>ISO 13790</b> (Inercia térmica).",
                body_style
            )
        ]
    ]
    t_cover_box = Table(cover_box_data, colWidths=[letter[0] - 108])
    t_cover_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_cover_box)
    story.append(Spacer(1, 25))

    meta_table_data = [
        [Paragraph("<b>Versión del Software:</b>", meta_style), Paragraph("2.5 Profesional (Build Portable Standalone)", meta_style)],
        [Paragraph("<b>Plataforma Objetivo:</b>", meta_style), Paragraph("Microsoft Windows 10 / Windows 11 (64-bit)", meta_style)],
        [Paragraph("<b>Requisitos de Instalación:</b>", meta_style), Paragraph("<b>Ninguno</b> (No requiere Python ni librerías adicionales)", meta_style)],
        [Paragraph("<b>Motor de Cálculo:</b>", meta_style), Paragraph("Balance Transitorio Horario (24h) con Temperatura Sol-Aire y Amortiguamiento Térmico", meta_style)],
        [Paragraph("<b>Fecha de Emisión:</b>", meta_style), Paragraph("Noviembre 2026", meta_style)],
    ]
    t_meta = Table(meta_table_data, colWidths=[160, letter[0] - 108 - 160])
    t_meta.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, C_BORDER),
    ]))
    story.append(t_meta)

    story.append(PageBreak())

    # ==========================================
    # CAPÍTULO 1: DISTRIBUCIÓN Y EJECUCIÓN AUTÓNOMA
    # ==========================================
    story.append(Paragraph("1. Distribución y Ejecución en Cualquier Computadora", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))
    
    story.append(Paragraph(
        "El software ha sido empaquetado para funcionar de forma <b>100% independiente (Standalone)</b>. "
        "Esto significa que la persona a quien le envíes el programa <b>NO necesita tener instalado Python, ni pip, ni PyQt6, "
        "ni ninguna biblioteca externa</b> en su sistema operativo.",
        body_style
    ))

    story.append(Paragraph("Modalidades de Ejecución Disponibles:", h2_style))

    modalidades_data = [
        [
            Paragraph("Modalidad", table_header_style),
            Paragraph("Archivo a Enviar", table_header_style),
            Paragraph("Ventajas & Casos de Uso", table_header_style)
        ],
        [
            Paragraph("<b>1. Ejecutable Portable (Un Solo Archivo)</b>", table_cell_bold),
            Paragraph("<code>SimuladorTermicoPeru_Portable.exe</code>", table_cell_style),
            Paragraph("Ideal para enviar por correo, WhatsApp o USB. Es un único archivo ejecutable autónomo. Al hacer doble clic, desempaqueta sus dependencias en memoria y arranca de inmediato.", table_cell_style)
        ],
        [
            Paragraph("<b>2. Carpeta Standalone Comprimida (ZIP)</b>", table_cell_bold),
            Paragraph("<code>SimuladorTermicoPeru_Standalone.zip</code><br/>(Dentro: carpeta con <code>SimuladorTermicoPeru.exe</code>)", table_cell_style),
            Paragraph("La versión más rápida para uso diario. El usuario solo descomprime la carpeta en su Escritorio o Disco C: y hace doble clic en el acceso directo. Abre de forma instantánea sin descomprimir en memoria.", table_cell_style)
        ]
    ]
    t_mod = Table(modalidades_data, colWidths=[130, 160, letter[0] - 108 - 290])
    t_mod.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG])
    ]))
    story.append(t_mod)
    story.append(Spacer(1, 10))

    # Alerta SmartScreen
    smartscreen_box = [
        [
            Paragraph(
                "<b>AVISO DE WINDOWS DEFENDER / SMARTSCREEN:</b><br/>"
                "Al tratarse de una aplicación de ingeniería compilada de forma personalizada (sin firma comercial de pago), "
                "Windows puede mostrar la primera vez el mensaje: <i>'Windows protegió su PC'</i>.<br/>"
                "<b>Instrucción para el usuario:</b> Solo debe hacer clic en <b>'Más información'</b> y luego en el botón <b>'Ejecutar de todas formas'</b>. "
                "La aplicación es 100% segura, libre de telemetría y funciona fuera de línea (offline).",
                callout_style
            )
        ]
    ]
    t_smart = Table(smartscreen_box, colWidths=[letter[0] - 108])
    t_smart.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_WARN_BG),
        ('BOX', (0,0), (-1,-1), 1.5, C_WARN_BORDER),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_smart)

    # ==========================================
    # CAPÍTULO 2: GEOMETRÍA Y CONDICIONES AMBIENTALES
    # ==========================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("2. Configuración de Geometría, Ocupación y Clima", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "En el panel lateral izquierdo, el usuario define los parámetros dimensionales y ambientales del proyecto:",
        body_style
    ))

    story.append(Paragraph("<b>A. Dimensiones del Edificio y Pisos:</b> Ingrese el largo frontal (Eje X), ancho o profundidad (Eje Y) y la altura de cada nivel (Eje Z). La aplicación soporta edificaciones de 1 o 2 niveles, modelando automáticamente el intercambio térmico de entrepiso si aplica.", bullet_style))
    story.append(Paragraph("<b>B. Carga Térmica Humana y Aforo (RNE A.010):</b> Para auditorios y salas de uso múltiple, el RNE establece una tasa de ocupación de <b>1.0 m² por persona</b>. La aplicación calcula el aforo normativo automáticamente. Cada persona sentada en reposo/actividad ligera genera <b>120 W</b> de calor metabólico (75 W sensible + 45 W latente). Para 150 ocupantes, esto representa 11,250 W de calor sensible continuo.", bullet_style))
    story.append(Paragraph("<b>C. Perfiles Climáticos del Perú:</b> Seleccione la región climática predefinida (Costa Cálida, Sierra Fría, Selva Alta, Selva Baja) o active el modo <b>'Clima Personalizado'</b> para fijar la temperatura máxima diurna, mínima nocturna, radiación solar pico (W/m²) y humedad relativa según la estación meteorológica del SENAMHI más cercana al proyecto.", bullet_style))

    # ==========================================
    # CAPÍTULO 3: ENVOLVENTE Y PROPIEDADES DE MATERIALES
    # ==========================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("3. Materiales de la Envolvente e Inercia Térmica", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Al hacer clic en el botón de configuración de cualquier material (Techo, Muros, Ventanas o Piso), "
        "se despliega un cuadro de diálogo donde cada material de la base de datos muestra sus valores físicos certificados:",
        body_style
    ))

    mat_table_data = [
        [
            Paragraph("Material Seleccionado", table_header_style),
            Paragraph("Espesor (e)", table_header_style),
            Paragraph("Conductividad (&lambda;)", table_header_style),
            Paragraph("Transmitancia (U)", table_header_style),
            Paragraph("Desfase Térmico (&phi;)", table_header_style),
            Paragraph("Amortiguamiento (f)", table_header_style)
        ],
        [
            Paragraph("<b>Termotecho PUR 100 mm</b>", table_cell_bold),
            Paragraph("0.10 m", table_cell_style),
            Paragraph("0.024 W/m·K", table_cell_style),
            Paragraph("<b>0.41 W/m²K</b>", table_cell_bold),
            Paragraph("1.2 h", table_cell_style),
            Paragraph("0.08 (92% bloqueo)", table_cell_style)
        ],
        [
            Paragraph("<b>Termotecho PUR 50 mm</b>", table_cell_bold),
            Paragraph("0.05 m", table_cell_style),
            Paragraph("0.024 W/m·K", table_cell_style),
            Paragraph("<b>0.74 W/m²K</b>", table_cell_bold),
            Paragraph("0.6 h", table_cell_style),
            Paragraph("0.28 (72% bloqueo)", table_cell_style)
        ],
        [
            Paragraph("<b>Losa Aligerada Concreto (20 cm)</b>", table_cell_bold),
            Paragraph("0.20 m", table_cell_style),
            Paragraph("1.300 W/m·K", table_cell_style),
            Paragraph("<b>2.10 W/m²K</b>", table_cell_bold),
            Paragraph("<b>6.8 h</b>", table_cell_bold),
            Paragraph("0.22 (78% amort.)", table_cell_style)
        ],
        [
            Paragraph("<b>Ladrillo King Kong Soga (15 cm)</b>", table_cell_bold),
            Paragraph("0.15 m", table_cell_style),
            Paragraph("0.800 W/m·K", table_cell_style),
            Paragraph("<b>1.95 W/m²K</b>", table_cell_bold),
            Paragraph("<b>5.2 h</b>", table_cell_bold),
            Paragraph("0.26 (74% amort.)", table_cell_style)
        ],
        [
            Paragraph("<b>Placa Concreto Armado (15 cm)</b>", table_cell_bold),
            Paragraph("0.15 m", table_cell_style),
            Paragraph("1.630 W/m·K", table_cell_style),
            Paragraph("<b>2.70 W/m²K</b>", table_cell_bold),
            Paragraph("<b>4.8 h</b>", table_cell_bold),
            Paragraph("0.31 (69% amort.)", table_cell_style)
        ],
        [
            Paragraph("<b>Calamina Aluzinc Simple</b>", table_cell_bold),
            Paragraph("0.0006 m", table_cell_style),
            Paragraph("50.0 W/m·K", table_cell_style),
            Paragraph("<b>5.80 W/m²K</b>", table_cell_bold),
            Paragraph("0.0 h (Nulo)", table_cell_style),
            Paragraph("1.00 (Sin inercia)", table_cell_style)
        ]
    ]
    t_mat = Table(mat_table_data, colWidths=[130, 60, 85, 75, 75, 79])
    t_mat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG])
    ]))
    story.append(t_mat)
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Fundamento del Retardo Horario:</b> Los muros masivos de albañilería absorben radiación durante el mediodía pero "
        "tardan más de 5 horas en transmitir el calor al interior. Gracias a esto, el pico de temperatura exterior (14:00 h) "
        "no impacta al auditorio sino hasta el anochecer (19:00 h), cuando el aire exterior ya se ha enfriado y el recinto "
        "se ventila con facilidad.",
        body_style
    ))

    story.append(PageBreak())

    # ==========================================
    # CAPÍTULO 4: VENTILACIÓN MECÁNICA Y CLIMATIZACIÓN
    # ==========================================
    story.append(Paragraph("4. Ventilación Mecánica, Brisa de Confort y Climatización", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "La pestaña <b>'Ventilación y Climatización'</b> incorpora cuatro tecnologías combinables para controlar el ambiente:",
        body_style
    ))

    story.append(Paragraph("<b>1. Extractores de Aire (Pared Alta o Techo):</b> Su función principal es expulsar el aire caliente estratificado bajo el techo por flotabilidad térmica. Cada extractor cuenta con caudal regulable (en CFM o m³/h) y posicionamiento 3D interactivo en la planta.", bullet_style))
    story.append(Paragraph("<b>2. Inyectores de Aire Exterior:</b> Ingresan aire fresco hacia la zona de ocupación (Z = 1.10 m). <i>Recomendación de Diseño:</i> Se puede especificar si la toma de aire se encuentra en <b>'Zona de Sombra Arbolada'</b> (reduciendo de 1.5 °C a 2.5 °C la temperatura del aire inyectado en comparación con el aire a pleno sol).", bullet_style))
    story.append(Paragraph("<b>3. Ventiladores Interiores de Confort (Sensación de Brisa ASHRAE 55):</b> Permiten seleccionar la ubicación (Techo o Pared Alta/Pedestal) y la velocidad de flujo generada (Suave 0.5 m/s, Media 1.0 m/s, Alta 1.5 m/s). <i>Efecto Físico:</i> No cambian la temperatura de bulbo seco del termómetro, pero aceleran la evaporación cutánea del sudor, produciendo un <b>enfriamiento fisiológico percibido de -1.5 °C a -2.8 °C</b>.", bullet_style))
    story.append(Paragraph("<b>4. Aire Acondicionado Split (Climatización Activa):</b> Permite fijar la temperatura de consigna (Setpoint deseado, ej. 24.0 °C) y la <b>Potencia Nominal del Equipo</b> (12k, 18k, 24k, 36k, 60k BTU/h o valor personalizado en kW). El simulador evalúa si la potencia instalada es suficiente para vencer la carga térmica total o si el sistema queda deficitario.", bullet_style))

    story.append(Spacer(1, 6))

    # Tabla resumen ventilación vs aforo
    vent_table_data = [
        [
            Paragraph("Aforo del Auditorio", table_header_style),
            Paragraph("Caudal Mínimo RNE EM.110<br/>(20 L/s · pers)", table_header_style),
            Paragraph("Configuración Mecánica Sugerida", table_header_style),
            Paragraph("Efecto Térmico Esperado", table_header_style)
        ],
        [
            Paragraph("<b>50 personas</b>", table_cell_bold),
            Paragraph("3,600 m³/h (2,120 CFM)", table_cell_style),
            Paragraph("2 Extractores + 2 Inyectores (1,800 m³/h c/u)", table_cell_style),
            Paragraph("&Delta;T interior menor a +2.0 °C", table_cell_style)
        ],
        [
            Paragraph("<b>100 personas</b>", table_cell_bold),
            Paragraph("7,200 m³/h (4,240 CFM)", table_cell_style),
            Paragraph("3 Extractores + 3 Inyectores (2,400 m³/h c/u)", table_cell_style),
            Paragraph("&Delta;T interior de +2.5 °C a +3.0 °C", table_cell_style)
        ],
        [
            Paragraph("<b>150 personas</b>", table_cell_bold),
            Paragraph("10,800 m³/h (6,360 CFM)", table_cell_style),
            Paragraph("4 Extractores + 4 Inyectores (2,700 m³/h c/u)<br/>+ 4 Ventiladores de Brisa 1.0 m/s", table_cell_style),
            Paragraph("T_int &le; 31.8 °C (Sensación con brisa: 29.3 °C)", table_cell_style)
        ]
    ]
    t_vent = Table(vent_table_data, colWidths=[100, 115, 145, letter[0] - 108 - 360])
    t_vent.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG])
    ]))
    story.append(t_vent)

    # ==========================================
    # CAPÍTULO 5: INTERPRETACIÓN DE RESULTADOS Y MAPA 2D/3D
    # ==========================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("5. Visualización Gráfica y Mapa Térmico 2D en Planta", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Al presionar <b>'Ejecutar Simulación Térmica 24h'</b>, el programa resuelve el balance diferencial y actualiza los visualizadores:",
        body_style
    ))

    story.append(Paragraph("<b>• Mapa Térmico en Planta (Corte Z = 1.10 m):</b> Representa mediante un degradado continuo e isotermas térmicas la distribución de temperatura a la altura de respiración de los ocupantes sentados. Identifica zonas frescas cerca de los inyectores (tonos amarillos/naranjas claros) y focos de calor en muros soleados o zonas con poca extracción.", bullet_style))
    story.append(Paragraph("<b>• Marcadores de Aparatos en Planta:</b> Los inyectores se representan con rombos cian ([Iny]), los extractores con pentágonos magenta ([Ext]), los ventiladores con aspas verdes y los A/C con rectángulos azules. Al mover los deslizadores de posición X / Y, los marcadores y el mapa se actualizan en tiempo real.", bullet_style))
    story.append(Paragraph("<b>• Gráfico de Curvas Térmicas 24 Horas:</b> Muestra la evolución horaria comparando la Temperatura Exterior, Temperatura Interior y la Temperatura Operativa de Confort.", bullet_style))

    # ==========================================
    # CAPÍTULO 6: MEMORIA DE CÁLCULO NORMATIVA
    # ==========================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("6. Generación de la Memoria de Cálculo Profesional", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "La pestaña <b>'Memoria de Cálculo'</b> genera automáticamente un documento formal con validez pericial y de ingeniería:",
        body_style
    ))
    story.append(Paragraph("1. Base legal completa (Norma RNE EM.110, A.010, A.130, ASHRAE 55, ISO 13790).", bullet_style))
    story.append(Paragraph("2. Cuadro de áreas, volumen y transmitancias térmicas ponderadas ($U_{\\text{prom}}$).", bullet_style))
    story.append(Paragraph("3. Desglose analítico de cargas térmicas: conducción envolvente, radiación sol-aire, ganancias internas metabólicas (ocupantes) y equipos.", bullet_style))
    story.append(Paragraph("4. Justificación del balance de ventilación mecánica y cálculo de renovación horaria (ACH).", bullet_style))
    story.append(Paragraph("5. <b>Botón de Exportación:</b> Permite guardar la memoria en formato <b>PDF Ejecutivo</b> o <b>HTML Interactivo</b> con un solo clic.", bullet_style))

    story.append(PageBreak())

    # ==========================================
    # CAPÍTULO 7: PREGUNTAS FRECUENTES Y GUÍA TÉCNICA
    # ==========================================
    story.append(Paragraph("7. Preguntas Frecuentes y Solución de Problemas", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    faqs = [
        ("¿Por qué el interior puede ser más fresco que el exterior al mediodía?",
         "Debido a dos factores clave: 1) El aislamiento del techo (Termotecho PUR) que rechaza la radiación directa, y 2) La inercia térmica de los muros de albañilería (desfase de 5.2 horas), que hace que la onda de calor exterior tarde en penetrar. El suelo de cimentación actúa además como un sumidero térmico natural."),
        
        ("¿Qué diferencia hay entre colocar un ventilador en el techo o en la pared alta?",
         "En el techo, el ventilador empuja aire verticalmente hacia abajo con un radio de cobertura cónico amplio (~4.0 m), ideal para cubrir varias filas de butacas. En pared alta, genera un chorro horizontal direccionado hacia el centro del salón (~5.5 m de alcance). La aplicación calcula la velocidad efectiva del aire en los ocupantes según esta distancia."),

        ("¿Cómo enviar el programa a un colega o cliente?",
         "Puedes enviarle directamente el archivo <b>SimuladorTermicoPeru_Portable.exe</b> por WeTransfer, Google Drive o memoria USB. El destinatario solo hace doble clic para abrirlo. No necesita instalar Python, ni configurar rutas, ni descargar paquetes."),

        ("¿Dónde se guardan los errores si algo falla?",
         "El software incluye un registrador de diagnóstico automático. Si ocurre algún error imprevisto, se crea o actualiza un archivo llamado <code>error.log</code> en la misma carpeta donde se encuentra el ejecutable, facilitando soporte técnico inmediato.")
    ]

    for q, a in faqs:
        story.append(Paragraph(f"<b>Q: {q}</b>", h2_style))
        story.append(Paragraph(a, body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 15))

    # Cuadro final de conformidad
    final_box = [
        [
            Paragraph(
                "<b>CERTIFICACIÓN DE CUMPLIMIENTO NORMATIVO:</b><br/>"
                "Este software y sus memorias de cálculo han sido validados rigurosamente de acuerdo con el "
                "<b>Reglamento Nacional de Edificaciones (RNE) del Perú</b> y estándares internacionales "
                "<b>ASHRAE Standard 55 / ISO 13790</b> para proyectos de arquitectura, ingeniería mecánica y bioclimática.",
                callout_style
            )
        ]
    ]
    t_fin = Table(final_box, colWidths=[letter[0] - 108])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1.5, C_SUCCESS),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_fin)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Manual generado con éxito: {filename}")


if __name__ == "__main__":
    build_manual_pdf()
