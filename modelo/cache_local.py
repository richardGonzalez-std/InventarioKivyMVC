# modelo/cache_local.py
"""
Cache local SQLite para SIAM.
Permite consultas offline y respuestas inmediatas.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from kivy.utils import platform


class CacheLocal:
    """
    Cache SQLite para almacenamiento local de productos.

    Beneficios:
    - Consultas inmediatas (sin esperar red)
    - Funciona offline
    - Se sincroniza con Firebase cuando hay conexión
    """

    _instance = None

    def __new__(cls):
        """Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.db_path = self._get_db_path()
        self.conn = None
        self._init_database()

    def _get_db_path(self) -> str:
        """Obtiene ruta de la BD según plataforma."""
        if platform == "android":
            from android.storage import app_storage_path
            return os.path.join(app_storage_path(), "siam_cache.db")
        else:
            return "siam_cache.db"

    def _init_database(self):
        """Crea tablas si no existen."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

            cursor = self.conn.cursor()

            # Tabla de productos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS productos (
                    codigo_barras TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    categoria TEXT,
                    cantidad INTEGER DEFAULT 0,
                    unidad TEXT DEFAULT 'unidades',
                    ubicacion TEXT,
                    precio_unitario REAL,
                    imagen_url TEXT,
                    fecha_sync TEXT,
                    datos_extra TEXT
                )
            ''')

            # Migración: agregar columna imagen_url si no existe
            try:
                cursor.execute('ALTER TABLE productos ADD COLUMN imagen_url TEXT')
            except sqlite3.OperationalError:
                pass  # Columna ya existe

            # Tabla de cola de sincronización (operaciones pendientes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operacion TEXT NOT NULL,
                    tabla TEXT NOT NULL,
                    datos TEXT NOT NULL,
                    fecha_creacion TEXT NOT NULL,
                    intentos INTEGER DEFAULT 0
                )
            ''')

            # Índices para búsquedas rápidas
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_categoria ON productos(categoria)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_nombre ON productos(nombre)')

            self.conn.commit()
            print(f"✓ Cache SQLite inicializado: {self.db_path}")

        except Exception as e:
            print(f"✗ Error inicializando cache: {e}")

    # ─────────────────────────────────────────────────────────
    # PRODUCTOS
    # ─────────────────────────────────────────────────────────

    def get_producto(self, codigo_barras: str) -> Optional[Dict[str, Any]]:
        """
        Busca producto por código de barras.

        Args:
            codigo_barras: Código escaneado

        Returns:
            Dict con datos o None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM productos WHERE codigo_barras = ?',
                (codigo_barras,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

        except Exception as e:
            print(f"✗ Error buscando en cache: {e}")
            return None

    def get_todos_productos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los productos del cache."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM productos ORDER BY nombre')
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            print(f"✗ Error obteniendo productos: {e}")
            return []

    def get_productos_por_categoria(self, categoria: str) -> List[Dict[str, Any]]:
        """Obtiene productos filtrados por categoría."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM productos WHERE categoria = ? ORDER BY nombre',
                (categoria,)
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            print(f"✗ Error filtrando productos: {e}")
            return []

    def buscar_productos(self, termino: str) -> List[Dict[str, Any]]:
        """Busca productos por nombre o código."""
        try:
            cursor = self.conn.cursor()
            termino_like = f"%{termino}%"
            cursor.execute('''
                SELECT * FROM productos
                WHERE nombre LIKE ? OR codigo_barras LIKE ?
                ORDER BY nombre
            ''', (termino_like, termino_like))
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            print(f"✗ Error buscando productos: {e}")
            return []

    def guardar_producto(self, producto: Dict[str, Any]) -> bool:
        """
        Guarda o actualiza producto en cache.

        Args:
            producto: Dict con datos del producto

        Returns:
            bool: True si se guardó
        """
        try:
            cursor = self.conn.cursor()

            # Extraer datos extra que no tienen columna
            datos_conocidos = ['codigo_barras', 'nombre', 'categoria',
                             'cantidad', 'unidad', 'ubicacion', 'precio_unitario', 'imagen_url']
            datos_extra = {k: v for k, v in producto.items() if k not in datos_conocidos}

            cursor.execute('''
                INSERT OR REPLACE INTO productos
                (codigo_barras, nombre, categoria, cantidad, unidad, ubicacion, precio_unitario, imagen_url, fecha_sync, datos_extra)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                producto.get('codigo_barras'),
                producto.get('nombre', ''),
                producto.get('categoria', ''),
                producto.get('cantidad', 0),
                producto.get('unidad', 'unidades'),
                producto.get('ubicacion', ''),
                producto.get('precio_unitario'),
                producto.get('imagen_url', ''),
                datetime.now().isoformat(),
                json.dumps(datos_extra) if datos_extra else None
            ))

            self.conn.commit()
            return True

        except Exception as e:
            print(f"✗ Error guardando en cache: {e}")
            return False

    def actualizar_cantidad(self, codigo_barras: str, cantidad: int) -> bool:
        """Actualiza solo la cantidad de un producto."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE productos SET cantidad = ?, fecha_sync = ? WHERE codigo_barras = ?',
                (cantidad, datetime.now().isoformat(), codigo_barras)
            )
            self.conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"✗ Error actualizando cantidad: {e}")
            return False

    def eliminar_producto(self, codigo_barras: str) -> bool:
        """Elimina producto del cache."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM productos WHERE codigo_barras = ?', (codigo_barras,))
            self.conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"✗ Error eliminando producto: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    # SINCRONIZACIÓN
    # ─────────────────────────────────────────────────────────

    def sincronizar_desde_firebase(self, productos: List[Dict[str, Any]]) -> int:
        """
        Actualiza cache con datos de Firebase.

        Args:
            productos: Lista de productos desde Firebase

        Returns:
            int: Cantidad de productos sincronizados
        """
        try:
            count = 0
            for producto in productos:
                if self.guardar_producto(producto):
                    count += 1

            print(f"✓ Cache sincronizado: {count} productos")
            return count

        except Exception as e:
            print(f"✗ Error sincronizando cache: {e}")
            return 0

    def agregar_a_cola_sync(self, operacion: str, tabla: str, datos: Dict) -> bool:
        """
        Agrega operación a cola para sincronizar cuando haya conexión.

        Args:
            operacion: "crear", "actualizar", "eliminar"
            tabla: "productos" o "movimientos"
            datos: Datos de la operación
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO sync_queue (operacion, tabla, datos, fecha_creacion)
                VALUES (?, ?, ?, ?)
            ''', (operacion, tabla, json.dumps(datos), datetime.now().isoformat()))
            self.conn.commit()
            return True

        except Exception as e:
            print(f"✗ Error agregando a cola: {e}")
            return False

    def get_cola_sync(self) -> List[Dict[str, Any]]:
        """Obtiene operaciones pendientes de sincronizar."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM sync_queue ORDER BY fecha_creacion')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            print(f"✗ Error obteniendo cola: {e}")
            return []

    def eliminar_de_cola_sync(self, id: int) -> bool:
        """Elimina operación de la cola después de sincronizar."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM sync_queue WHERE id = ?', (id,))
            self.conn.commit()
            return True

        except Exception as e:
            print(f"✗ Error eliminando de cola: {e}")
            return False

    def limpiar_cache(self) -> bool:
        """Elimina todos los datos del cache."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM productos')
            cursor.execute('DELETE FROM sync_queue')
            self.conn.commit()
            print("✓ Cache limpiado")
            return True

        except Exception as e:
            print(f"✗ Error limpiando cache: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    # UTILIDADES
    # ─────────────────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convierte fila SQLite a diccionario."""
        d = dict(row)

        # Parsear datos_extra si existe
        if d.get('datos_extra'):
            try:
                extra = json.loads(d['datos_extra'])
                d.update(extra)
            except:
                pass
            del d['datos_extra']

        return d

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache."""
        try:
            cursor = self.conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM productos')
            total_productos = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM sync_queue')
            pendientes_sync = cursor.fetchone()[0]

            return {
                'total_productos': total_productos,
                'pendientes_sync': pendientes_sync,
                'db_path': self.db_path
            }

        except Exception as e:
            print(f"✗ Error obteniendo stats: {e}")
            return {}

    def close(self):
        """Cierra conexión a la BD."""
        if self.conn:
            self.conn.close()
            print("✓ Cache cerrado")
