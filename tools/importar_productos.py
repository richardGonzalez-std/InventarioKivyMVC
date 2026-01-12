#!/usr/bin/env python3
"""
Script para importar productos venezolanos desde Open Food Facts a Firebase.

Uso:
    python tools/importar_productos.py [--limit N] [--dry-run]

Opciones:
    --limit N    Limitar a N productos (default: todos)
    --dry-run    Solo mostrar, no subir a Firebase
"""

import requests
import json
import time
import sys
import os

# Agregar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────

OPENFOODFACTS_API = "https://world.openfoodfacts.org/api/v2/search"
COUNTRY = "venezuela"
PAGE_SIZE = 100  # Productos por página
FIELDS = "code,product_name,brands,categories,image_url"

# Mapeo de categorías Open Food Facts → categorías SIAM
CATEGORIA_MAP = {
    "beverages": "Bebidas",
    "dairy": "Lácteos",
    "snacks": "Snacks",
    "cereals": "Cereales",
    "spreads": "Untables",
    "sauces": "Salsas",
    "canned": "Enlatados",
    "frozen": "Congelados",
    "breads": "Panadería",
    "meats": "Carnes",
    "fruits": "Frutas",
    "vegetables": "Vegetales",
    "condiments": "Condimentos",
    "oils": "Aceites",
    "pastas": "Pastas",
    "flours": "Harinas",
}


