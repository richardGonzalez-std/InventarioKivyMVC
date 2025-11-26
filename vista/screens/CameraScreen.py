from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.camera import Camera

# KivyMD widgets
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
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
