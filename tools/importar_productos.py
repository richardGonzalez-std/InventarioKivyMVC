#!/usr/bin/env python3
"""
Script para importar productos a Firebase desde diversas fuentes.

Fuentes soportadas:
1. Open Food Facts (API)
2. Farmatodo.com.ve (Scraping)
3. Farmago.com.ve (Scraping)
4. Sambilonline.com (Scraping)

Uso:
    # Importar desde Open Food Facts
    python tools/importar_productos.py --source openfoodfacts [--limit N] [--dry-run]

    # Importar desde web scraping
    python tools/importar_productos.py --source <nombre_tienda> --query "<término>" [--limit N] [--dry-run]

Opciones:
    --source     Fuente de datos: openfoodfacts, farmatodo, farmago, sambil (default: openfoodfacts)
    --query      Término de búsqueda para scraping (ej: "harina pan")
    --limit N    Limitar a N productos (default: todos)
    --dry-run    Solo mostrar, no subir a Firebase
"""

import requests
import json
import time
import sys
import os
import re
from bs4 import BeautifulSoup

# Agregar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────

# --- Open Food Facts ---
OPENFOODFACTS_API = "https://world.openfoodfacts.org/api/v2/search"
COUNTRY = "venezuela"
PAGE_SIZE = 100
FIELDS = "code,product_name,brands,categories,image_url"

# Mapeo de categorías Open Food Facts → categorías SIAM
CATEGORIA_MAP = {
    "beverages": "Bebidas", "dairy": "Lácteos", "snacks": "Snacks",
    "cereals": "Cereales", "spreads": "Untables", "sauces": "Salsas",
    "canned": "Enlatados", "frozen": "Congelados", "breads": "Panadería",
    "meats": "Carnes", "fruits": "Frutas", "vegetables": "Vegetales",
    "condiments": "Condimentos", "oils": "Aceites", "pastas": "Pastas",
    "flours": "Harinas",
}

# --- Web Scraping ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
SCRAPING_TARGETS = {
    "farmatodo": {
        "url": "https://www.farmatodo.com.ve/buscar?qa={query}",
        "parser": "parse_farmatodo"
    },
    "farmago": {
        "url": "https://farmago.com.ve/?s={query}&post_type=product",
        "parser": "parse_farmago"
    },
    "sambilonline": {
        "url": "https://www.sambilonline.com/search/?q={query}",
        "parser": "parse_sambil"
    }
}

# ─────────────────────────────────────────────────────────
# PARSERS DE SCRAPING
# ─────────────────────────────────────────────────────────

def parse_farmatodo(soup, limit):
    """Parsea el HTML de Farmatodo"""
    productos = []
    items = soup.select('div.product-tile-container')

    for item in items:
        if limit and len(productos) >= limit:
            break

        try:
            name_elem = item.select_one('a.link')
            price_elem = item.select_one('span.price')
            img_elem = item.select_one('img.tile-image')
            
            if not all([name_elem, price_elem, img_elem]):
                continue

            nombre = name_elem.get_text(strip=True)
            precio_str = price_elem.get_text(strip=True).replace('Bs.', '').replace('.', '').replace(',', '.').strip()
            precio = float(re.sub(r'[^\d.]', '', precio_str))
            imagen_url = img_elem.get('src', '')
            product_id = name_elem.get('href', '').split('/')[-1]

            producto = {
                'codigo_barras': f"FARM-{product_id}",
                'nombre': nombre,
                'categoria': "Farmacia",
                'cantidad': 0,
                'unidad': 'unidades',
                'ubicacion': 'Por asignar',
                'marca': "Desconocida",
                'imagen_url': imagen_url,
                'precio': precio,
                'fuente': 'Farmatodo'
            }
            productos.append(producto)
        except (AttributeError, ValueError, TypeError) as e:
            print(f"   ! Warning: Saltando producto por error de parseo: {e}")
            continue
            
    return productos

