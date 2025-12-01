# vista/screens/camera_screen.py
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.camera import Camera
from kivy.graphics.texture import Texture

# KivyMD widgets
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.boxlayout import MDBoxLayout

# Para escaneo de códigos (mantenemos tu lógica de importación)
try:
    from pyzbar import pyzbar
    import cv2
    import numpy as np
    BARCODE_SUPPORT = True
except ImportError:
    BARCODE_SUPPORT = False

class CameraScreen(MDScreen):
    """
    Pantalla de cámara con correcciones de ciclo de vida y layout.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_widget = None
        self.scanning_active = False
        self.last_scanned_code = None
        self.scan_event = None
    
    def on_enter(self, *args):
        """Inicia la cámara al entrar."""
        print("✓ Entrando a CameraScreen...")
        Clock.schedule_once(self.check_permissions_and_start_cam, 0)
    
    def on_leave(self, *args):
        """Detiene la cámara al salir para liberar recursos."""
        print("✓ Saliendo de CameraScreen...")
        self.stop_scanning()
        if self.camera_widget:
            self.camera_widget.play = False # Pausamos para ahorrar batería
            if hasattr(self, 'ids') and 'camera_container' in self.ids:
                self.ids.camera_container.remove_widget(self.camera_widget)
    
    def check_permissions_and_start_cam(self, *args):
        """Gestiona permisos e inicio de cámara."""
        
        # 1. Permisos Android
        if platform == "android":
            from android.permissions import check_permission, Permission # pyright: ignore
            if not check_permission(Permission.CAMERA):
                print("✗ Permiso de cámara denegado")
                self._show_error_message("Se necesita permiso de cámara.")
                return
        
        # 2. Crear Widget (Solo si no existe)
        if not self.camera_widget:
            print("✓ Creando nueva instancia de cámara...")
            try:
                self.camera_widget = Camera(
                    resolution=(640, 480),
                    allow_stretch=True,
                    play=True
                )
                
                # --- CORRECCIÓN 1: ROTACIÓN ---
                # Hemos eliminado la rotación manual. Kivy suele manejar esto bien ahora.
                # Si la cámara sale rotada 90 grados, avísame y aplicaremos una 
                # rotación basada en coordenadas de textura, no en canvas.before.
                
            except Exception as e:
                print(f"✗ Error al crear cámara: {e}")
                self._show_error_message("Error al iniciar cámara.")
                return
        
        # --- CORRECCIÓN 2: REINICIO ---
        # Siempre aseguramos que play sea True, incluso si el widget ya existía.
        # Esto soluciona el problema de la "imagen congelada".
        self.camera_widget.play = True
        
        # 3. Configurar UI
        self._setup_camera_ui()
    
    def _setup_camera_ui(self):
        if 'camera_container' not in self.ids:
            return
        
        self.ids.camera_container.clear_widgets()
        # Añadir el widget al layout hace que se recalcule su tamaño correctamente
        self.ids.camera_container.add_widget(self.camera_widget)
        
        if 'controls_container' in self.ids:
            self._create_controls()
            
    # ... (El resto de tus métodos: _create_controls, toggle_scanning, etc. se mantienen igual) ...
    # Copia aquí el resto de métodos (_create_controls, toggle_scanning, start_scanning, 
    # stop_scanning, scan_frame, on_code_scanned, capture_photo, _texture_to_numpy, _show_error_message)
    # tal como los tenías en tu archivo original.

    def _create_controls(self):
        """Crea los botones de control (Copia de tu código original)."""
        controls = self.ids.controls_container
        controls.clear_widgets()
        
        if BARCODE_SUPPORT:
            self.scan_button = MDButton(style="elevated", size_hint_x=0.5, on_release=self.toggle_scanning)
            self.scan_button.add_widget(MDButtonText(text="🔍 Iniciar Escaneo"))
            controls.add_widget(self.scan_button)
        else:
            disabled_button = MDButton(style="elevated", size_hint_x=0.5, disabled=True)
            disabled_button.add_widget(MDButtonText(text="⚠ Pyzbar faltante"))
            controls.add_widget(disabled_button)
        
        capture_button = MDButton(style="filled", size_hint_x=0.5, on_release=self.capture_photo)
        capture_button.add_widget(MDButtonText(text="📸 Capturar"))
        controls.add_widget(capture_button)

    def toggle_scanning(self, *args):
        if not BARCODE_SUPPORT: return
        if self.scanning_active: self.stop_scanning()
        else: self.start_scanning()

    def start_scanning(self):
        self.scanning_active = True
        self.last_scanned_code = None
        if hasattr(self, 'scan_button'): self.scan_button.children[0].text = "⏹ Detener"
        self.scan_event = Clock.schedule_interval(self.scan_frame, 0.5)

    def stop_scanning(self):
        if self.scanning_active:
            self.scanning_active = False
            if self.scan_event: self.scan_event.cancel()
            if hasattr(self, 'scan_button'): self.scan_button.children[0].text = "🔍 Iniciar Escaneo"

    def scan_frame(self, dt):
        if not self.camera_widget or not self.camera_widget.texture: return
        try:
            texture = self.camera_widget.texture
            frame = self._texture_to_numpy(texture)
            barcodes = pyzbar.decode(frame)
            if barcodes:
                for barcode in barcodes:
                    code_data = barcode.data.decode('utf-8')
                    if code_data != self.last_scanned_code:
                        self.last_scanned_code = code_data
                        self.on_code_scanned(code_data, barcode.type)
                        break
        except Exception as e:
            print(f"✗ Error scan: {e}")

    def on_code_scanned(self, code_data, code_type):
        print(f"✓ CÓDIGO: {code_data}")
        self.stop_scanning()
        if 'status_label' in self.ids: self.ids.status_label.text = f"✓ Código: {code_data}"

    def capture_photo(self, *args):
        if not self.camera_widget or not self.camera_widget.texture: return
        try:
            texture = self.camera_widget.texture
            frame = self._texture_to_numpy(texture)
            if 'status_label' in self.ids: self.ids.status_label.text = "✓ Foto capturada"
            print(f"✓ Foto OK: {frame.shape}")
        except Exception as e:
            print(f"✗ Error foto: {e}")

    def _texture_to_numpy(self, texture):
        size = texture.size
        pixels = texture.pixels
        arr = np.frombuffer(pixels, dtype=np.uint8)
        arr = arr.reshape(size[1], size[0], 4)
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

    def _show_error_message(self, message):
        if 'camera_container' in self.ids:
            self.ids.camera_container.clear_widgets()
            self.ids.camera_container.add_widget(MDLabel(text=message, halign="center", theme_text_color="Error"))