# vista/screens/inventory_screen.py
"""
Pantalla de Inventario con RecycleView para rendimiento óptimo.
Diseño con imagen de producto estilo MDListItem.
"""
from kivy.properties import ListProperty, BooleanProperty, StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard


class ProductoItem(RecycleDataViewBehavior, MDCard):
    """Item de producto para RecycleView con diseño de tarjeta."""
    index = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(88)
        self.padding = dp(8)
        self.spacing = dp(12)
        self.radius = [dp(8)]
        self.elevation = 0
        self.md_bg_color = (1, 1, 1, 1)
        self.ripple_behavior = True

        # Imagen del producto
        self.imagen = FitImage(
            source="",
            size_hint=(None, None),
            size=(dp(64), dp(64)),
            radius=[dp(8)],
        )
        self.add_widget(self.imagen)

        # Contenedor de texto
        text_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(2),
            padding=(0, dp(4), 0, dp(4)),
        )

        self.nombre_label = MDLabel(
            text="",
            font_style="Title",
            role="medium",
            adaptive_height=True,
            shorten=True,
            shorten_from="right",
        )
        self.info_label = MDLabel(
            text="",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        self.stock_label = MDLabel(
            text="",
            font_style="Label",
            role="medium",
            theme_text_color="Primary",
            adaptive_height=True,
        )

        text_box.add_widget(self.nombre_label)
        text_box.add_widget(self.info_label)
        text_box.add_widget(self.stock_label)
        self.add_widget(text_box)

    def refresh_view_attrs(self, rv, index, data):
        """Actualiza el item con nuevos datos."""
        self.index = index

        # Nombre
        self.nombre_label.text = data.get('nombre', 'Sin nombre')[:45]

        # Info
        categoria = data.get('categoria', 'General')
        codigo = data.get('codigo_barras', '')
        self.info_label.text = f"{categoria} | {codigo}"

        # Stock
        cantidad = data.get('cantidad', 0)
        precio = data.get('precio', 0)
        if precio > 0:
            self.stock_label.text = f"Stock: {cantidad} | ${precio:.2f}"
        else:
            self.stock_label.text = f"Stock: {cantidad}"

        # Imagen
        imagen_url = data.get('imagen_url', '')
        if imagen_url:
            self.imagen.source = imagen_url
        else:
            self.imagen.source = "assets/placeholder.png"

        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """Maneja click en el item."""
        if self.collide_point(*touch.pos):
            # Navegar hacia arriba para encontrar el screen
            parent = self.parent
            while parent:
                if hasattr(parent, '_on_producto_click'):
                    if hasattr(parent, 'parent') and hasattr(parent.parent, 'data'):
                        rv = parent.parent
                        if self.index < len(rv.data):
                            parent._on_producto_click(rv.data[self.index])
                    break
                if isinstance(parent, InventoryScreen):
                    rv_widget = parent.ids.get('product_rv')
                    if rv_widget and self.index < len(rv_widget.data):
                        parent._on_producto_click(rv_widget.data[self.index])
                    break
                parent = parent.parent
            return True
        return super().on_touch_down(touch)


class InventoryScreen(MDScreen):
    """
    Pantalla de inventario con RecycleView.
    Renderiza solo items visibles para máximo rendimiento.
    """

    productos = ListProperty([])
    is_loading = BooleanProperty(False)
    error_message = StringProperty("")
    is_offline = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = None

    def on_enter(self, *args):
        """Carga productos cuando entra a la pantalla."""
        print(f"✓ Entrando a InventoryScreen: {self.name}")
        self.cargar_productos()

    def on_leave(self, *args):
        """Callback cuando sale de la pantalla."""
        print(f"✓ Saliendo de InventoryScreen: {self.name}")

    def cargar_productos(self):
        """Carga productos desde cache local y/o Firebase."""
        if self.is_loading:
            return

        self.is_loading = True
        self.error_message = ""

        # Inicializar Repository si no existe
        if self.repository is None:
            from modelo.repository import ProductoRepository
            self.repository = ProductoRepository()
            self.repository.conectar()

        # Cargar desde cache (inmediato, funciona offline)
        self.is_offline = not self.repository.is_online
        productos_cache = self.repository.get_todos()

        if productos_cache:
            self._on_productos_cargados(productos_cache)
            if self.repository.is_online:
                self._sync_desde_firebase()
        elif self.repository.is_online:
            self._sync_desde_firebase()
        else:
            self.is_loading = False
            self.error_message = "Sin conexión y sin datos en cache"

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
        Clock.schedule_once(lambda dt: self._actualizar_recycleview())

    def _on_firebase_sync(self, productos):
        """Callback cuando llegan datos de Firebase."""
        if productos:
            self.repository.cache.sincronizar_desde_firebase(productos)
            self.is_offline = False
            print(f"✓ Sincronizados {len(productos)} productos desde Firebase")
            if len(productos) != len(self.productos):
                self.productos = productos
                Clock.schedule_once(lambda dt: self._actualizar_recycleview())
        self.is_loading = False

    def _on_error_carga(self, error):
        """Callback cuando hay error de carga."""
        self.is_loading = False
        if self.productos:
            print(f"⚠ Error sync Firebase (usando cache): {error}")
            self.is_offline = True
        else:
            self.error_message = str(error)
            print(f"✗ Error cargando productos: {error}")

    def _actualizar_recycleview(self):
        """Actualiza el RecycleView con los productos."""
        rv = self.ids.get('product_rv')
        if rv:
            rv.data = self.productos
            print(f"✓ RecycleView actualizado: {len(self.productos)} items")

    def _on_producto_click(self, producto):
        """Maneja click en un producto."""
        print(f"✓ Producto seleccionado: {producto.get('nombre')}")
        # TODO: Mostrar detalle o diálogo de edición

    def refrescar(self):
        """Refresca la lista de productos."""
        self.cargar_productos()
