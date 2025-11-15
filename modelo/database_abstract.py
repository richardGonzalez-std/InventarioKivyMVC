# /model/database_abstract.py
from abc import ABC, abstractmethod

class DatabaseInterface(ABC):
    """
    Define la interfaz que cualquier clase de base de datos debe implementar.
    Esto nos permite cambiar de 'database_dummy' a 'database_firebase'
    sin cambiar el controlador o el modelo.
    """

    @abstractmethod
    def connect(self, user_id):
        """Inicializa la conexión o autentica al usuario."""
        pass

    @abstractmethod
    def get_item(self, collection, item_id):
        """Obtiene un solo artículo de la base de datos."""
        pass

    @abstractmethod
    def get_inventory_list(self, collection):
        """Obtiene una lista de todos los artículos en una colección."""
        pass

    @abstractmethod
    def get_history_list(self):
        """Obtiene todos los registros del historial."""
        pass

    @abstractmethod
    def update_item_and_log_history(self, collection, item_id, item_data, history_log):
        """
        Actualiza un artículo Y escribe en el historial como una 'transacción'.
        Esto reemplaza la necesidad de 'setDoc' y 'addDoc' por separado.
        """
        pass