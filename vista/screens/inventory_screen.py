# vista/screens/inventory_screen.py
from kivymd.uix.screen import MDScreen


class InventoryScreen(MDScreen):
    """
    Pantalla genérica para listas de inventario.
    
    Se reutiliza para 3 secciones diferentes:
    - Consumos (víveres, papelería, etc.)
    - Mantenimiento (herramientas, equipos)
    - Oficina (mobiliario, electrónicos)
    
    El atributo 'name' (definido en el .kv) determina qué inventario mostrar.
    
    Características actuales:
    - TopAppBar con título dinámico según root.name
    - Label de placeholder (será reemplazado por RecycleView en Fase 2)
    
    TODO en Fase 2:
    - Conectar con InventoryModel
    - Implementar RecycleView para mostrar datos
    - Agregar botones de acción (añadir, editar, eliminar)
    - Implementar búsqueda/filtrado
    """
    
    def on_enter(self, *args):
        """
        Callback cuando el usuario entra a esta pantalla.
        
        Aquí cargaremos los datos del inventario correspondiente
        cuando integremos el modelo en la Fase 2.
        """
        print(f"✓ Entrando a InventoryScreen: {self.name}")
        # TODO Fase 2: Cargar datos del inventario
        # self.load_inventory_data(self.name)
    
    def on_leave(self, *args):
        """
        Callback cuando el usuario sale de esta pantalla.
        """
        print(f"✓ Saliendo de InventoryScreen: {self.name}")