def descargar_productos_venezuela(limit=None):
    """
    Descarga productos de Venezuela desde Open Food Facts API v2.

    Args:
        limit: Número máximo de productos (None = todos)

    Returns:
        Lista de productos formateados
    """
    productos = []
    page = 1
    total_descargados = 0

    print(f"📥 Descargando productos de Venezuela desde Open Food Facts...")
    print(f"   Límite: {limit or 'Sin límite'}")
    print()

    while True:
        params = {
            'countries_tags_en': COUNTRY,
            'page': page,
            'page_size': PAGE_SIZE,
            'fields': FIELDS,
        }

        try:
            response = requests.get(OPENFOODFACTS_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"✗ Error en página {page}: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"✗ Error parseando JSON en página {page}: {e}")
            break

        page_products = data.get('products', [])

        if not page_products:
            print(f"   Fin de datos en página {page}")
            break

        for p in page_products:
            producto = formatear_producto(p)
            if producto:  # Solo si tiene datos válidos
                productos.append(producto)
                total_descargados += 1

                if limit and total_descargados >= limit:
                    break

        print(f"   Página {page}: {len(page_products)} productos (Total: {total_descargados})")

        if limit and total_descargados >= limit:
            break

        page += 1
        time.sleep(0.5)  # Respetar rate limit

    print(f"\n✓ Descargados: {len(productos)} productos válidos")
    return productos


def formatear_producto(off_product):
    """
    Convierte producto de Open Food Facts al formato SIAM.

    Args:
        off_product: Producto en formato Open Food Facts

    Returns:
        Dict con formato SIAM o None si no es válido
    """
    codigo = off_product.get('code', '').strip()
    nombre = off_product.get('product_name', '').strip()

    # Validar datos mínimos
    if not codigo or not nombre:
        return None

    # Limpiar código (solo números)
    codigo = ''.join(c for c in codigo if c.isdigit())
    if len(codigo) < 8:  # Códigos muy cortos no son válidos
        return None

    # Obtener categoría
    categorias_off = off_product.get('categories', '').lower()
    categoria = "General"
    for key, value in CATEGORIA_MAP.items():
        if key in categorias_off:
            categoria = value
            break

    # Construir producto SIAM
    producto = {
        'codigo_barras': codigo,
        'nombre': nombre[:100],  # Limitar longitud
        'categoria': categoria,
        'cantidad': 0,  # Stock inicial
        'unidad': 'unidades',
        'ubicacion': 'Por asignar',
        'marca': off_product.get('brands', '')[:50],
        'imagen_url': off_product.get('image_url', ''),
    }

    return producto


def subir_a_firebase(productos, dry_run=False):
    """
    Sube productos a Firebase Firestore.

    Args:
        productos: Lista de productos a subir
        dry_run: Si True, solo muestra sin subir

    Returns:
        Cantidad de productos subidos
    """
    if dry_run:
        print("\n🔍 DRY RUN - Mostrando productos (no se subirán):")
        for i, p in enumerate(productos[:10]):
            print(f"   {i+1}. [{p['codigo_barras']}] {p['nombre']} - {p['categoria']}")
        if len(productos) > 10:
            print(f"   ... y {len(productos) - 10} más")
        return 0

    # Cargar configuración Firebase
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'firebase-config.json'
    )

    if not os.path.exists(config_path):
        print(f"✗ No se encontró {config_path}")
        print("  Crea el archivo con tu project_id y api_key")
        return 0

    with open(config_path) as f:
        config = json.load(f)

    project_id = config.get('project_id')
    api_key = config.get('api_key')

    if not project_id or not api_key:
        print("✗ Configuración Firebase incompleta")
        return 0

    print(f"\n📤 Subiendo {len(productos)} productos a Firebase...")
    print(f"   Proyecto: {project_id}")

    # URL base Firestore REST API
    base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"

    subidos = 0
    errores = 0

    for i, producto in enumerate(productos):
        codigo = producto['codigo_barras']

        # Convertir a formato Firestore
        firestore_doc = {
            'fields': {
                'codigo_barras': {'stringValue': producto['codigo_barras']},
                'nombre': {'stringValue': producto['nombre']},
                'categoria': {'stringValue': producto['categoria']},
                'cantidad': {'integerValue': str(producto['cantidad'])},
                'unidad': {'stringValue': producto['unidad']},
                'ubicacion': {'stringValue': producto['ubicacion']},
                'marca': {'stringValue': producto.get('marca', '')},
                'imagen_url': {'stringValue': producto.get('imagen_url', '')},
            }
        }

        # Crear/actualizar documento
        url = f"{base_url}/productos/{codigo}?key={api_key}"

        try:
            response = requests.patch(url, json=firestore_doc, timeout=10)

            if response.status_code in (200, 201):
                subidos += 1
            else:
                errores += 1
                if errores <= 3:  # Solo mostrar primeros errores
                    print(f"   ✗ Error [{codigo}]: {response.status_code}")

        except requests.RequestException as e:
            errores += 1
            if errores <= 3:
                print(f"   ✗ Error [{codigo}]: {e}")

        # Progreso cada 50 productos
        if (i + 1) % 50 == 0:
            print(f"   Progreso: {i + 1}/{len(productos)} ({subidos} subidos, {errores} errores)")

        time.sleep(0.1)  # Rate limit

    print(f"\n✓ Completado: {subidos} subidos, {errores} errores")
    return subidos


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description='Importar productos de Venezuela a Firebase')
    parser.add_argument('--limit', type=int, default=None, help='Límite de productos')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar, no subir')

    args = parser.parse_args()

    print("=" * 50)
    print("SIAM - Importador de Productos")
    print("Fuente: Open Food Facts (Venezuela)")
    print("=" * 50)
    print()

    # 1. Descargar productos
    productos = descargar_productos_venezuela(limit=args.limit)

    if not productos:
        print("✗ No se encontraron productos")
        return 1

    # 2. Subir a Firebase
    subidos = subir_a_firebase(productos, dry_run=args.dry_run)

    print()
    print("=" * 50)
    if args.dry_run:
        print(f"DRY RUN completado. {len(productos)} productos listos para subir.")
        print("Ejecuta sin --dry-run para subir a Firebase.")
    else:
        print(f"Importación completada. {subidos} productos en Firebase.")
    print("=" * 50)

    return 0


if __name__ == '__main__':
    sys.exit(main())
