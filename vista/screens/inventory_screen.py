# vista/screens/inventory_screen.py
"""
Pantalla de Inventario - Lista de productos desde Firebase.
"""
from kivy.properties import ListProperty, BooleanProperty, StringProperty
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDListItem, MDListItemLeadingAvatar, MDListItemHeadlineText, MDListItemSupportingText, MDListItemTertiaryText


class InventoryScreen(MDScreen):
    """
    Pantalla de inventario que muestra productos desde Firebase.
    Diseño minimalista con lista de productos e imágenes.
    """

    productos = ListProperty([])
    is_loading = BooleanProperty(False)
    error_message = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.firebase = None

    def on_enter(self, *args):
        """Carga productos cuando entra a la pantalla."""
        print(f"✓ Entrando a InventoryScreen: {self.name}")
        self.cargar_productos()

    def on_leave(self, *args):
        """Callback cuando sale de la pantalla."""
        print(f"✓ Saliendo de InventoryScreen: {self.name}")

    def cargar_productos(self):
        """Carga productos desde Firebase."""
        # Evitar múltiples cargas simultáneas
        if self.is_loading:
            return

        self.is_loading = True
        self.error_message = ""

        # Actualizar UI de carga
        self._mostrar_cargando()

        # Inicializar Firebase si no está conectado
        if self.firebase is None:
            from modelo.firebase_client import FirebaseClient
            self.firebase = FirebaseClient()
            self.firebase.connect()

        if not self.firebase.is_connected:
            self.error_message = "No se pudo conectar a Firebase"
            self.is_loading = False
            self._mostrar_error()
            return

        # Fetch asíncrono
        self.firebase.get_todos_productos_async(
            on_success=self._on_productos_cargados,
            on_error=self._on_error_carga
        )

    def _on_productos_cargados(self, productos):
        """Callback cuando se cargan los productos."""
        self.is_loading = False
        self.productos = productos or []
        print(f"✓ Cargados {len(self.productos)} productos")

        # Actualizar lista en el hilo principal
        Clock.schedule_once(lambda dt: self._actualizar_lista())

    def _on_error_carga(self, error):
        """Callback cuando hay error de carga."""
        self.is_loading = False
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
        """Actualiza la lista de productos en la UI."""
        lista = self.ids.get('product_list')
        if not lista:
            print("✗ No se encontró product_list")
            return

        lista.clear_widgets()

        if not self.productos:
            return

        for producto in self.productos:
            item = self._crear_item_producto(producto)
            lista.add_widget(item)

    def _crear_item_producto(self, producto):
        """Crea un item de lista para un producto."""
        nombre = producto.get('nombre', 'Sin nombre')
        categoria = producto.get('categoria', 'General')
        cantidad = producto.get('cantidad', 0)
        codigo = producto.get('codigo_barras', '')
        imagen_url = producto.get('imagen_url', '')
        precio = producto.get('precio', 0)

        # Crear item de lista
        item = MDListItem(
            on_release=lambda x, p=producto: self._on_producto_click(p)
        )

        # Imagen del producto
        if imagen_url:
            avatar = MDListItemLeadingAvatar(source=imagen_url)
        else:
            avatar = MDListItemLeadingAvatar(source="assets/placeholder.png")
        item.add_widget(avatar)

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
