from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.camera import Camera
import textwrap
# --- IMPORTACIONES DE MATERIAL DESIGN 3 ---
# De 'appbar' importamos la barra superior y sus componentes
from kivymd.uix.appbar import (
    MDTopAppBar,
    MDTopAppBarLeadingButtonContainer,
    MDTopAppBarTitle,
    MDActionTopAppBarButton
)
# De 'navigationbar' importamos la barra inferior y sus ítems
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
# ------------------------------------------


# --- Definición de la Interfaz (KV) ---
KV_STRING = textwrap.dedent("""
# 1. Definimos el 'BaseMDNavigationItem' de tu ejemplo
#    para crear los botones de la barra inferior.
<BaseMDNavigationItem>:
    icon: "camera-document"
    text: "Scanner"

    MDNavigationItemIcon:
        icon: root.icon

    MDNavigationItemLabel:
        text: root.text


# 2. Definimos la PANTALLA DE CÁMARA
<CameraScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            type: "small"
            MDTopAppBarTitle:
                text: "Cámara de Inventario"
                halign: "center"
        
        Camera:
            id: camera_widget
            resolution: (640, 480)
            allow_stretch: True


# 3. Definimos la PANTALLA DE INVENTARIO (reutilizable)
<InventoryScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            id: inventory_toolbar
            type: "small"
            MDTopAppBarTitle:
                # El título se establecerá desde Python
                text: root.name.capitalize() 
                halign: "center"
        
        MDLabel:
            text: f"Contenido de {root.name}"
            halign: "center"


# 4. Definimos el WIDGET RAÍZ de la aplicación
MDBoxLayout:
    orientation: "vertical"
    md_bg_color: self.theme_cls.backgroundColor

    # El área principal de contenido
    MDScreenManager:
        id: screen_manager

        CameraScreen:
            name: "camera" # Este 'name' debe coincidir con el ítem de la barra

        InventoryScreen:
            name: "consumos"

        InventoryScreen:
            name: "mantenimiento"

        InventoryScreen:
            name: "oficina"

    # La barra de navegación en la parte inferior
    MDNavigationBar:
        # Llama a la función 'on_switch_tabs' de la app
        on_switch_tabs: app.on_switch_tabs(*args)

        BaseMDNavigationItem:
            name: "camera" # 'name' coincide con la pantalla
            text: "Cámara"
            icon: "camera"
            active: True # La pantalla por defecto

        BaseMDNavigationItem:
            name: "consumos" # 'name' coincide con la pantalla
            text: "Consumos"
            icon: "food-apple"

        BaseMDNavigationItem:
            name: "mantenimiento" # 'name' coincide con la pantalla
            text: "Mantenimiento"
            icon: "wrench"
            
        BaseMDNavigationItem:
            name: "oficina" # 'name' coincide con la pantalla
            text: "Oficina"
            icon: "desktop-tower"
""")

# --- Clases de Python para las Pantallas ---

class BaseMDNavigationItem(MDNavigationItem):
    """Clase base para el ítem de navegación (de tu ejemplo)."""
    pass

class CameraScreen(MDScreen):
    """Controla la lógica de la pantalla de la cámara."""
    def on_enter(self, *args):
        print("Iniciando cámara...")
        try:
            self.ids.camera_widget.play = True
        except Exception as e:
            print(f"Error al iniciar cámara: {e}")

    def on_leave(self, *args):
        print("Deteniendo cámara...")
        try:
            self.ids.camera_widget.play = False
        except Exception as e:
            print(f"Error al detener cámara: {e}")

class InventoryScreen(MDScreen):
    """Pantalla genérica para las listas de inventario."""
    pass


# --- Clase Principal de la Aplicación ---

class InventoryApp(MDApp):
    
    def build(self):
        self.theme_cls.material_style = "M3"
        # Opcional: Establece los colores
        # self.theme_cls.primary_palette = "Green"
        return Builder.load_string(KV_STRING)

    def on_switch_tabs(
        self,
        bar: MDNavigationBar,
        item: MDNavigationItem,
        item_icon: str,
        item_text: str,
    ):
        """
        Se llama cada vez que se presiona un ítem de la barra inferior.
        
        Usamos 'item.name' (que definimos en el KV) para cambiar de pantalla.
        """
        print(f"Cambiando a pantalla: {item.name}")
        self.root.ids.screen_manager.current = item.name

if __name__ == "__main__":
    InventoryApp().run()