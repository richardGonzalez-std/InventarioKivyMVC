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

# Selenium para sitios con JavaScript
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

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
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SCRAPING_TARGETS = {
    "sambilonline": {
        "url": "https://www.sambilonline.com/despensa.html?q={query}",
        "parser": "parse_sambilonline",
        "wait_selector": "li.ais-Hits-item, div.result-wrapper",
        "requires_js": True
    },
    "farmago": {
        "url": "https://www.farmago.com.ve/website/search?search={query}&order=name+asc",
        "parser": "parse_farmago",
        "wait_selector": "a.dropdown-item, div.o_search_result_item",
        "requires_js": True
    },
    "centroplaza": {
        "url": "https://centroplaza.elplazas.com/catalogsearch/result/?q={query}",
        "parser": "parse_centroplaza",
        "wait_selector": "li.product-item, div.product-item-info",
        "requires_js": True
    },
    "farmahorro": {
        "url": "https://www.farmahorro.com/search?q={query}",
        "parser": "parse_farmahorro",
        "wait_selector": "div.product-card, div.product-item",
        "requires_js": True
    },
    "locatel": {
        "url": "https://www.locatelvenezuela.com/{query}?_q={query}&map=ft",
        "parser": "parse_locatel",
        "wait_selector": "div.vtex-search-result-3-x-galleryItem, article[class*='product']",
        "requires_js": True
    }
}


def get_selenium_driver():
    """Crea un driver de Selenium con Chrome headless."""
    if not SELENIUM_AVAILABLE:
        print("✗ Selenium no está instalado. Ejecuta: pip install selenium webdriver-manager")
        return None

    try:
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        # options.add_argument('--headless')  # Comentado para debugging - descomentar en producción
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'--user-agent={USER_AGENT}')
        options.add_argument('--window-size=1920,1080')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"✗ Error creando driver Selenium: {e}")
        return None

# ─────────────────────────────────────────────────────────
# PARSERS DE SCRAPING
# ─────────────────────────────────────────────────────────

