# controlador/app_controller.py
"""
Controlador principal de la aplicación de inventario.

Responsabilidades:
- Inicializar la aplicación (MDApp)
- Gestionar permisos de Android
- Coordinar la navegación entre pantallas
- Cargar la UI apropiada según la plataforma (mobile/PC)

NO define clases de UI (están en vista/screens/)
"""

from kivy.utils import platform

# Configuración ANTES de importar Kivy (solo en no-Android)
if platform != "android":
    import os
    os.environ["KIVY_NO_CONSOLELOG"] = "1"  # Desactivar logs en consola
    os.environ["KIVY_CAMERA"] = "opencv"    # Usar OpenCV para pruebas locales

# Imports de Kivy/KivyMD
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.window import Window

# Imports de widgets (solo para type hints y navegación)
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem

# Import de nuestras pantallas personalizadas
from vista.screens import CameraScreen, InventoryScreen, AdminScreen


class InventoryApp(MDApp):
    """
    Aplicación principal de inventario.
    
    Gestiona:
    - Tema Material Design 3
    - Permisos de cámara en Android
    - Navegación entre pantallas
    - Carga de UI según plataforma
    """
    
    def build(self):
        """
        Construye la interfaz de usuario.
        
        Se ejecuta UNA VEZ al iniciar la app.
        
        Comportamiento:
        - Android: Tema oscuro + vista/mobile.kv
        - Otros: Tema claro + vista/pc.kv
        
        Returns:
            Widget raíz de la aplicación
        """
        self.theme_cls.material_style = "M3"

        # Configurar Material Design 3
        # --- CONFIGURACIÓN DE COLORES CORPOELEC ---
        # Usamos el Azul Profundo como color primario de la app
        self.theme_cls.primary_palette = "Blue"  # KivyMD busca el más cercano
        
        # O podemos forzar un color específico si usamos colores personalizados:
        # self.theme_cls.primary_hue = "900" # Tono oscuro
        
        # PERO, para ser exactos con el logo, usaremos colores HEX personalizados:
        # KivyMD permite definir colores personalizados asignándolos al theme_cls
        self.theme_cls.theme_style = "Light" # Fondo claro para contraste limpio
        
        # Definimos el color primario (Azul CORPOELEC)
        self.theme_cls.primary_color = [0, 26/255, 112/255, 1] # RGB para #001A70
        
        # Definimos el color de acento (Rojo CORPOELEC) para botones de acción flotante, etc.
        self.theme_cls.accent_color = [227/255, 28/255, 35/255, 1] # RGB para #E31C23
        
        # Cargar UI según plataforma
        if platform == "android":
            print("✓ ANDROID: Construyendo UI móvil con MD3 (Dark)")
            self.theme_cls.theme_style = "Dark"
            return Builder.load_file("vista/mobile.kv")
        else:
            print("✓ DESKTOP: Construyendo UI de escritorio con MD3 (Light)")
            Window.size = (1360, 768)  # Tamaño ventana para pruebas en PC
            Window.minimum_width, Window.minimum_height = (800, 600)  # Tamaño mínimo
            Builder.load_file("vista/pc.kv")
            return AdminScreen()  # Cargar pantalla admin directamente para PC
    
    # ─────────────────────────────────────────────────────────
    # GESTIÓN DE PERMISOS ANDROID
    # ─────────────────────────────────────────────────────────
    
    def on_start(self):
        """
        Se ejecuta DESPUÉS de build(), cuando la app está lista.
        
        Este es el momento correcto para solicitar permisos
        porque la UI ya está construida.
        """
        if platform == "android":
            print("✓ ANDROID: Verificando permisos de cámara...")
            self._request_android_permissions()
        else:
            print("✓ DESKTOP: No se requieren permisos especiales")
    
    def _request_android_permissions(self):
        """
        Solicita permiso de cámara en Android.
        
        Flujo:
        1. Verificar si ya tenemos el permiso
        2. Si NO → Mostrar popup del sistema
        3. Usuario acepta/rechaza → Callback on_permissions_granted
        """
        from android.permissions import request_permissions, Permission, check_permission
        
        if not check_permission(Permission.CAMERA):
            print("✓ ANDROID: Solicitando permiso de cámara...")
            request_permissions(
                [Permission.CAMERA],
                self.on_permissions_granted
            )
        else:
            print("✓ ANDROID: Permiso de cámara ya concedido")
    
    def on_permissions_granted(self, permissions, grants):
        """
        Callback que recibe la respuesta del usuario al popup de permisos.
        
        Args:
            permissions: Lista de permisos solicitados
            grants: Lista de booleanos (True=concedido, False=denegado)
        """
        if all(grants):
            print("✓ ANDROID: ¡Permiso de cámara CONCEDIDO!")
        else:
            print("✗ ANDROID: Permiso de cámara DENEGADO")
            # TODO Fase 2: Mostrar dialog explicando por qué se necesita
    
    # ─────────────────────────────────────────────────────────
    # NAVEGACIÓN
    # ─────────────────────────────────────────────────────────
    
    def on_switch_tabs(
        self,
        bar: MDNavigationBar,
        item: MDNavigationItem,
        item_icon: str,
        item_text: str,
    ):
        """
        Handler para cambios de tab en la barra de navegación inferior.
        
        Se llama automáticamente cuando el usuario presiona un tab.
        Definido en mobile.kv: on_switch_tabs: app.on_switch_tabs(*args)
        
        Args:
            bar: Instancia de MDNavigationBar
            item: El MDNavigationItem seleccionado
            item_icon: Nombre del ícono del item
            item_text: Texto del item
        """
        screen_name = item.name  # Definido en el .kv para cada BaseMDNavigationItem
        print(f"✓ Navegando a pantalla: {screen_name}")
        self.root.ids.screen_manager.current = screen_name


# ─────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Este bloque solo se ejecuta si ejecutas directamente app_controller.py
    En producción, se ejecuta desde main.py
    """
    InventoryApp().run()