# vista/screens/inventory_screen.py
"""
Pantalla de Inventario - Lista de productos con soporte offline.
Usa ProductoRepository que maneja cache local + Firebase.
Optimizado para carga progresiva y evitar bloqueos de UI.
"""
from kivy.properties import ListProperty, BooleanProperty, StringProperty
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDListItem, MDListItemLeadingIcon, MDListItemHeadlineText, MDListItemSupportingText, MDListItemTertiaryText

# Constantes de optimización
BATCH_SIZE = 10  # Productos a cargar por frame
BATCH_DELAY = 0.016  # ~60fps entre batches


class InventoryScreen(MDScreen):
    """
    Pantalla de inventario que muestra productos.
    Usa cache local para funcionar offline.
    """

    productos = ListProperty([])
    is_loading = BooleanProperty(False)
    error_message = StringProperty("")
    is_offline = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = None
        self._batch_event = None  # Para cancelar carga en progreso
        self._productos_pendientes = []  # Cola de productos por renderizar

    def on_enter(self, *args):
        """Carga productos cuando entra a la pantalla."""
        print(f"✓ Entrando a InventoryScreen: {self.name}")
        self.cargar_productos()

    def on_leave(self, *args):
        """Callback cuando sale de la pantalla."""
        print(f"✓ Saliendo de InventoryScreen: {self.name}")
        # Cancelar carga de batches pendientes
        if self._batch_event:
            self._batch_event.cancel()
            self._batch_event = None

    def cargar_productos(self):
        """Carga productos desde cache local y/o Firebase."""
        # Evitar múltiples cargas simultáneas
        if self.is_loading:
            return

        self.is_loading = True
        self.error_message = ""

        # Actualizar UI de carga
        self._mostrar_cargando()

        # Inicializar Repository si no existe
        if self.repository is None:
            from modelo.repository import ProductoRepository
            self.repository = ProductoRepository()
            self.repository.conectar()

        # Cargar desde cache (inmediato, funciona offline)
        self.is_offline = not self.repository.is_online
        productos_cache = self.repository.get_todos()

        if productos_cache:
            # Mostrar datos del cache inmediatamente
            self._on_productos_cargados(productos_cache)

            # Si hay conexión, sincronizar en background
            if self.repository.is_online:
                self._sync_desde_firebase()
        elif self.repository.is_online:
            # Cache vacío, intentar cargar desde Firebase
            self._sync_desde_firebase()
        else:
            # Sin cache y sin conexión
            self.is_loading = False
            self.error_message = "Sin conexión y sin datos en cache"
            self._mostrar_error()

    def _sync_desde_firebase(self):
        """Sincroniza productos desde Firebase en background."""
        if not self.repository.firebase:
            return

        self.repository.firebase.get_todos_productos_async(
            on_success=self._on_firebase_sync,
            on_error=self._on_error_carga
        )

    def _on_productos_cargados(self, productos):
        """Callback cuando se cargan los productos."""
        self.is_loading = False
        self.productos = productos or []
        modo = "offline" if self.is_offline else "online"
        print(f"✓ Cargados {len(self.productos)} productos ({modo})")

        # Actualizar lista en el hilo principal
        Clock.schedule_once(lambda dt: self._actualizar_lista())

    def _on_firebase_sync(self, productos):
        """Callback cuando llegan datos de Firebase."""
        if productos:
            # Guardar en cache local para uso offline
            self.repository.cache.sincronizar_desde_firebase(productos)
            self.is_offline = False
            print(f"✓ Sincronizados {len(productos)} productos desde Firebase")
            # Solo actualizar UI si hay cambios significativos
            if len(productos) != len(self.productos):
                self.productos = productos
                Clock.schedule_once(lambda dt: self._actualizar_lista())
        self.is_loading = False

    def _on_error_carga(self, error):
        """Callback cuando hay error de carga."""
        self.is_loading = False
        # Si ya hay productos en cache, solo mostrar warning
        if self.productos:
            print(f"⚠ Error sync Firebase (usando cache): {error}")
            self.is_offline = True
        else:
            self.error_message = str(error)
            print(f"✗ Error cargando productos: {error}")
            Clock.schedule_once(lambda dt: self._mostrar_error())

    def _mostrar_cargando(self):
        """Muestra indicador de carga."""
        lista = self.ids.get('product_list')
        if lista:
            lista.clear_widgets()
            # El spinner se muestra automáticamente vía binding en KV

    def _mostrar_error(self):
        """Muestra mensaje de error."""
        lista = self.ids.get('product_list')
        if lista:
            lista.clear_widgets()

    def _actualizar_lista(self):
        """Actualiza la lista de productos en la UI usando carga por batches."""
        lista = self.ids.get('product_list')
        if not lista:
            print("✗ No se encontró product_list")
            return

        # Cancelar carga anterior si existe
        if self._batch_event:
            self._batch_event.cancel()

        lista.clear_widgets()

        if not self.productos:
            return

        # Preparar cola de productos para carga progresiva
        self._productos_pendientes = list(self.productos)
        self._cargar_batch()

    def _cargar_batch(self, dt=None):
        """Carga un batch de productos en la UI."""
        lista = self.ids.get('product_list')
        if not lista or not self._productos_pendientes:
            self._batch_event = None
            return

        # Procesar batch actual
        batch = self._productos_pendientes[:BATCH_SIZE]
        self._productos_pendientes = self._productos_pendientes[BATCH_SIZE:]

        for producto in batch:
            item = self._crear_item_producto(producto)
            lista.add_widget(item)

        # Programar siguiente batch si quedan productos
        if self._productos_pendientes:
            self._batch_event = Clock.schedule_once(self._cargar_batch, BATCH_DELAY)
        else:
            self._batch_event = None

    def _crear_item_producto(self, producto):
        """Crea un item de lista para un producto."""
        nombre = producto.get('nombre', 'Sin nombre')
        categoria = producto.get('categoria', 'General')
        cantidad = producto.get('cantidad', 0)
        codigo = producto.get('codigo_barras', '')
        precio = producto.get('precio', 0)

        # Crear item de lista
        item = MDListItem(
            on_release=lambda x, p=producto: self._on_producto_click(p)
        )

        # Icono del producto (evita errores de imagen no encontrada)
        icon = MDListItemLeadingIcon(icon="package-variant")
        item.add_widget(icon)

        # Nombre del producto
        item.add_widget(MDListItemHeadlineText(text=nombre[:40]))

        # Categoría y código
        item.add_widget(MDListItemSupportingText(text=f"{categoria} | {codigo}"))

        # Cantidad y precio
        if precio > 0:
            terciario = f"Stock: {cantidad} | ${precio:.2f}"
        else:
            terciario = f"Stock: {cantidad}"
        item.add_widget(MDListItemTertiaryText(text=terciario))

        return item

    def _on_producto_click(self, producto):
        """Maneja click en un producto."""
        print(f"✓ Producto seleccionado: {producto.get('nombre')}")
        # TODO: Mostrar detalle o diálogo de edición

    def refrescar(self):
        """Refresca la lista de productos."""
        self.cargar_productos()
