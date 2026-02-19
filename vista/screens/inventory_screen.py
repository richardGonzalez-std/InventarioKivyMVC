# vista/screens/inventory_screen.py
"""
Pantalla de Inventario con RecycleView para rendimiento óptimo.
Diseño con imagen de producto estilo MDListItem.
"""
from kivy.properties import ListProperty, BooleanProperty, StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText


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

        # Stock con alerta visual (SIAM-RF-02)
        cantidad = data.get('cantidad', 0)
        stock_maximo = data.get('stock_maximo', 0)
        stock_minimo = data.get('stock_minimo', 0)
        precio = data.get('precio', 0)

        # Determinar si stock está bajo
        stock_bajo = False
        if stock_maximo > 0 and cantidad <= stock_maximo * 0.15:
            stock_bajo = True
        elif stock_minimo > 0 and cantidad <= stock_minimo:
            stock_bajo = True

        if precio > 0:
            self.stock_label.text = f"Stock: {cantidad} | ${precio:.2f}"
        else:
            self.stock_label.text = f"Stock: {cantidad}"

        if stock_bajo:
            self.stock_label.text += "  BAJO"
            self.stock_label.theme_text_color = "Custom"
            self.stock_label.text_color = (0.89, 0.11, 0.14, 1)  # Rojo CORPOELEC
        else:
            self.stock_label.theme_text_color = "Primary"

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
        # Productos ya vienen ordenados por stock desde cache_local
        self.productos = productos or []
        modo = "offline" if self.is_offline else "online"
        print(f"✓ Cargados {len(self.productos)} productos ({modo})")
        Clock.schedule_once(lambda dt: self._actualizar_recycleview())

        # SIAM-RF-02: Verificar alertas de stock bajo
        Clock.schedule_once(lambda dt: self._verificar_alertas(), 0.5)

    def _on_firebase_sync(self, productos):
        """Callback cuando llegan datos de Firebase."""
        if productos:
            self.repository.cache.sincronizar_desde_firebase(productos)
            self.is_offline = False
            print(f"✓ Sincronizados {len(productos)} productos desde Firebase")
            # Siempre actualizar UI con datos frescos de Firebase
            # Ordenar por stock descendente
            productos_ordenados = sorted(
                productos,
                key=lambda p: p.get('cantidad', 0),
                reverse=True
            )
            self.productos = productos_ordenados
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

    def _verificar_alertas(self):
        """Verifica alertas de stock bajo y vencimiento (SIAM-RF-02)."""
        if not self.repository:
            return

        alertas = self.repository.get_todas_alertas()
        stock_bajo = alertas.get('stock_bajo', [])
        por_vencer = alertas.get('por_vencer', [])

        total = len(stock_bajo) + len(por_vencer)
        if total > 0:
            partes = []
            if stock_bajo:
                partes.append(f"{len(stock_bajo)} con stock bajo")
            if por_vencer:
                partes.append(f"{len(por_vencer)} por vencer")
            mensaje = "Alertas: " + ", ".join(partes)
            MDSnackbar(
                MDSnackbarText(text=mensaje),
                y="24dp",
                pos_hint={"center_x": 0.5},
                size_hint_x=0.9,
            ).open()
            print(f"⚠ {mensaje}")

    def generar_reporte(self):
        """Genera reporte PDF del inventario (SIAM-RF-04)."""
        try:
            from modelo.reportes import generar_reporte_inventario, REPORTLAB_AVAILABLE
        except ImportError:
            MDSnackbar(
                MDSnackbarText(text="Modulo de reportes no disponible"),
                y="24dp", pos_hint={"center_x": 0.5}, size_hint_x=0.9,
            ).open()
            return

        if not REPORTLAB_AVAILABLE:
            MDSnackbar(
                MDSnackbarText(text="reportlab no instalado"),
                y="24dp", pos_hint={"center_x": 0.5}, size_hint_x=0.9,
            ).open()
            return

        if not self.productos:
            MDSnackbar(
                MDSnackbarText(text="No hay productos para reportar"),
                y="24dp", pos_hint={"center_x": 0.5}, size_hint_x=0.9,
            ).open()
            return

        try:
            from kivy.app import App
            app = App.get_running_app()
            usuario = getattr(app, 'current_user', None) or ""
            ruta = generar_reporte_inventario(self.productos, usuario)
            MDSnackbar(
                MDSnackbarText(text=f"Reporte generado: {ruta}"),
                y="24dp", pos_hint={"center_x": 0.5}, size_hint_x=0.9,
            ).open()
        except Exception as e:
            print(f"✗ Error generando reporte: {e}")
            MDSnackbar(
                MDSnackbarText(text=f"Error: {e}"),
                y="24dp", pos_hint={"center_x": 0.5}, size_hint_x=0.9,
            ).open()

    def refrescar(self):
        """Refresca la lista de productos."""
        self.cargar_productos()
