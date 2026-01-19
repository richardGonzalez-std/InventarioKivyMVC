# modelo/repository.py
"""
Repository Pattern para SIAM.
Orquesta las operaciones entre Firebase (remoto) y SQLite (cache local).
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from kivy.clock import Clock

from modelo.firebase_client import FirebaseClient, FIREBASE_AVAILABLE
from modelo.cache_local import CacheLocal


class ProductoRepository:
    """
    Repositorio de productos.

    Estrategia:
    - LECTURA: Cache primero → Firebase si no existe → Actualizar cache
    - ESCRITURA: Firebase primero → Cache después (o cola si offline)
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
        self.cache = CacheLocal()
        self.firebase = FirebaseClient() if FIREBASE_AVAILABLE else None
        self.is_online = False
        self._sync_in_progress = False

    def conectar(self, config_path: str = "firebase-config.json") -> bool:
        """
        Inicializa conexión con Firebase.

        Args:
            config_path: Ruta a configuración Firebase (firebase-config.json)

        Returns:
            bool: True si conectó (o si solo hay cache)
        """
        if self.firebase:
            self.is_online = self.firebase.connect(config_path)
            if self.is_online:
                # Sincronizar cache en background
                Clock.schedule_once(lambda dt: self._sync_inicial(), 1)
        return True  # Cache siempre disponible

    def _sync_inicial(self):
        """Sincroniza cache con Firebase al iniciar."""
        if self._sync_in_progress or not self.is_online:
            return

        self._sync_in_progress = True
        try:
            productos = self.firebase.get_todos_productos_sync()
            if productos:
                self.cache.sincronizar_desde_firebase(productos)
                print(f"✓ Sync inicial: {len(productos)} productos")
        except Exception as e:
            print(f"✗ Error en sync inicial: {e}")
        finally:
            self._sync_in_progress = False

    # ─────────────────────────────────────────────────────────
    # LECTURA
    # ─────────────────────────────────────────────────────────

    def buscar_por_codigo(self, codigo_barras: str, callback: Callable = None) -> Optional[Dict[str, Any]]:
        """
        Busca producto por código de barras.
        Primero cache, luego Firebase si es necesario.

        Args:
            codigo_barras: Código escaneado
            callback: Función a llamar con el resultado (para async)

        Returns:
            Dict con producto o None
        """
        # 1. Buscar en cache (inmediato)
        producto = self.cache.get_producto(codigo_barras)

        if producto:
            print(f"✓ Encontrado en cache: {codigo_barras}")
            if callback:
                callback(producto)
            return producto

        # 2. Si no está en cache y hay conexión, buscar en Firebase
        if self.is_online and self.firebase:
            print(f"→ Buscando en Firebase: {codigo_barras}")
            producto = self.firebase.get_producto_sync(codigo_barras)

            if producto:
                # Guardar en cache para próxima vez
                self.cache.guardar_producto(producto)
                print(f"✓ Encontrado en Firebase y cacheado: {codigo_barras}")

            if callback:
                callback(producto)
            return producto

        # 3. No encontrado
        print(f"✗ Producto no encontrado: {codigo_barras}")
        if callback:
            callback(None)
        return None

    def get_todos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los productos del cache."""
        return self.cache.get_todos_productos()

    def get_por_categoria(self, categoria: str) -> List[Dict[str, Any]]:
        """Obtiene productos por categoría."""
        return self.cache.get_productos_por_categoria(categoria)

    def buscar(self, termino: str) -> List[Dict[str, Any]]:
        """Busca productos por nombre o código."""
        return self.cache.buscar_productos(termino)

    # ─────────────────────────────────────────────────────────
    # ESCRITURA
    # ─────────────────────────────────────────────────────────

    def registrar_entrada(
        self,
        codigo_barras: str,
        cantidad: int,
        usuario: str,
        notas: str = "",
        callback: Callable = None
    ) -> bool:
        """
        Registra entrada de material (aumenta stock).

        Args:
            codigo_barras: Código del producto
            cantidad: Cantidad que entra
            usuario: Usuario que registra
            notas: Notas opcionales
            callback: Función a llamar al completar

        Returns:
            bool: True si se registró
        """
        return self._registrar_movimiento(
            codigo_barras, "entrada", cantidad, usuario, notas, callback
        )

    def registrar_salida(
        self,
        codigo_barras: str,
        cantidad: int,
        usuario: str,
        notas: str = "",
        callback: Callable = None
    ) -> bool:
        """
        Registra salida de material (disminuye stock).

        Args:
            codigo_barras: Código del producto
            cantidad: Cantidad que sale
            usuario: Usuario que registra
            notas: Notas opcionales
            callback: Función a llamar al completar

        Returns:
            bool: True si se registró
        """
        return self._registrar_movimiento(
            codigo_barras, "salida", cantidad, usuario, notas, callback
        )

    def _registrar_movimiento(
        self,
        codigo_barras: str,
        tipo: str,
        cantidad: int,
        usuario: str,
        notas: str,
        callback: Callable
    ) -> bool:
        """Lógica común para entrada/salida."""

        # 1. Obtener producto actual
        producto = self.buscar_por_codigo(codigo_barras)
        if not producto:
            print(f"✗ Producto no existe: {codigo_barras}")
            if callback:
                callback(False, "Producto no encontrado")
            return False

        # 2. Calcular nueva cantidad
        cantidad_actual = producto.get('cantidad', 0)
        if tipo == "entrada":
            nueva_cantidad = cantidad_actual + cantidad
        else:  # salida
            if cantidad > cantidad_actual:
                print(f"✗ Stock insuficiente: {cantidad_actual} < {cantidad}")
                if callback:
                    callback(False, f"Stock insuficiente. Disponible: {cantidad_actual}")
                return False
            nueva_cantidad = cantidad_actual - cantidad

        # 3. Actualizar en cache (inmediato)
        self.cache.actualizar_cantidad(codigo_barras, nueva_cantidad)

        # 4. Sincronizar con Firebase
        if self.is_online and self.firebase:
            try:
                # Ejecutar async en background
                asyncio.create_task(self._sync_movimiento(
                    codigo_barras, tipo, cantidad, nueva_cantidad, usuario, notas
                ))
            except RuntimeError:
                # Si no hay event loop, agregar a cola
                self._agregar_a_cola(codigo_barras, tipo, cantidad, usuario, notas)
        else:
            # Offline: agregar a cola
            self._agregar_a_cola(codigo_barras, tipo, cantidad, usuario, notas)

        print(f"✓ {tipo.capitalize()} registrada: {cantidad} x {codigo_barras}")
        if callback:
            callback(True, f"{tipo.capitalize()} registrada. Nuevo stock: {nueva_cantidad}")
        return True

    async def _sync_movimiento(
        self,
        codigo_barras: str,
        tipo: str,
        cantidad: int,
        nueva_cantidad: int,
        usuario: str,
        notas: str
    ):
        """Sincroniza movimiento con Firebase."""
        try:
            # Actualizar cantidad
            await self.firebase.actualizar_cantidad(codigo_barras, nueva_cantidad)

            # Registrar movimiento
            await self.firebase.registrar_movimiento(
                codigo_barras, tipo, cantidad, usuario, notas
            )
        except Exception as e:
            print(f"✗ Error sincronizando movimiento: {e}")
            self._agregar_a_cola(codigo_barras, tipo, cantidad, usuario, notas)

    def _agregar_a_cola(self, codigo_barras: str, tipo: str, cantidad: int, usuario: str, notas: str):
        """Agrega movimiento a cola para sincronizar después."""
        self.cache.agregar_a_cola_sync("movimiento", "movimientos", {
            'codigo_barras': codigo_barras,
            'tipo': tipo,
            'cantidad': cantidad,
            'usuario': usuario,
            'notas': notas
        })

    def crear_producto(self, producto: Dict[str, Any], callback: Callable = None) -> bool:
        """
        Crea nuevo producto.

        Args:
            producto: Dict con datos del producto
            callback: Función a llamar al completar

        Returns:
            bool: True si se creó
        """
        # Validar datos mínimos
        if not producto.get('codigo_barras') or not producto.get('nombre'):
            if callback:
                callback(False, "Código y nombre son requeridos")
            return False

        # Guardar en cache
        self.cache.guardar_producto(producto)

        # Sincronizar con Firebase
        if self.is_online and self.firebase:
            try:
                asyncio.create_task(self.firebase.crear_producto(producto.copy()))
            except RuntimeError:
                self.cache.agregar_a_cola_sync("crear", "productos", producto)
        else:
            self.cache.agregar_a_cola_sync("crear", "productos", producto)

        if callback:
            callback(True, "Producto creado")
        return True

    # ─────────────────────────────────────────────────────────
    # SINCRONIZACIÓN
    # ─────────────────────────────────────────────────────────

    def sincronizar(self, callback: Callable = None):
        """
        Sincroniza manualmente con Firebase.
        Sube operaciones pendientes y descarga cambios.
        """
        if not self.is_online:
            if callback:
                callback(False, "Sin conexión")
            return

        # 1. Procesar cola de pendientes
        cola = self.cache.get_cola_sync()
        for item in cola:
            try:
                # TODO: Procesar cada operación pendiente
                self.cache.eliminar_de_cola_sync(item['id'])
            except Exception as e:
                print(f"✗ Error procesando cola: {e}")

        # 2. Descargar productos actualizados
        self._sync_inicial()

        if callback:
            callback(True, "Sincronización completada")

    def get_estado(self) -> Dict[str, Any]:
        """Obtiene estado del repositorio."""
        stats = self.cache.get_stats()
        stats['is_online'] = self.is_online
        stats['firebase_disponible'] = FIREBASE_AVAILABLE
        return stats