def parse_sambilonline(soup, limit):
    """Parsea el HTML de Sambil Online (Magento + Algolia)"""
    productos = []
    # Selectores para Sambil Online
    items = soup.select('li.ais-Hits-item')

    for item in items:
        if limit and len(productos) >= limit:
            break

        try:
            # Selectores Sambil Online con schema.org
            name_elem = item.select_one('h3.result-title, [itemprop="name"]')
            price_meta = item.select_one('meta[itemprop="price"]')
            img_elem = item.select_one('img[itemprop="image"]')
            url_meta = item.select_one('meta[itemprop="url"]')

            if not name_elem:
                continue

            nombre = name_elem.get_text(strip=True)

            # Precio desde meta tag (ya es número limpio en USD)
            precio = 0.0
            if price_meta:
                try:
                    precio = float(price_meta.get('content', '0'))
                except ValueError:
                    precio = 0.0

            imagen_url = img_elem.get('src', '') if img_elem else ''

            # Extraer código de barras de la URL: s1-v199791-7591002200046-229.html
            codigo_barras = ''
            if url_meta:
                url = url_meta.get('content', '')
                # Buscar patrón de 13 dígitos (código de barras EAN-13)
                match = re.search(r'-(\d{13})-', url)
                if match:
                    codigo_barras = match.group(1)
                else:
                    # Intentar extraer cualquier número largo
                    match = re.search(r'-(\d{7,14})-', url)
                    if match:
                        codigo_barras = match.group(1)

            if not codigo_barras:
                codigo_barras = f"SAMBIL-{re.sub(r'[^a-zA-Z0-9]', '', nombre)[:15]}"

            producto = {
                'codigo_barras': codigo_barras,
                'nombre': nombre[:100],
                'categoria': "General",
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
            print(f"   ! Warning: Saltando producto: {e}")
            continue

    return productos


def parse_farmago(soup, limit):
    """Parsea el HTML de Farmago (Odoo)"""
    productos = []
    # Buscar los enlaces de productos en el dropdown de búsqueda
    items = soup.select('a.dropdown-item[href*="/shop/"]')

    for item in items:
        if limit and len(productos) >= limit:
            break
        try:
            # Nombre: concatenar spans dentro de div.h6
            name_container = item.select_one('div.h6.fw-bold')
            if not name_container:
                continue

            # Obtener texto de todos los spans
            nombre = name_container.get_text(strip=True)

            # Precio: span.oe_currency_value
            price_elem = item.select_one('span.oe_currency_value')
            precio = 0.0
            if price_elem:
                precio_str = price_elem.get_text(strip=True)
                # Formato venezolano: "471,60" -> 471.60
                precio_str = precio_str.replace('.', '').replace(',', '.')
                try:
                    precio = float(precio_str) if precio_str else 0.0
                except ValueError:
                    precio = 0.0

            # Imagen
            img_elem = item.select_one('img.o_image_64_contain')
            imagen_url = ''
            if img_elem:
                src = img_elem.get('src', '')
                if src.startswith('/'):
                    imagen_url = f"https://www.farmago.com.ve{src}"
                else:
                    imagen_url = src

            # Código de barras de la URL: /shop/7591206285641-pepito-mundo-marino-x-80-gr-pepsico-70336
            href = item.get('href', '')
            codigo_barras = ''
            # Extraer el código de barras (primer número después de /shop/)
            match = re.search(r'/shop/(\d{7,14})-', href)
            if match:
                codigo_barras = match.group(1)

            if not codigo_barras:
                codigo_barras = f"FAGO-{re.sub(r'[^a-zA-Z0-9]', '', nombre)[:15]}"

            # Categoría del botón
            categoria = "General"
            cat_btn = item.select_one('button[onclick*="/shop/category/"]')
            if cat_btn:
                categoria = cat_btn.get_text(strip=True)

            producto = {
                'codigo_barras': codigo_barras,
                'nombre': nombre[:100],
                'categoria': categoria,
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
            print(f"   ! Warning: Saltando producto: {e}")
            continue
    return productos


def parse_centroplaza(soup, limit):
    """Parsea el HTML de Centro Plaza (Magento)"""
    productos = []
    items = soup.select('li.product-item, div.product-item-info, div.product-item')

    for item in items:
        if limit and len(productos) >= limit:
            break
        try:
            name_elem = item.select_one('a.product-item-link, strong.product-item-name, h2.product-name')
            price_elem = item.select_one('span.price, span[data-price-type="finalPrice"]')
            img_elem = item.select_one('img.product-image-photo, img.photo')
            link_elem = item.select_one('a.product-item-link, a[href*="/product/"]')

            if not name_elem:
                continue

            nombre = name_elem.get_text(strip=True)

            precio = 0.0
            if price_elem:
                precio_str = price_elem.get_text(strip=True)
                precio_str = re.sub(r'[^\d,.]', '', precio_str).replace(',', '.')
                try:
                    precio = float(precio_str) if precio_str else 0.0
                except ValueError:
                    precio = 0.0

            imagen_url = img_elem.get('src', '') if img_elem else ''
            product_id = link_elem.get('href', '').split('/')[-1].replace('.html', '') if link_elem else re.sub(r'\W+', '', nombre)[:15]

            producto = {
                'codigo_barras': f"CPLAZA-{product_id[:20]}",
                'nombre': nombre[:100],
                'categoria': "Tienda",
                'cantidad': 0,
                'unidad': 'unidades',
                'ubicacion': 'Por asignar',
                'marca': "Desconocida",
                'imagen_url': imagen_url,
                'precio': precio,
                'fuente': 'CentroPlaza'
            }
            productos.append(producto)
        except (AttributeError, ValueError, TypeError) as e:
            print(f"   ! Warning: Saltando producto: {e}")
            continue
    return productos


def parse_farmahorro(soup, limit):
    """Parsea el HTML de Farmahorro"""
    productos = []
    items = soup.select('div.product-card, div.product-item, article.product')

    for item in items:
        if limit and len(productos) >= limit:
            break
        try:
            name_elem = item.select_one('h2, h3, .product-name, .product-title, a[class*="product"]')
            price_elem = item.select_one('.price, .product-price, span[class*="price"]')
            img_elem = item.select_one('img')

            if not name_elem:
                continue

            nombre = name_elem.get_text(strip=True)

            precio = 0.0
            if price_elem:
                precio_str = price_elem.get_text(strip=True)
                precio_str = re.sub(r'[^\d,.]', '', precio_str).replace(',', '.')
                try:
                    precio = float(precio_str) if precio_str else 0.0
                except ValueError:
                    precio = 0.0

            imagen_url = img_elem.get('src', '') if img_elem else ''
            product_id = re.sub(r'\W+', '', nombre).lower()[:20]

            producto = {
                'codigo_barras': f"FAHO-{product_id}",
                'nombre': nombre[:100],
                'categoria': "Farmacia",
                'cantidad': 0,
                'unidad': 'unidades',
                'ubicacion': 'Por asignar',
                'marca': "Desconocida",
                'imagen_url': imagen_url,
                'precio': precio,
                'fuente': 'Farmahorro'
            }
            productos.append(producto)
        except (AttributeError, ValueError, TypeError) as e:
            print(f"   ! Warning: Saltando producto: {e}")
            continue
    return productos


def parse_locatel(soup, limit):
    """Parsea el HTML de Locatel (VTEX)"""
    productos = []
    items = soup.select('div.vtex-search-result-3-x-galleryItem, article.vtex-product-summary-2-x-element, div.vtex-product-summary-2-x-container')

    for item in items:
        if limit and len(productos) >= limit:
            break
        try:
            name_elem = item.select_one('span.vtex-product-summary-2-x-productBrand, h3, .vtex-product-summary-2-x-productNameContainer')
            price_elem = item.select_one('span.vtex-product-price-1-x-sellingPrice, span[class*="sellingPrice"], span[class*="currencyContainer"]')
            img_elem = item.select_one('img.vtex-product-summary-2-x-image, img[class*="productImage"]')
            link_elem = item.select_one('a[class*="clearLink"], a[href*="/p"]')

            if not name_elem:
                continue

            nombre = name_elem.get_text(strip=True)

            precio = 0.0
            if price_elem:
                precio_str = price_elem.get_text(strip=True)
                precio_str = re.sub(r'[^\d,.]', '', precio_str).replace(',', '.')
                try:
                    precio = float(precio_str) if precio_str else 0.0
                except ValueError:
                    precio = 0.0

            imagen_url = img_elem.get('src', '') if img_elem else ''
            product_id = link_elem.get('href', '').split('/')[-1].replace('/p', '') if link_elem else re.sub(r'\W+', '', nombre)[:15]

            producto = {
                'codigo_barras': f"LOC-{product_id[:20]}",
                'nombre': nombre[:100],
                'categoria': "Farmacia/Tienda",
                'cantidad': 0,
                'unidad': 'unidades',
                'ubicacion': 'Por asignar',
                'marca': "Desconocida",
                'imagen_url': imagen_url,
                'precio': precio,
                'fuente': 'Locatel'
            }
            productos.append(producto)
        except (AttributeError, ValueError, TypeError) as e:
            print(f"   ! Warning: Saltando producto: {e}")
            continue

    return productos


# ─────────────────────────────────────────────────────────
# LÓGICA PRINCIPAL DE IMPORTACIÓN
# ─────────────────────────────────────────────────────────

def descargar_productos_scraping(target, query, limit=None):
    """
    Descarga productos desde un sitio web usando scraping.
    Usa Selenium para sitios que requieren JavaScript.
    """
    if target not in SCRAPING_TARGETS:
        print(f"✗ Error: El target de scraping '{target}' no es válido.")
        print(f"   Targets disponibles: {', '.join(SCRAPING_TARGETS.keys())}")
        return []

    config = SCRAPING_TARGETS[target]
    url = config['url'].format(query=requests.utils.quote(query))
    parser_func = globals()[config['parser']]
    requires_js = config.get('requires_js', False)
    wait_selector = config.get('wait_selector', 'body')

    print(f"📥 Scrapeando '{query}' desde {target}...")
    print(f"   URL: {url}")
    print(f"   Método: {'Selenium (JavaScript)' if requires_js else 'Requests (HTML estático)'}")
    print(f"   Límite: {limit or 'Sin límite'}")

    html_content = None

    if requires_js:
        # Usar Selenium para sitios con JavaScript
        if not SELENIUM_AVAILABLE:
            print("✗ Este sitio requiere Selenium. Instálalo con:")
            print("   pip install selenium webdriver-manager")
            return []

        driver = get_selenium_driver()
        if not driver:
            return []

        try:
            print("   Cargando página con Selenium...")
            driver.get(url)

            # Esperar a que carguen los productos
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
                print("   ✓ Productos cargados")
            except Exception:
                print("   ! Timeout esperando productos, continuando...")

            # Scroll para cargar más productos (lazy loading)
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            html_content = driver.page_source

        except Exception as e:
            print(f"✗ Error Selenium: {e}")
            return []
        finally:
            driver.quit()
    else:
        # Usar requests para sitios estáticos
        headers = {'User-Agent': USER_AGENT}
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html_content = response.text
        except requests.RequestException as e:
            print(f"✗ Error al acceder a la URL: {e}")
            return []

    if not html_content:
        print("✗ No se pudo obtener el contenido HTML")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
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


# Consultas comunes para importación masiva
QUERIES_COMUNES = [
    "arroz", "harina", "aceite", "azucar", "pasta", "leche",
    "cafe", "atun", "sardina", "mayonesa", "salsa", "jabon",
    "shampoo", "detergente", "papel", "cereal", "galletas",
    "jugo", "refresco", "agua", "pan", "queso", "mantequilla"
]


def importar_todo(limit_por_fuente=50, limit_por_query=10, dry_run=False):
    """
    Importa productos de todas las fuentes disponibles.

    Args:
        limit_por_fuente: Límite de productos de Open Food Facts
        limit_por_query: Límite de productos por query en scraping
        dry_run: Si es True, no sube a Firebase

    Returns:
        Número total de productos subidos
    """
    todos_productos = {}  # Usar dict para evitar duplicados por código de barras

    print("=" * 60)
    print("SIAM - Importación Masiva de Productos")
    print("=" * 60)
    print()

    # 1. Open Food Facts (API)
    print("📦 [1/2] Importando desde Open Food Facts...")
    print("-" * 40)
    off_productos = descargar_productos_venezuela(limit=limit_por_fuente)
    for p in off_productos:
        todos_productos[p['codigo_barras']] = p
    print(f"   ✓ {len(off_productos)} productos de Open Food Facts")
    print()

    # 2. Scraping de todas las fuentes
    print(f"🌐 [2/2] Scrapeando {len(SCRAPING_TARGETS)} sitios...")
    print("-" * 40)

    for source_name in SCRAPING_TARGETS.keys():
        print(f"\n   📍 {source_name.upper()}")
        source_count = 0

        for query in QUERIES_COMUNES[:5]:  # Limitar a 5 queries por sitio para no sobrecargar
            try:
                productos = descargar_productos_scraping(source_name, query, limit=limit_por_query)
                for p in productos:
                    if p['codigo_barras'] not in todos_productos:
                        todos_productos[p['codigo_barras']] = p
                        source_count += 1

                if productos:
                    print(f"      '{query}': {len(productos)} productos")

            except Exception as e:
                print(f"      '{query}': Error - {e}")

            time.sleep(1)  # Pausa entre queries para no sobrecargar

        print(f"      → Total nuevos de {source_name}: {source_count}")

    # Convertir a lista
    productos_lista = list(todos_productos.values())

    print()
    print("=" * 60)
    print(f"📊 RESUMEN: {len(productos_lista)} productos únicos encontrados")
    print("=" * 60)
    print()

    # Mostrar desglose por fuente
    fuentes = {}
    for p in productos_lista:
        fuente = p.get('fuente', 'Desconocida')
        fuentes[fuente] = fuentes.get(fuente, 0) + 1

    print("Productos por fuente:")
    for fuente, count in sorted(fuentes.items(), key=lambda x: -x[1]):
        print(f"   • {fuente}: {count}")
    print()

    # Subir a Firebase
    subidos = subir_a_firebase(productos_lista, dry_run=dry_run)

    return subidos


def main():
    """Función principal."""
    import argparse
    parser = argparse.ArgumentParser(
        description='Importador de Productos para SIAM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Importar desde Open Food Facts (API oficial)
  python importar_productos.py --source openfoodfacts --limit 50 --dry-run

  # Importar desde Sambil Online (requiere Selenium)
  python importar_productos.py --source sambilonline --query "arroz" --limit 10

  # Importar desde Farmago
  python importar_productos.py --source farmago --query "pepito" --limit 10

  # IMPORTACIÓN MASIVA - Todas las fuentes automáticamente
  python importar_productos.py --all --dry-run

Requisitos para scraping:
  pip install selenium webdriver-manager
        """
    )
    parser.add_argument('--source', type=str, default='openfoodfacts',
                        choices=['openfoodfacts'] + list(SCRAPING_TARGETS.keys()),
                        help='Fuente de los datos (default: openfoodfacts)')
    parser.add_argument('--query', type=str, default=None,
                        help='Término de búsqueda (requerido para scraping)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Límite de productos a importar')
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo mostrar, no subir a Firebase')
    parser.add_argument('--all', action='store_true',
                        help='Importar de TODAS las fuentes automáticamente')
    parser.add_argument('--limit-off', type=int, default=100,
                        help='Límite de productos de Open Food Facts (default: 100)')
    parser.add_argument('--limit-query', type=int, default=10,
                        help='Límite de productos por query en scraping (default: 10)')
    args = parser.parse_args()

    # Modo importación masiva
    if args.all:
        subidos = importar_todo(
            limit_por_fuente=args.limit_off,
            limit_por_query=args.limit_query,
            dry_run=args.dry_run
        )
        print()
        print("=" * 60)
        if args.dry_run:
            print("DRY RUN completado.")
            print("Ejecuta sin --dry-run para subir a Firebase.")
        else:
            print(f"Importación masiva completada. {subidos} productos en Firebase.")
        print("=" * 60)
        return 0

    # Modo individual
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