def parse_farmago(soup, limit):
    """Parsea el HTML de Farmago"""
    productos = []
    items = soup.select('div.product-wrapper')

    for item in items:
        if limit and len(productos) >= limit:
            break
        try:
            name_elem = item.select_one('h2.woocommerce-loop-product__title')
            price_elem = item.select_one('span.price')
            img_elem = item.select_one('img.attachment-woocommerce_thumbnail')

            if not all([name_elem, price_elem, img_elem]):
                continue

            nombre = name_elem.get_text(strip=True)
            # El precio puede tener un rango, tomamos el primero
            precio_str = price_elem.find('bdi').get_text(strip=True).replace('$', '').strip()
            precio = float(re.sub(r'[^\d.]', '', precio_str))
            imagen_url = img_elem.get('src', '')
            # No hay ID claro, usamos el nombre
            product_id = re.sub(r'\W+', '', nombre).lower()[:20]

            producto = {
                'codigo_barras': f"FAGO-{product_id}",
                'nombre': nombre,
                'categoria': "Farmacia",
                'cantidad': 0,
                'unidad': 'unidades',
                'ubicacion': 'Por asignar',
                'marca': "Desconocida",
                'imagen_url': imagen_url,
                'precio': precio,
                'fuente': 'Farmago'
            }
            productos.append(producto)
        except (AttributeError, ValueError, TypeError) as e:
            print(f"   ! Warning: Saltando producto por error de parseo: {e}")
            continue
    return productos


def parse_sambil(soup, limit):
    """Parsea el HTML de Sambil Online"""
    productos = []
    items = soup.select('div.product-item-info')

    for item in items:
        if limit and len(productos) >= limit:
            break
        try:
            name_elem = item.select_one('a.product-item-link')
            price_elem = item.select_one('span.price')
            img_elem = item.select_one('img.product-image-photo')
            
            if not all([name_elem, price_elem, img_elem]):
                continue

            nombre = name_elem.get_text(strip=True)
            precio_str = price_elem.get_text(strip=True).replace('$', '').strip()
            precio = float(re.sub(r'[^\d.]', '', precio_str))
            imagen_url = img_elem.get('src', '')
            product_id = name_elem.get('href', '').split('/')[-1].replace('.html', '')

            producto = {
                'codigo_barras': f"SAM-{product_id}",
                'nombre': nombre,
                'categoria': "Tienda",
                'cantidad': 0,
                'unidad': 'unidades',
                'ubicacion': 'Por asignar',
                'marca': "Desconocida",
                'imagen_url': imagen_url,
                'precio': precio,
                'fuente': 'Sambil Online'
            }
            productos.append(producto)
        except (AttributeError, ValueError, TypeError) as e:
            print(f"   ! Warning: Saltando producto por error de parseo: {e}")
            continue

    return productos


# ─────────────────────────────────────────────────────────
# LÓGICA PRINCIPAL DE IMPORTACIÓN
# ─────────────────────────────────────────────────────────

def descargar_productos_scraping(target, query, limit=None):
    """
    Descarga productos desde un sitio web usando scraping.
    """
    if target not in SCRAPING_TARGETS:
        print(f"✗ Error: El target de scraping '{target}' no es válido.")
        return []

    config = SCRAPING_TARGETS[target]
    url = config['url'].format(query=requests.utils.quote(query))
    parser_func = globals()[config['parser']]

    print(f"📥 Scrapeando '{query}' desde {target}...")
    print(f"   URL: {url}")
    print(f"   Límite: {limit or 'Sin límite'}")

    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"✗ Error al acceder a la URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'lxml')
    productos = parser_func(soup, limit)

    print(f"\n✓ Encontrados: {len(productos)} productos válidos")
    return productos

