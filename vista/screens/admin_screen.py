from kivymd.uix.screen import MDScreen
from kivy.clock import Clock

class AdminScreen(MDScreen):
    """
    Controla la lógica de la pantalla de administración.
    """
    
    def __init__(self, **kwargs):
        """
        Constructor de la clase. Se ejecuta cuando creas 'AdminScreen()'.
        """
        super().__init__(**kwargs)
        
        # Como NO estamos en un ScreenManager, usamos el __init__
        # para programar la carga de datos una vez que la UI esté lista.
        Clock.schedule_once(self.cargar_datos_inicio, 0)

    def cargar_datos_inicio(self, dt):
        """
        Simula la carga de datos iniciales.
        """
        print("✓ AdminScreen inicializado. Cargando datos...")
        adminName = "Richard Gonzalez"
        self.actualizar_nombre(adminName)

    def actualizar_nombre(self, nombre):
        """
        Actualiza el label con el nombre del administrador.
        """
        # 1. Verificamos el ID correcto (admin_label)
        if 'admin_label' in self.ids:
            # 2. Asignamos al ID correcto (admin_label)
            self.ids.admin_label.text = f"Administrador: {nombre}"
            print(f"✓ Texto actualizado a: {nombre}")
        else:
            print("⚠ Error: No se encontró el ID 'admin_label' en pc.kv")