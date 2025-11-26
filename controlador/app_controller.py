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
# --- Clases de Python para las Pantallas ---

class BaseMDNavigationItem(MDNavigationItem):
    """Clase base para el ítem de navegación."""
    pass




# --- Clase Principal de la Aplicación ---

class InventoryApp(MDApp):
    
    def build(self):
        self.theme_cls.material_style = "M3"
        # Cargar el KV es AHORA SEGURO, porque no hay <Camera> en él.
        if platform == "android":
            print("ANDROID: Construyendo la aplicación con Material Design 3.")
            self.theme_cls.theme_style = "Dark"
            return Builder.load_file("vista/mobile.kv")
        else:
            self.theme_cls.theme_style = "Light"
            return Builder.load_file("vista/pc.kv")

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