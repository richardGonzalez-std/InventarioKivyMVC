from kivy.utils import platform
if platform != "android":
    import os
    os.environ["KIVY_NO_CONSOLELOG"] = "1"  # Desactivar logs en consola si no es Android
    os.environ["KIVY_CAMERA"] = "opencv"  # Usar OpenCV en no-Android para pruebas locales
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.camera import Camera
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
import textwrap
  # Importación clave para verificar la plataforma
# --- IMPORTACIONES DE MATERIAL DESIGN 3 ---
from kivymd.uix.appbar import (
    MDTopAppBar,
    MDTopAppBarLeadingButtonContainer,
    MDTopAppBarTitle,
    MDActionTopAppBarButton
)
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
# ------------------------------------------

# --- Definición de la Interfaz (KV) ---
KV_STRING = textwrap.dedent("""
# 1. Definimos el 'BaseMDNavigationItem'
<BaseMDNavigationItem>:
    icon: "camera-document"
    text: "Scanner"

    MDNavigationItemIcon:
        icon: root.icon

    MDNavigationItemLabel:
        text: root.text


# 2. Definimos la PANTALLA DE CÁMARA (¡MODIFICADA!)
<CameraScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            type: "small"
            MDTopAppBarTitle:
                text: "Cámara de Inventario"
                halign: "center"
        
        # Este es el contenedor vacío donde pondremos la cámara
        # usando código Python, DESPUÉS de tener el permiso.
        MDBoxLayout:
            id: camera_placeholder


# 3. Definimos la PANTALLA DE INVENTARIO (reutilizable)
<InventoryScreen>:
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            id: inventory_toolbar
            type: "small"
            MDTopAppBarTitle:
                text: root.name.capitalize() 
                halign: "center"
        
        MDLabel:
            text: f"Contenido de {root.name}"
            halign: "center"


# 4. Definimos el WIDGET RAÍZ de la aplicación
MDBoxLayout:
    orientation: "vertical"
    md_bg_color: self.theme_cls.backgroundColor

    MDScreenManager:
        id: screen_manager

        CameraScreen:
            name: "camera"

        InventoryScreen:
            name: "consumos"

        InventoryScreen:
            name: "mantenimiento"

        InventoryScreen:
            name: "oficina"

    MDNavigationBar:
        on_switch_tabs: app.on_switch_tabs(*args)

        BaseMDNavigationItem:
            name: "camera"
            text: "Cámara"
            icon: "camera"
            active: True

        BaseMDNavigationItem:
            name: "consumos"
            text: "Consumos"
            icon: "food-apple"

        BaseMDNavigationItem:
            name: "mantenimiento"
            text: "Mantenimiento"
            icon: "wrench"
            
        BaseMDNavigationItem:
            name: "oficina"
            text: "Oficina"
            icon: "desktop-tower"
""")

# --- Clases de Python para las Pantallas ---

class BaseMDNavigationItem(MDNavigationItem):
    """Clase base para el ítem de navegación."""
    pass

class CameraScreen(MDScreen):
    """
    Controla la lógica de la pantalla de la cámara.
    ¡MODIFICADA PARA CARGA DIFERIDA (LAZY LOADING)!
    """
    camera_widget = None  # Guardaremos una referencia a la cámara aquí

    def on_enter(self, *args):
        """
        Se llama CADA VEZ que el usuario entra a esta pantalla.
        Usamos Clock.schedule_once para evitar el crash de 'ids'.
        """
        print("Entrando a CameraScreen, programando chequeo de permisos...")
        # Retrasamos la lógica por un frame (0 segundos) para dar tiempo a Kivy
        # de poblar el diccionario self.ids.
        Clock.schedule_once(self.check_permissions_and_start_cam, 0)

    def check_permissions_and_start_cam(self, *args):
        """
        Esta es la lógica que se ejecutará en el siguiente frame.
        Ahora self.ids.camera_placeholder SÍ existirá.
        """
        print("Chequeando permisos e iniciando cámara...")
        
        # 1. Comprobar si estamos en Android
        if platform == "android":
            from android.permissions import check_permission, Permission
            # 2. Comprobar si el permiso fue concedido (en on_start)
            if not check_permission(Permission.CAMERA):
                print("PERMISO DENEGADO. Mostrando mensaje de error.")
                self.ids.camera_placeholder.clear_widgets()
                self.ids.camera_placeholder.add_widget(
                    MDLabel(
                        text="Se necesita permiso de cámara para continuar.\n"
                             "Por favor, concédelo en los ajustes de la app.",
                        halign="center"
                    )
                )
                return  # Salir de la función si no hay permiso

        # 3. Si el permiso está OK (o no estamos en Android), crear la cámara
        print("Permiso OK. Creando e iniciando la cámara...")
        if not self.camera_widget:
            try:
                self.camera_widget = Camera(resolution=(640, 480), allow_stretch=True)
                self.camera_widget.play = True # Asegurar que play sea True
            except Exception as e:
                print(f"Error iniciando cámara: {e}")
                self.ids.camera_placeholder.add_widget(
                    MDLabel(text="Error al iniciar cámara.\nVerifica drivers.", halign="center")
                )
                return

        self.ids.camera_placeholder.clear_widgets()
        self.ids.camera_placeholder.add_widget(self.camera_widget)
        
        # Rotación SOLO para Android
        if platform == 'android':
            with self.camera_widget.canvas.before:
                PushMatrix()
                Rotate(angle=-90, origin=self.camera_widget.center)
            with self.camera_widget.canvas.after:
                PopMatrix()

    def on_leave(self, *args):
        """
        Se llama CADA VEZ que el usuario sale de esta pantalla.
        Es CRUCIAL para apagar la cámara y ahorrar batería.
        """
        print("Saliendo de CameraScreen, apagando y eliminando la cámara.")
        if self.camera_widget:
            self.camera_widget.play = False
            self.ids.camera_placeholder.remove_widget(self.camera_widget)
            # Opcional: destruir el widget si la memoria es un problema
            # self.camera_widget = None


class InventoryScreen(MDScreen):
    """Pantalla genérica para las listas de inventario."""
    pass


# --- Clase Principal de la Aplicación ---

class InventoryApp(MDApp):
    
    def build(self):
        self.theme_cls.material_style = "M3"
        # Cargar el KV es AHORA SEGURO, porque no hay <Camera> en él.
        return Builder.load_string(KV_STRING)

    # --- INICIO DEL NUEVO CÓDIGO DE PERMISOS ---
    def on_start(self):
        """
        Se llama al iniciar la app, DESPUÉS de build().
        Este es el lugar correcto para pedir permisos.
        """
        if platform == "android":
            print("ANDROID: Verificando permisos de cámara...")
            from android.permissions import request_permissions, Permission, check_permission
            
            # Comprueba si ya tenemos el permiso
            if not check_permission(Permission.CAMERA):
                print("ANDROID: No hay permiso, solicitándolo...")
                # Pide el permiso (esto mostrará el pop-up)
                request_permissions(
                    [Permission.CAMERA], 
                    self.on_permissions_granted
                )
            else:
                print("ANDROID: El permiso de cámara ya estaba concedido.")
        else:
            print("Plataforma no es Android, no se piden permisos.")

    def on_permissions_granted(self, permissions, grants):
        """
        Callback que se llama cuando el usuario responde al pop-up.
        """
        if all(grants):
            print("ANDROID: ¡Permiso de cámara CONCEDIDO!")
        else:
            print("ANDROID: Permiso de cámara DENEGADO.")
            # Aquí podrías mostrar un pop-up informando al usuario
    # --- FIN DEL NUEVO CÓDIGO DE PERMISOS ---

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