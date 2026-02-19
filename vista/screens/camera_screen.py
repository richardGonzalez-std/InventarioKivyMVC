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
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogSupportingText, MDDialogButtonContainer, MDDialogContentContainer
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

# Numpy siempre disponible (necesario para escaneo optimizado)
import numpy as np

# Para escaneo de códigos (PC)
try:
    from pyzbar import pyzbar
    import cv2
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

# Para escaneo en Android via ZXing Core embebido
ANDROID_SCANNER = False
_autoclass = None
_cast = None
_activity = None
_zxing_reader = None

if platform == "android":
    try:
        from jnius import autoclass as _autoclass, cast as _cast
        from android import activity as _activity

        # Importar clases ZXing Core
        _MultiFormatReader = _autoclass('com.google.zxing.MultiFormatReader')
        _BinaryBitmap = _autoclass('com.google.zxing.BinaryBitmap')
        _HybridBinarizer = _autoclass('com.google.zxing.common.HybridBinarizer')
        _RGBLuminanceSource = _autoclass('com.google.zxing.RGBLuminanceSource')
        _DecodeHintType = _autoclass('com.google.zxing.DecodeHintType')
        _BarcodeFormat = _autoclass('com.google.zxing.BarcodeFormat')
        _HashMap = _autoclass('java.util.HashMap')
        _ArrayList = _autoclass('java.util.ArrayList')

        # Crear reader con hints para todos los formatos
        _zxing_reader = _MultiFormatReader()
        hints = _HashMap()
        formats = _ArrayList()
        formats.add(_BarcodeFormat.QR_CODE)
        formats.add(_BarcodeFormat.EAN_13)
        formats.add(_BarcodeFormat.EAN_8)
        formats.add(_BarcodeFormat.UPC_A)
        formats.add(_BarcodeFormat.UPC_E)
        formats.add(_BarcodeFormat.CODE_128)
        formats.add(_BarcodeFormat.CODE_39)
        hints.put(_DecodeHintType.POSSIBLE_FORMATS, formats)
        hints.put(_DecodeHintType.TRY_HARDER, True)
        _zxing_reader.setHints(hints)

        ANDROID_SCANNER = True
        print("✓ ZXing Core inicializado")
    except Exception as e:
        print(f"⚠ ZXing Core no disponible: {e}")
        ANDROID_SCANNER = False

# Determinar soporte de escaneo
BARCODE_SUPPORT = PYZBAR_AVAILABLE or ANDROID_SCANNER

# Repositorio para búsqueda en BD
try:
    from modelo.repository import ProductoRepository
    REPOSITORY_AVAILABLE = True
except ImportError:
    REPOSITORY_AVAILABLE = False
    print("⚠ Repository no disponible")

