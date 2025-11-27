# vista/screens/camera_screen.py
"""
Pantalla de cámara con funcionalidad de captura y escaneo de códigos.

Características:
- Lazy loading de cámara (ahorro de batería)
- Captura de fotos con preview
- Escaneo de códigos de barras (QR, EAN-13, Code128, etc.)
- UI con Material Design 3
- Manejo de permisos en Android
"""

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

# Para escaneo de códigos
try:
    from pyzbar import pyzbar
    import cv2
    import numpy as np
    BARCODE_SUPPORT = True
    print("✓ Soporte de códigos de barras: ACTIVADO (pyzbar + opencv)")
except ImportError as e:
    BARCODE_SUPPORT = False
    print(f"⚠ Soporte de códigos de barras: DESACTIVADO ({e})")
    print("  Instala con: pip install pyzbar opencv-python")


class CameraScreen(MDScreen):
    """
    Pantalla de cámara con capacidades de captura y escaneo.
    
    Atributos:
        camera_widget: Instancia del widget Camera
        scanning_active: Flag para controlar el escaneo continuo
        last_scanned_code: Último código escaneado (evita duplicados)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_widget = None
        self.scanning_active = False
        self.last_scanned_code = None
        self.scan_event = None  # Referencia al evento de escaneo programado
    
    # ─────────────────────────────────────────────────────────
    # CICLO DE VIDA DE LA PANTALLA
    # ─────────────────────────────────────────────────────────
    
    def on_enter(self, *args):
        """
        Se llama cuando el usuario entra a esta pantalla.
        Inicia la cámara con lazy loading.
        """
        print("✓ Entrando a CameraScreen...")
        Clock.schedule_once(self.check_permissions_and_start_cam, 0)
    
    def on_leave(self, *args):
        """
        Se llama cuando el usuario sale de esta pantalla.
        Apaga la cámara y detiene el escaneo para ahorrar batería.
        """
        print("✓ Saliendo de CameraScreen, limpiando recursos...")
        self.stop_scanning()
        if self.camera_widget:
            self.camera_widget.play = False
            if hasattr(self, 'ids') and 'camera_container' in self.ids:
                self.ids.camera_container.remove_widget(self.camera_widget)
    
    # ─────────────────────────────────────────────────────────
    # INICIALIZACIÓN DE CÁMARA
    # ─────────────────────────────────────────────────────────
    
    def check_permissions_and_start_cam(self, *args):
        """
        Verifica permisos (Android) y crea el widget de cámara.
        
        Flujo:
        1. Verificar permisos en Android
        2. Si OK → Crear cámara y agregar controles
        3. Si NO → Mostrar mensaje de error
        """
        print("✓ Verificando permisos...")
        
        # Verificación de permisos en Android
        if platform == "android":
            from android.permissions import check_permission, Permission  # pyright: ignore
            
            if not check_permission(Permission.CAMERA):
                print("✗ Permiso de cámara denegado")
                self._show_error_message(
                    "Se necesita permiso de cámara.\n"
                    "Por favor, actívalo en Ajustes > Apps."
                )
                return
        
        # Crear cámara
        print("✓ Creando widget de cámara...")
        if not self.camera_widget:
            try:
                self.camera_widget = Camera(
                    resolution=(640, 480),
                    allow_stretch=True,
                    play=True
                )
                
                # Rotación solo en Android
                if platform == 'android':
                    with self.camera_widget.canvas.before:
                        PushMatrix()
                        Rotate(angle=-90, origin=self.camera_widget.center)
                    with self.camera_widget.canvas.after:
                        PopMatrix()
                
            except Exception as e:
                print(f"✗ Error al crear cámara: {e}")
                self._show_error_message(
                    "Error al iniciar cámara.\n"
                    "Verifica drivers o permisos."
                )
                return
        
        # Agregar cámara y controles a la UI
        self._setup_camera_ui()
    
    def _setup_camera_ui(self):
        """
        Construye la interfaz de cámara con controles.
        
        Estructura:
        - Container de cámara (arriba)
        - Barra de controles (abajo) con botones de acción
        """
        if 'camera_container' not in self.ids:
            print("⚠ Warning: camera_container no encontrado en .kv")
            return
        
        # Limpiar container
        self.ids.camera_container.clear_widgets()
        
        # Agregar cámara
        self.ids.camera_container.add_widget(self.camera_widget)
        
        # Crear barra de controles (solo si no existe)
        if 'controls_container' in self.ids:
            self._create_controls()
        
        print("✓ Cámara lista")
    
    def _create_controls(self):
        """
        Crea los botones de control de la cámara.
        
        Botones:
        - Escanear código (toggle on/off)
        - Capturar foto
        """
        controls = self.ids.controls_container
        controls.clear_widgets()
        
        # Botón: Escanear Código
        if BARCODE_SUPPORT:
            self.scan_button = MDButton(
                style="elevated",
                size_hint_x=0.5,
                on_release=self.toggle_scanning
            )
            self.scan_button.add_widget(
                MDButtonText(text="🔍 Iniciar Escaneo")
            )
            controls.add_widget(self.scan_button)
        else:
            # Mostrar botón deshabilitado si no hay soporte
            disabled_button = MDButton(
                style="elevated",
                size_hint_x=0.5,
                disabled=True
            )
            disabled_button.add_widget(
                MDButtonText(text="⚠ Pyzbar no instalado")
            )
            controls.add_widget(disabled_button)
        
        # Botón: Capturar Foto
        capture_button = MDButton(
            style="filled",
            size_hint_x=0.5,
            on_release=self.capture_photo
        )
        capture_button.add_widget(
            MDButtonText(text="📸 Capturar")
        )
        controls.add_widget(capture_button)
    
    # ─────────────────────────────────────────────────────────
    # ESCANEO DE CÓDIGOS
    # ─────────────────────────────────────────────────────────
    
    def toggle_scanning(self, *args):
        """
        Activa/desactiva el escaneo continuo de códigos.
        """
        if not BARCODE_SUPPORT:
            print("⚠ Escaneo no disponible: pyzbar no instalado")
            return
        
        if self.scanning_active:
            self.stop_scanning()
        else:
            self.start_scanning()
    
    def start_scanning(self):
        """
        Inicia el escaneo continuo de códigos de barras.
        Escanea cada 0.5 segundos.
        """
        print("✓ Escaneo ACTIVADO")
        self.scanning_active = True
        self.last_scanned_code = None
        
        # Actualizar UI del botón
        if hasattr(self, 'scan_button'):
            self.scan_button.children[0].text = "⏹ Detener Escaneo"
        
        # Programar escaneos periódicos
        self.scan_event = Clock.schedule_interval(self.scan_frame, 0.5)
    
    def stop_scanning(self):
        """
        Detiene el escaneo continuo.
        """
        if self.scanning_active:
            print("✓ Escaneo DESACTIVADO")
            self.scanning_active = False
            
            # Cancelar evento programado
            if self.scan_event:
                self.scan_event.cancel()
                self.scan_event = None
            
            # Actualizar UI del botón
            if hasattr(self, 'scan_button'):
                self.scan_button.children[0].text = "🔍 Iniciar Escaneo"
    
    def scan_frame(self, dt):
        """
        Escanea el frame actual de la cámara buscando códigos.
        
        Proceso:
        1. Capturar frame de la cámara
        2. Convertir a formato OpenCV
        3. Usar pyzbar para detectar códigos
        4. Si encuentra código → Procesar
        
        Args:
            dt: Delta time del Clock (ignorado)
        """
        if not self.camera_widget or not self.camera_widget.texture:
            return
        
        try:
            # Obtener frame de la cámara
            texture = self.camera_widget.texture
            frame = self._texture_to_numpy(texture)
            
            # Escanear códigos
            barcodes = pyzbar.decode(frame)
            
            # Procesar primer código encontrado
            if barcodes:
                for barcode in barcodes:
                    code_data = barcode.data.decode('utf-8')
                    code_type = barcode.type
                    
                    # Evitar procesar el mismo código múltiples veces
                    if code_data != self.last_scanned_code:
                        self.last_scanned_code = code_data
                        self.on_code_scanned(code_data, code_type)
                        break  # Solo procesar el primero
        
        except Exception as e:
            print(f"✗ Error en escaneo: {e}")
    
    def on_code_scanned(self, code_data, code_type):
        """
        Callback cuando se escanea un código exitosamente.
        
        Args:
            code_data: Contenido del código (string)
            code_type: Tipo de código (EAN13, QRCODE, CODE128, etc.)
        """
        print(f"✓ CÓDIGO DETECTADO: {code_data} ({code_type})")
        
        # Detener escaneo automáticamente
        self.stop_scanning()
        
        # Mostrar resultado temporalmente
        if 'status_label' in self.ids:
            self.ids.status_label.text = f"✓ Código: {code_data}"
        
        # TODO Fase 2: Buscar en inventario y mostrar detalles
        # self.search_inventory(code_data)
    
    # ─────────────────────────────────────────────────────────
    # CAPTURA DE FOTOS
    # ─────────────────────────────────────────────────────────
    
    def capture_photo(self, *args):
        """
        Captura una foto desde la cámara.
        
        Guarda la foto en memoria para procesamiento posterior.
        TODO: Implementar guardado en disco y/o envío a servidor.
        """
        if not self.camera_widget or not self.camera_widget.texture:
            print("⚠ No hay textura disponible para capturar")
            return
        
        print("✓ Capturando foto...")
        
        try:
            # Obtener textura
            texture = self.camera_widget.texture
            
            # Convertir a numpy array (para procesamiento)
            frame = self._texture_to_numpy(texture)
            
            # Actualizar status
            if 'status_label' in self.ids:
                self.ids.status_label.text = "✓ Foto capturada"
            
            print(f"✓ Foto capturada: {frame.shape}")
            
            # TODO Fase 2: Guardar foto o procesarla
            # self.save_photo(frame)
            # self.process_with_ocr(frame)
            
        except Exception as e:
            print(f"✗ Error al capturar: {e}")
            if 'status_label' in self.ids:
                self.ids.status_label.text = f"✗ Error: {str(e)}"
    
    # ─────────────────────────────────────────────────────────
    # UTILIDADES
    # ─────────────────────────────────────────────────────────
    
    def _texture_to_numpy(self, texture):
        """
        Convierte una textura de Kivy a array numpy (OpenCV).
        
        Args:
            texture: Kivy texture object
            
        Returns:
            numpy.ndarray: Imagen en formato BGR (OpenCV)
        """
        # Obtener bytes de la textura
        size = texture.size
        pixels = texture.pixels
        
        # Convertir a numpy array
        arr = np.frombuffer(pixels, dtype=np.uint8)
        arr = arr.reshape(size[1], size[0], 4)  # RGBA
        
        # Convertir RGBA a BGR (formato OpenCV)
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        
        return arr
    
    def _show_error_message(self, message):
        """
        Muestra un mensaje de error en lugar de la cámara.
        
        Args:
            message: Texto del mensaje
        """
        if 'camera_container' in self.ids:
            self.ids.camera_container.clear_widgets()
            self.ids.camera_container.add_widget(
                MDLabel(
                    text=message,
                    halign="center",
                    theme_text_color="Error"
                )
            )