def descargar_productos_venezuela(limit=None):
    """
    Descarga productos de Venezuela desde Open Food Facts API v2.
    """
    productos = []
    page = 1
    total_descargados = 0

    print(f"📥 Descargando productos de Venezuela desde Open Food Facts...")
    print(f"   Límite: {limit or 'Sin límite'}")
    print()

    while True:
        if limit and total_descargados >= limit:
            break

        params = {
            'countries_tags_en': COUNTRY, 'page': page,
            'page_size': PAGE_SIZE, 'fields': FIELDS,
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
            producto = formatear_producto_off(p)
            if producto:
                productos.append(producto)
                total_descargados += 1
                if limit and total_descargados >= limit:
                    break
        
        print(f"   Página {page}: {len(page_products)} productos (Total: {total_descargados})")
        page += 1
        time.sleep(0.5)

    print(f"\n✓ Descargados: {len(productos)} productos válidos")
    return productos


def formatear_producto_off(off_product):
    """
    Convierte producto de Open Food Facts al formato SIAM.
    """
    codigo = off_product.get('code', '').strip()
    nombre = off_product.get('product_name', '').strip()

    if not codigo or not nombre:
        return None

    codigo = ''.join(c for c in codigo if c.isdigit())
    if len(codigo) < 8:
        return None

    categorias_off = off_product.get('categories', '').lower()
    categoria = "General"
    for key, value in CATEGORIA_MAP.items():
        if key in categorias_off:
            categoria = value
            break

    return {
        'codigo_barras': codigo,
        'nombre': nombre[:100],
        'categoria': categoria,
        'cantidad': 0,
        'unidad': 'unidades',
        'ubicacion': 'Por asignar',
        'marca': off_product.get('brands', '')[:50],
        'imagen_url': off_product.get('image_url', ''),
        'fuente': 'OpenFoodFacts'
    }


def subir_a_firebase(productos, dry_run=False):
    """
    Sube productos a Firebase Firestore.
    """
    if dry_run:
        print("\n🔍 DRY RUN - Mostrando productos (no se subirán):")
        for i, p in enumerate(productos[:10]):
            info = f"[{p['codigo_barras']}] {p['nombre']} - {p['categoria']}"
            if 'precio' in p:
                info += f" (Bs. {p['precio']:.2f})"
            print(f"   {i+1}. {info}")
        if len(productos) > 10:
            print(f"   ... y {len(productos) - 10} más")
        return 0

    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'firebase-config.json')
    if not os.path.exists(config_path):
        print(f"✗ No se encontró {config_path}. Crea el archivo con tu 'project_id' y 'api_key'.")
        return 0

    with open(config_path) as f:
        config = json.load(f)
    project_id = config.get('project_id')
    api_key = config.get('api_key')

    if not project_id or not api_key:
        print("✗ Configuración Firebase incompleta.")
        return 0

    print(f"\n📤 Subiendo {len(productos)} productos a Firebase (Proyecto: {project_id})...")
    base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
    subidos, errores = 0, 0

    for i, producto in enumerate(productos):
        codigo = producto['codigo_barras']
        
        firestore_doc = {'fields': {
            'codigo_barras': {'stringValue': producto['codigo_barras']},
            'nombre': {'stringValue': producto['nombre']},
            'categoria': {'stringValue': producto['categoria']},
            'cantidad': {'integerValue': str(producto['cantidad'])},
            'unidad': {'stringValue': producto['unidad']},
            'ubicacion': {'stringValue': producto['ubicacion']},
            'marca': {'stringValue': producto.get('marca', '')},
            'imagen_url': {'stringValue': producto.get('imagen_url', '')},
            'fuente': {'stringValue': producto.get('fuente', 'Desconocida')}
        }}
        if 'precio' in producto:
            firestore_doc['fields']['precio'] = {'doubleValue': producto['precio']}

        url = f"{base_url}/productos/{codigo}?key={api_key}"
        try:
            # Usamos PATCH (update/create) para no sobreescribir datos existentes no incluidos
            response = requests.patch(url, json=firestore_doc, timeout=10)
            if response.status_code in (200, 201):
                subidos += 1
            else:
                errores += 1
                if errores <= 3: print(f"   ✗ Error [{codigo}]: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            errores += 1
            if errores <= 3: print(f"   ✗ Error [{codigo}]: {e}")
        
        if (i + 1) % 50 == 0:
            print(f"   Progreso: {i + 1}/{len(productos)} ({subidos} subidos, {errores} errores)")
        time.sleep(0.1)

    print(f"\n✓ Completado: {subidos} subidos, {errores} errores")
    return subidos


def main():
    """Función principal."""
    import argparse
    parser = argparse.ArgumentParser(description='Importador de Productos para SIAM')
    parser.add_argument('--source', type=str, default='openfoodfacts',
                        choices=['openfoodfacts'] + list(SCRAPING_TARGETS.keys()),
                        help='Fuente de los datos')
    parser.add_argument('--query', type=str, default=None,
                        help='Término de búsqueda para scraping')
    parser.add_argument('--limit', type=int, default=None,
                        help='Límite de productos a importar')
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo mostrar, no subir a Firebase')
    args = parser.parse_args()

    print("=" * 60)
    print("SIAM - Importador de Productos")
    print(f"Fuente: {args.source.title()}")
    print("=" * 60)
    print()

    productos = []
    if args.source == 'openfoodfacts':
        productos = descargar_productos_venezuela(limit=args.limit)
    else:
        if not args.query:
            print("✗ Error: Se requiere --query para hacer scraping.")
            return 1
        productos = descargar_productos_scraping(args.source, args.query, limit=args.limit)

    if not productos:
        print("✗ No se encontraron productos para la fuente y consulta especificadas.")
        return 1

    subidos = subir_a_firebase(productos, dry_run=args.dry_run)

    print()
    print("=" * 60)
    if args.dry_run:
        print(f"DRY RUN completado. {len(productos)} productos listos para subir.")
        print("Ejecuta sin --dry-run para subir a Firebase.")
    else:
        print(f"Importación completada. {subidos} productos en Firebase.")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