class CameraScreen(MDScreen):
    """
    Pantalla de cámara con escaneo de códigos y búsqueda en BD.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_widget = None
        self.scanning_active = False
        self.last_scanned_code = None
        self.scan_event = None
        self.dialog = None
        self.current_producto = None
        self._camera_init_attempts = 0
        self._camera_ready = False
        self._recent_scans = []   # Últimos 5 productos escaneados [(nombre, codigo), ...]
        self._cantidad_mov = 1    # Cantidad para el movimiento actual

        # Inicializar repositorio
        if REPOSITORY_AVAILABLE:
            self.repository = ProductoRepository()
            self.repository.conectar()
        else:
            self.repository = None

    def on_enter(self, *args):
        """Inicia la cámara al entrar."""
        print("✓ Entrando a CameraScreen...")
        self._camera_init_attempts = 0
        Clock.schedule_once(self._init_camera_safe, 0.3)
        Clock.schedule_once(lambda dt: self._update_recent_bar(), 0.6)

    def _init_camera_safe(self, dt):
        """Intenta inicializar la cámara de forma segura con reintentos."""
        self._camera_init_attempts += 1

        # Verificar que el layout esté listo
        if not hasattr(self, 'ids') or 'camera_container' not in self.ids:
            if self._camera_init_attempts < 5:
                print(f"⏳ Esperando layout (intento {self._camera_init_attempts})...")
                Clock.schedule_once(self._init_camera_safe, 0.2)
            else:
                print("✗ Layout no disponible después de 5 intentos")
                self._show_error_message("Error inicializando cámara")
            return

        # Layout listo, iniciar cámara
        self.check_permissions_and_start_cam()

    def on_leave(self, *args):
        """Detiene la cámara al salir para liberar recursos."""
        print("✓ Saliendo de CameraScreen...")
        self.stop_scanning()
        self._camera_ready = False
        if self.camera_widget:
            self.camera_widget.play = False  # Pausamos para ahorrar batería
            # No remover el widget, solo pausar - esto evita problemas de reinicio
    
    def check_permissions_and_start_cam(self, *args):
        """Gestiona permisos e inicio de cámara."""

        # 1. Permisos Android
        if platform == "android":
            from android.permissions import check_permission, Permission  # pyright: ignore
            if not check_permission(Permission.CAMERA):
                print("✗ Permiso de cámara denegado")
                self._show_error_message("Se necesita permiso de cámara.")
                return

        # 2. Crear Widget (Solo si no existe)
        if not self.camera_widget:
            print("✓ Creando nueva instancia de cámara...")
            try:
                self.camera_widget = Camera(
                    #resolution=(640, 480),
                    allow_stretch=True,
                    play=False  # Empezar pausada, activar después de añadir al layout
                )

                # --- CORRECCIÓN DE ROTACIÓN PARA ANDROID ---
                if platform == "android":
                    # Rotar 90 grados en sentido horario para corregir orientación
                    with self.camera_widget.canvas.before:
                        PushMatrix()
                        self._rotation = Rotate(
                            angle=-90,
                            origin=self.camera_widget.center
                        )
                    with self.camera_widget.canvas.after:
                        PopMatrix()

                    # Actualizar origen de rotación cuando cambie el tamaño
                    self.camera_widget.bind(
                        size=self._update_rotation_origin,
                        pos=self._update_rotation_origin
                    )

            except Exception as e:
                print(f"✗ Error al crear cámara: {e}")
                self._show_error_message("Error al iniciar cámara.")
                return

        # 3. Configurar UI (añadir widget al layout)
        self._setup_camera_ui()

        # 4. Activar cámara DESPUÉS de añadir al layout (con pequeño delay)
        Clock.schedule_once(self._activate_camera, 0.1)
    
    def _setup_camera_ui(self):
        """Configura la UI de la cámara."""
        if 'camera_container' not in self.ids:
            print("✗ camera_container no encontrado")
            return

        container = self.ids.camera_container

        # Solo añadir si no está ya en el container
        if self.camera_widget.parent != container:
            container.clear_widgets()
            container.add_widget(self.camera_widget)
            print("✓ Cámara añadida al layout")

        if 'controls_container' in self.ids:
            self._create_controls()

    def _activate_camera(self, dt):
        """Activa la cámara después de que el layout esté listo."""
        if not self.camera_widget:
            return

        # Verificar que el widget tenga tamaño válido
        if self.camera_widget.width <= 0 or self.camera_widget.height <= 0:
            print("⏳ Esperando tamaño de cámara...")
            Clock.schedule_once(self._activate_camera, 0.1)
            return

        # Activar cámara
        self.camera_widget.play = True
        self._camera_ready = True
        print(f"✓ Cámara activada ({self.camera_widget.width}x{self.camera_widget.height})")

        if 'status_label' in self.ids:
            self.ids.status_label.text = "Apunte la cámara al código de barras"
            
    # ... (El resto de tus métodos: _create_controls, toggle_scanning, etc. se mantienen igual) ...
    # Copia aquí el resto de métodos (_create_controls, toggle_scanning, start_scanning, 
    # stop_scanning, scan_frame, on_code_scanned, capture_photo, _texture_to_numpy, _show_error_message)
    # tal como los tenías en tu archivo original.

    def _create_controls(self):
        """Crea botones de control grandes (UX para operación con una mano)."""
        controls = self.ids.controls_container
        controls.clear_widgets()

        if platform == "android" and ANDROID_SCANNER:
            # Botón de escaneo grande (60% ancho)
            self.scan_button = MDButton(
                style="elevated",
                size_hint=(0.6, 1),
                on_release=self.toggle_scanning_android
            )
            self.scan_button.add_widget(MDButtonText(text="ESCANEAR", bold=True))
            controls.add_widget(self.scan_button)

            # Botón manual (40% ancho)
            manual_button = MDButton(
                style="outlined",
                size_hint=(0.4, 1),
                on_release=self._entrada_manual
            )
            manual_button.add_widget(MDButtonText(text="Manual"))
            controls.add_widget(manual_button)

        elif platform == "android":
            # Android sin ZXing - botón manual a ancho completo
            manual_button = MDButton(
                style="elevated",
                size_hint=(1, 1),
                on_release=self._entrada_manual
            )
            manual_button.add_widget(MDButtonText(text="INGRESAR CÓDIGO", bold=True))
            controls.add_widget(manual_button)

        elif PYZBAR_AVAILABLE:
            # PC con pyzbar
            self.scan_button = MDButton(
                style="elevated",
                size_hint=(0.6, 1),
                on_release=self.toggle_scanning
            )
            self.scan_button.add_widget(MDButtonText(text="INICIAR ESCANEO", bold=True))
            controls.add_widget(self.scan_button)

            capture_button = MDButton(
                style="filled",
                size_hint=(0.4, 1),
                on_release=self.capture_photo
            )
            capture_button.add_widget(MDButtonText(text="Capturar"))
            controls.add_widget(capture_button)

        else:
            # PC sin pyzbar - solo entrada manual
            manual_button = MDButton(
                style="elevated",
                size_hint=(1, 1),
                on_release=self._entrada_manual
            )
            manual_button.add_widget(MDButtonText(text="INGRESAR CÓDIGO", bold=True))
            controls.add_widget(manual_button)

    def toggle_scanning_android(self, *args):
        """Toggle escaneo en Android usando ZXing Core."""
        if self.scanning_active:
            self.stop_scanning()
        else:
            self.start_scanning_android()

    def start_scanning_android(self):
        """Inicia escaneo continuo con ZXing Core."""
        print(f"[SCAN] start_scanning_android llamado. ANDROID_SCANNER={ANDROID_SCANNER}")
        self.scanning_active = True
        self.last_scanned_code = None
        self._scan_frame_count = 0
        if hasattr(self, 'scan_button'):
            self.scan_button.children[0].text = "Detener"
        if 'status_label' in self.ids:
            self.ids.status_label.text = "Escaneando..."
        # Escanear cada 500ms
        self.scan_event = Clock.schedule_interval(self.scan_frame_android, 0.5)
        print("[SCAN] Intervalo programado cada 0.5s")

    def scan_frame_android(self, dt):
        """Escanea frame actual usando ZXing Core (Optimizado con array operations)."""
        import time
        self._scan_frame_count = getattr(self, '_scan_frame_count', 0) + 1
        frame_num = self._scan_frame_count

        # 1. Validaciones iniciales
        if not self.camera_widget or not self.camera_widget.texture:
            print(f"[SCAN #{frame_num}] Sin cámara o textura")
            return
        if not ANDROID_SCANNER:
            print(f"[SCAN #{frame_num}] ANDROID_SCANNER=False")
            return
        if not _zxing_reader:
            print(f"[SCAN #{frame_num}] _zxing_reader=None")
            return

        t0 = time.time()
        try:
            texture = self.camera_widget.texture
            w = int(texture.width)
            h = int(texture.height)
            pixels = texture.pixels
            t1 = time.time()
            print(f"[SCAN #{frame_num}] Textura: {w}x{h}, pixels={len(pixels)} bytes ({(t1-t0)*1000:.0f}ms)")

            # Convertir a numpy array
            pixel_bytes = bytes(pixels) if not isinstance(pixels, bytes) else pixels
            img = np.frombuffer(pixel_bytes, dtype=np.uint8).reshape(h, w, 4)
            t2 = time.time()
            print(f"[SCAN #{frame_num}] Numpy reshape OK ({(t2-t1)*1000:.0f}ms)")

            # 3. Recorte central (ROI más pequeño para velocidad)
            crop_w = min(w, 320)
            crop_h = min(h, 240)
            start_x = (w - crop_w) // 2
            start_y = (h - crop_h) // 2

            roi = img[start_y:start_y+crop_h, start_x:start_x+crop_w]
            t3 = time.time()
            print(f"[SCAN #{frame_num}] ROI {crop_w}x{crop_h} ({(t3-t2)*1000:.0f}ms)")

            # 4. Convertir RGBA a ARGB int32 (formato Java) - operación vectorizada
            r = roi[:, :, 0].astype(np.int32)
            g = roi[:, :, 1].astype(np.int32)
            b = roi[:, :, 2].astype(np.int32)

            # ARGB con alpha=255: 0xFF000000 | (R << 16) | (G << 8) | B
            argb = (0xFF << 24) | (r << 16) | (g << 8) | b

            # Convertir a signed int32 (Java usa signed)
            argb = argb.astype(np.int32)
            t4 = time.time()
            print(f"[SCAN #{frame_num}] ARGB conversion ({(t4-t3)*1000:.0f}ms)")

            # Flatten a lista para ZXing
            pixel_array = argb.flatten().tolist()
            t5 = time.time()
            print(f"[SCAN #{frame_num}] tolist() {len(pixel_array)} elementos ({(t5-t4)*1000:.0f}ms)")

            # 5. Decodificación con ZXing
            source = _RGBLuminanceSource(crop_w, crop_h, pixel_array)
            t6 = time.time()
            print(f"[SCAN #{frame_num}] RGBLuminanceSource ({(t6-t5)*1000:.0f}ms)")

            bitmap = _BinaryBitmap(_HybridBinarizer(source))
            t7 = time.time()
            print(f"[SCAN #{frame_num}] BinaryBitmap ({(t7-t6)*1000:.0f}ms)")

            result = _zxing_reader.decodeWithState(bitmap)
            t8 = time.time()
            print(f"[SCAN #{frame_num}] decodeWithState ({(t8-t7)*1000:.0f}ms) result={result is not None}")

            if result:
                code_data = result.getText()
                code_type = result.getBarcodeFormat().toString()
                print(f"[SCAN #{frame_num}] CÓDIGO ENCONTRADO: {code_data} ({code_type})")

                if code_data and code_data != self.last_scanned_code:
                    self.last_scanned_code = code_data
                    print(f"✓ Código escaneado: {code_data} ({code_type})")
                    Clock.schedule_once(lambda dt: self.on_code_scanned(code_data, code_type), 0)

            print(f"[SCAN #{frame_num}] TOTAL: {(t8-t0)*1000:.0f}ms")

        except Exception as e:
            error_name = type(e).__name__
            if "NotFoundException" not in str(e) and "NotFoundException" not in error_name:
                print(f"[SCAN #{frame_num}] ERROR: {error_name}: {e}")
            else:
                print(f"[SCAN #{frame_num}] No code found ({(time.time()-t0)*1000:.0f}ms)")
        finally:
            if _zxing_reader:
                _zxing_reader.reset()

    def _entrada_manual(self, *args):
        """Muestra diálogo para ingresar código manualmente."""
        if self.dialog:
            self.dialog.dismiss()

        self.codigo_manual_field = MDTextField(
            MDTextFieldHintText(text="Código de barras"),
            mode="outlined",
        )

        self.dialog = MDDialog(
            MDDialogHeadlineText(text="Ingresar Código"),
            MDDialogContentContainer(
                MDBoxLayout(
                    self.codigo_manual_field,
                    orientation="vertical",
                    spacing="12dp",
                    padding="12dp",
                    adaptive_height=True,
                ),
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Cancelar"),
                    style="text",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDButton(
                    MDButtonText(text="Buscar"),
                    style="filled",
                    on_release=self._procesar_codigo_manual
                ),
                spacing="8dp",
            ),
        )
        self.dialog.open()

    def _procesar_codigo_manual(self, *args):
        """Procesa código ingresado manualmente."""
        if not hasattr(self, 'codigo_manual_field'):
            return

        codigo = self.codigo_manual_field.text.strip()

        if not codigo:
            self._mostrar_snackbar("Ingrese un código")
            return

        if self.dialog:
            self.dialog.dismiss()

        # Procesar como si fuera escaneado
        self.on_code_scanned(codigo, "MANUAL")

    def toggle_scanning(self, *args):
        if not PYZBAR_AVAILABLE: return
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
            if hasattr(self, '_scan_timeout') and self._scan_timeout:
                self._scan_timeout.cancel()
            if hasattr(self, 'scan_button'): self.scan_button.children[0].text = "Escanear"

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
        """Procesa código escaneado y busca en BD."""
        print(f"✓ CÓDIGO: {code_data} (tipo: {code_type})")
        self.stop_scanning()
        self._vibrar()  # Feedback háptico inmediato

        if 'status_label' in self.ids:
            self.ids.status_label.text = f"Buscando: {code_data}..."

        # Buscar en repositorio (cache + Firebase)
        if self.repository:
            self.repository.buscar_por_codigo(
                codigo_barras=code_data,
                callback=lambda producto: self._mostrar_resultado(producto, code_data)
            )
        else:
            self._mostrar_resultado(None, code_data)

    def _mostrar_resultado(self, producto, codigo):
        """Muestra resultado de búsqueda en diálogo."""
        if producto:
            nombre = producto.get('nombre', 'Producto')
            # Agregar a recientes (máximo 5, sin duplicados)
            entry = (nombre, codigo)
            if entry in self._recent_scans:
                self._recent_scans.remove(entry)
            self._recent_scans.insert(0, entry)
            self._recent_scans = self._recent_scans[:5]
            self._update_recent_bar()

            if 'status_label' in self.ids:
                self.ids.status_label.text = f"✓ {nombre}"
            self._mostrar_dialog_producto(producto)
        else:
            if 'status_label' in self.ids:
                self.ids.status_label.text = f"No encontrado: {codigo}"
            self._mostrar_dialog_nuevo(codigo)

    def _mostrar_dialog_producto(self, producto):
        """Diálogo simplificado con selector +/- directo (UX mejorado para almacén)."""
        if self.dialog:
            self.dialog.dismiss()

        nombre = producto.get('nombre', 'Sin nombre')
        cantidad_actual = producto.get('cantidad', 0)
        ubicacion = producto.get('ubicacion', 'No especificada')

        self.current_producto = producto
        self._cantidad_mov = 1

        # Label grande para mostrar la cantidad del movimiento
        self._mov_cantidad_label = MDLabel(
            text="1",
            halign="center",
            theme_text_color="Primary",
            font_style="Display",
            role="small",
            size_hint_x=0.35,
        )

        # Botones grandes - y +
        btn_menos = MDButton(
            style="outlined",
            size_hint=(0.3, None),
            height="68dp",
            on_release=lambda x: self._cambiar_cantidad_mov(-1),
        )
        btn_menos.add_widget(MDButtonText(text="−", bold=True))

        btn_mas = MDButton(
            style="filled",
            size_hint=(0.3, None),
            height="68dp",
            on_release=lambda x: self._cambiar_cantidad_mov(1),
        )
        btn_mas.add_widget(MDButtonText(text="+", bold=True))

        row_cantidad = MDBoxLayout(
            btn_menos,
            self._mov_cantidad_label,
            btn_mas,
            orientation="horizontal",
            size_hint_y=None,
            height="76dp",
            spacing="8dp",
        )

        info_label = MDLabel(
            text=f"Stock: {cantidad_actual}   |   {ubicacion}",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height="36dp",
            font_style="Label",
            role="large",
        )

        self.dialog = MDDialog(
            MDDialogHeadlineText(text=nombre),
            MDDialogContentContainer(
                MDBoxLayout(
                    info_label,
                    row_cantidad,
                    orientation="vertical",
                    spacing="4dp",
                    padding=["12dp", "0dp"],
                    adaptive_height=True,
                ),
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="SALIDA", bold=True),
                    style="outlined",
                    on_release=lambda x: self._confirmar_movimiento("salida"),
                ),
                MDButton(
                    MDButtonText(text="ENTRADA", bold=True),
                    style="filled",
                    on_release=lambda x: self._confirmar_movimiento("entrada"),
                ),
                spacing="8dp",
            ),
        )
        self.dialog.open()

    def _mostrar_dialog_nuevo(self, codigo):
        """Muestra diálogo para crear nuevo producto con campos requeridos."""
        if self.dialog:
            self.dialog.dismiss()

        # Campos del formulario
        self.nombre_producto_field = MDTextField(
            MDTextFieldHintText(text="Nombre del producto *"),
            mode="outlined",
        )

        self.ubicacion_field = MDTextField(
            MDTextFieldHintText(text="Ubicación física *"),
            mode="outlined",
        )

        self.cantidad_inicial_field = MDTextField(
            MDTextFieldHintText(text="Cantidad inicial"),
            mode="outlined",
            input_filter="int",
        )

        self._codigo_nuevo = codigo  # Guardar código para usar al registrar

        self.dialog = MDDialog(
            MDDialogHeadlineText(text="Registrar Producto Nuevo"),
            MDDialogSupportingText(
                text=f"Código: {codigo}"
            ),
            MDDialogContentContainer(
                MDBoxLayout(
                    self.nombre_producto_field,
                    self.ubicacion_field,
                    self.cantidad_inicial_field,
                    orientation="vertical",
                    spacing="12dp",
                    padding="12dp",
                    adaptive_height=True,
                ),
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Cancelar"),
                    style="text",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDButton(
                    MDButtonText(text="Guardar"),
                    style="filled",
                    on_release=lambda x: self._guardar_producto_nuevo()
                ),
                spacing="8dp",
            ),
        )
        self.dialog.open()

    def _mostrar_dialog_cantidad(self, tipo_movimiento):
        """Muestra diálogo para ingresar cantidad."""
        if self.dialog:
            self.dialog.dismiss()

        titulo = "Registrar Entrada" if tipo_movimiento == "entrada" else "Registrar Salida"

        # Campo de cantidad
        self.cantidad_field = MDTextField(
            MDTextFieldHintText(text="Cantidad"),
            mode="outlined",
            input_filter="int",
        )

        self.dialog = MDDialog(
            MDDialogHeadlineText(text=titulo),
            MDDialogContentContainer(
                MDBoxLayout(
                    self.cantidad_field,
                    orientation="vertical",
                    spacing="12dp",
                    padding="12dp",
                    adaptive_height=True,
                ),
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Cancelar"),
                    style="text",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDButton(
                    MDButtonText(text="Confirmar"),
                    style="filled",
                    on_release=lambda x: self._procesar_movimiento(tipo_movimiento)
                ),
                spacing="8dp",
            ),
        )
        self.dialog.open()

    def _procesar_movimiento(self, tipo):
        """Procesa entrada o salida de inventario."""
        if not self.current_producto or not hasattr(self, 'cantidad_field'):
            return

        try:
            cantidad = int(self.cantidad_field.text or 0)

            # SIAM-CP3-CU01: Validación de cantidad negativa
            if cantidad < 0:
                self._mostrar_snackbar("⚠ Error: No se permiten cantidades negativas")
                return

            if cantidad == 0:
                self._mostrar_snackbar("Ingrese una cantidad mayor a cero")
                return

        except ValueError:
            self._mostrar_snackbar("Cantidad inválida")
            return

        codigo = self.current_producto.get('codigo_barras')

        if self.dialog:
            self.dialog.dismiss()

        if self.repository:
            # Obtener usuario autenticado
            from kivy.app import App
            app = App.get_running_app()
            usuario = getattr(app, 'current_user', None) or "usuario_app"

            if tipo == "entrada":
                self.repository.registrar_entrada(
                    codigo_barras=codigo,
                    cantidad=cantidad,
                    usuario=usuario,
                    callback=lambda ok, msg: self._movimiento_completado(ok, tipo, cantidad, msg)
                )
            else:
                self.repository.registrar_salida(
                    codigo_barras=codigo,
                    cantidad=cantidad,
                    usuario=usuario,
                    callback=lambda ok, msg: self._movimiento_completado(ok, tipo, cantidad, msg)
                )
        else:
            self._mostrar_snackbar("⚠ Repositorio no disponible")

    def _movimiento_completado(self, exito, tipo, cantidad, mensaje=""):
        """Callback cuando se completa un movimiento."""
        if exito:
            emoji = "➕" if tipo == "entrada" else "➖"
            self._mostrar_snackbar(f"{emoji} {tipo.capitalize()}: {cantidad} unidades")
        else:
            self._mostrar_snackbar(mensaje or f"✗ Error al registrar {tipo}")

    def _guardar_producto_nuevo(self):
        """Guarda el producto nuevo en la base de datos."""
        if not hasattr(self, 'nombre_producto_field') or not hasattr(self, '_codigo_nuevo'):
            return

        nombre = self.nombre_producto_field.text.strip()
        ubicacion = self.ubicacion_field.text.strip() if hasattr(self, 'ubicacion_field') else ""
        cantidad_text = self.cantidad_inicial_field.text.strip() if hasattr(self, 'cantidad_inicial_field') else "0"
        codigo = self._codigo_nuevo

        # Validaciones SIAM-RF-03: Ubicación física requerida
        if not nombre:
            self._mostrar_snackbar("Ingrese el nombre del producto")
            return

        if not ubicacion:
            self._mostrar_snackbar("Ingrese la ubicación física")
            return

        # Parsear cantidad inicial
        try:
            cantidad = int(cantidad_text) if cantidad_text else 0
            if cantidad < 0:
                self._mostrar_snackbar("La cantidad no puede ser negativa")
                return
        except ValueError:
            cantidad = 0

        if self.dialog:
            self.dialog.dismiss()

        # Crear producto con campos requeridos
        producto = {
            'codigo_barras': codigo,
            'nombre': nombre,
            'cantidad': cantidad,
            'ubicacion': ubicacion,
            'categoria': 'General',
            'precio': 0,
            'stock_minimo': 0,
            'stock_maximo': 0,
        }

        # Guardar usando el repositorio
        if self.repository:
            self.repository.crear_producto(
                producto=producto,
                callback=lambda ok, msg: self._on_producto_creado(ok, msg, nombre)
            )
        else:
            self._mostrar_snackbar("Error: Repositorio no disponible")

    def _on_producto_creado(self, exito, mensaje, nombre):
        """Callback cuando se crea un producto."""
        if exito:
            self._mostrar_snackbar(f"Producto '{nombre}' registrado")
            print(f"✓ Producto creado: {nombre}")
        else:
            self._mostrar_snackbar(f"Error: {mensaje}")
            print(f"✗ Error creando producto: {mensaje}")

    def _cambiar_cantidad_mov(self, delta):
        """Cambia la cantidad del movimiento (+/-)."""
        self._cantidad_mov = max(1, self._cantidad_mov + delta)
        if hasattr(self, '_mov_cantidad_label'):
            self._mov_cantidad_label.text = str(self._cantidad_mov)

    def _confirmar_movimiento(self, tipo):
        """Procesa entrada o salida directamente desde el diálogo simplificado."""
        if not self.current_producto:
            return

        cantidad = self._cantidad_mov
        codigo = self.current_producto.get('codigo_barras')

        if self.dialog:
            self.dialog.dismiss()

        if self.repository:
            from kivy.app import App
            app = App.get_running_app()
            usuario = getattr(app, 'current_user', None) or "usuario_app"

            if tipo == "entrada":
                self.repository.registrar_entrada(
                    codigo_barras=codigo,
                    cantidad=cantidad,
                    usuario=usuario,
                    callback=lambda ok, msg: self._movimiento_completado(ok, tipo, cantidad, msg)
                )
            else:
                self.repository.registrar_salida(
                    codigo_barras=codigo,
                    cantidad=cantidad,
                    usuario=usuario,
                    callback=lambda ok, msg: self._movimiento_completado(ok, tipo, cantidad, msg)
                )
        else:
            self._mostrar_snackbar("Repositorio no disponible")

    def _vibrar(self, duracion_ms=80):
        """Vibración háptica al escanear (solo Android)."""
        if platform != "android":
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            vibrator = activity.getSystemService('vibrator')
            if vibrator and vibrator.hasVibrator():
                vibrator.vibrate(duracion_ms)
        except Exception as e:
            print(f"⚠ Vibración: {e}")

    def _update_recent_bar(self):
        """Actualiza la barra horizontal de recientes."""
        if 'recent_bar' not in self.ids:
            return

        bar = self.ids.recent_bar
        bar.clear_widgets()

        if not self._recent_scans:
            hint = MDLabel(
                text="Recientes aparecerán aquí",
                theme_text_color="Hint",
                font_style="Label",
                role="small",
                size_hint_x=None,
                width="220dp",
                halign="center",
            )
            bar.add_widget(hint)
            return

        for nombre, codigo in self._recent_scans:
            texto = nombre[:14] + "…" if len(nombre) > 14 else nombre
            chip = MDButton(
                style="tonal",
                size_hint=(None, None),
                height="36dp",
                width="130dp",
                on_release=lambda x, c=codigo: self.on_code_scanned(c, "RECIENTE"),
            )
            chip.add_widget(MDButtonText(text=texto, font_size="11sp"))
            bar.add_widget(chip)

    def _mostrar_snackbar(self, mensaje):
        """Muestra mensaje snackbar."""
        MDSnackbar(
            MDSnackbarText(text=mensaje),
            y="24dp",
            pos_hint={"center_x": 0.5},
            size_hint_x=0.9,
        ).open()

    def _mostrar_menu_usuario(self):
        """Muestra información del usuario actual."""
        from kivy.app import App
        app = App.get_running_app()
        usuario = getattr(app, 'current_user', None) or "Sin sesión"
        self._mostrar_snackbar(f"Usuario: {usuario}")

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
        """Convierte textura Kivy a numpy array (requiere cv2/numpy)."""
        if not PYZBAR_AVAILABLE:
            return None
        size = texture.size
        pixels = texture.pixels
        arr = np.frombuffer(pixels, dtype=np.uint8)
        arr = arr.reshape(size[1], size[0], 4)
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

    def _show_error_message(self, message):
        if 'camera_container' in self.ids:
            self.ids.camera_container.clear_widgets()
            self.ids.camera_container.add_widget(MDLabel(text=message, halign="center", theme_text_color="Error"))

    def _update_rotation_origin(self, *args):
        """Actualiza el origen de rotación cuando cambia el tamaño del widget."""
        if hasattr(self, '_rotation') and self.camera_widget:
            self._rotation.origin = self.camera_widget.center