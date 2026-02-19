# modelo/reportes.py
"""
Generador de reportes comparativos para SIAM (SIAM-RF-04).
Genera PDFs con estadísticas del inventario.
"""
import os
from datetime import datetime
from typing import List, Dict, Any

# reportlab es opcional (no disponible en Android por defecto)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from kivy.utils import platform


CORPOELEC_BLUE = '#001A70'
CORPOELEC_RED = '#E31C23'


def _get_output_path(nombre_archivo: str) -> str:
    """Obtiene ruta de salida según plataforma."""
    if platform == "android":
        from android.storage import primary_external_storage_path
        ruta = os.path.join(primary_external_storage_path(), "SIAM")
        os.makedirs(ruta, exist_ok=True)
        return os.path.join(ruta, nombre_archivo)
    else:
        return nombre_archivo


def generar_reporte_inventario(productos: List[Dict[str, Any]], usuario: str = "") -> str:
    """
    Genera reporte PDF del estado actual del inventario.

    Args:
        productos: Lista de productos del inventario
        usuario: Usuario que genera el reporte

    Returns:
        str: Ruta del archivo generado
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab no disponible")

    fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre = f"Reporte_Inventario_{fecha}.pdf"
    ruta = _get_output_path(nombre)

    doc = SimpleDocTemplate(ruta, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle('Titulo', parent=styles['Heading1'],
                            fontSize=20, alignment=TA_CENTER,
                            spaceAfter=20, textColor=colors.HexColor(CORPOELEC_BLUE))
    subtitulo = ParagraphStyle('Sub', parent=styles['Heading2'],
                               fontSize=14, spaceAfter=10, spaceBefore=15,
                               textColor=colors.HexColor(CORPOELEC_BLUE))
    normal = ParagraphStyle('Norm', parent=styles['Normal'],
                            fontSize=10, alignment=TA_JUSTIFY, spaceAfter=6)

    story = []

    # Encabezado
    story.append(Paragraph("REPORTE DE INVENTARIO", titulo))
    story.append(Paragraph("SIAM - Sistema de Inventario Automatico", styles['Heading3']))
    story.append(Spacer(1, 8))
    info = f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if usuario:
        info += f"  |  Usuario: {usuario}"
    info += f"  |  Total productos: {len(productos)}"
    story.append(Paragraph(info, normal))
    story.append(Spacer(1, 15))

    # Resumen estadístico
    story.append(Paragraph("1. RESUMEN ESTADISTICO", subtitulo))

    total = len(productos)
    total_stock = sum(p.get('cantidad', 0) for p in productos)
    stock_bajo = [p for p in productos
                  if (p.get('stock_maximo', 0) > 0 and
                      p.get('cantidad', 0) <= p.get('stock_maximo', 0) * 0.15)
                  or (p.get('stock_minimo', 0) > 0 and
                      p.get('cantidad', 0) <= p.get('stock_minimo', 0))]
    sin_stock = [p for p in productos if p.get('cantidad', 0) == 0]

    # Tabla de resumen
    resumen_data = [
        ['Metrica', 'Valor'],
        ['Total de productos', str(total)],
        ['Stock total (unidades)', str(total_stock)],
        ['Productos sin stock', str(len(sin_stock))],
        ['Productos con stock bajo', str(len(stock_bajo))],
    ]

    resumen_table = Table(resumen_data, colWidths=[3 * inch, 2 * inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CORPOELEC_BLUE)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(resumen_table)
    story.append(Spacer(1, 15))

    # Distribución por categoría
    story.append(Paragraph("2. DISTRIBUCION POR CATEGORIA", subtitulo))

    categorias = {}
    for p in productos:
        cat = p.get('categoria', 'General') or 'General'
        if cat not in categorias:
            categorias[cat] = {'count': 0, 'stock': 0}
        categorias[cat]['count'] += 1
        categorias[cat]['stock'] += p.get('cantidad', 0)

    cat_data = [['Categoria', 'Productos', 'Stock Total']]
    for cat, vals in sorted(categorias.items()):
        cat_data.append([cat, str(vals['count']), str(vals['stock'])])

    cat_table = Table(cat_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CORPOELEC_BLUE)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 15))

    # Listado completo de productos
    story.append(Paragraph("3. LISTADO DE PRODUCTOS", subtitulo))

    # Tabla de productos (máx primeros 100 para no sobrecargar)
    prod_data = [['Codigo', 'Nombre', 'Cantidad', 'Ubicacion', 'Categoria']]
    for p in productos[:100]:
        prod_data.append([
            str(p.get('codigo_barras', ''))[:15],
            str(p.get('nombre', ''))[:30],
            str(p.get('cantidad', 0)),
            str(p.get('ubicacion', ''))[:20],
            str(p.get('categoria', ''))[:15],
        ])

    if len(productos) > 100:
        prod_data.append(['...', f'(+{len(productos) - 100} mas)', '', '', ''])

    col_widths = [1.2 * inch, 2 * inch, 0.8 * inch, 1.3 * inch, 1 * inch]
    prod_table = Table(prod_data, colWidths=col_widths)
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CORPOELEC_BLUE)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(prod_table)
    story.append(Spacer(1, 15))

    # Alertas (stock bajo)
    if stock_bajo:
        story.append(Paragraph("4. ALERTAS DE STOCK BAJO", subtitulo))
        alerta_data = [['Producto', 'Stock Actual', 'Stock Min', 'Stock Max']]
        for p in stock_bajo:
            alerta_data.append([
                str(p.get('nombre', ''))[:35],
                str(p.get('cantidad', 0)),
                str(p.get('stock_minimo', 0)),
                str(p.get('stock_maximo', 0)),
            ])

        alerta_table = Table(alerta_data, colWidths=[2.8 * inch, 1 * inch, 1 * inch, 1 * inch])
        alerta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(CORPOELEC_RED)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#FFF0F0'), colors.HexColor('#FFE0E0')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(alerta_table)

    # Generar
    doc.build(story)
    print(f"✓ Reporte generado: {ruta}")
    return ruta
