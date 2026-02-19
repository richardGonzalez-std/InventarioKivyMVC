# /model/inventory_model.py
from datetime import datetime

class InventoryModel:
    """
    Contiene la lógica de negocio. Es 'agnóstico' de la UI y la BD.
    Recibe una interfaz de base de datos y la utiliza.
    """
    
    def __init__(self, db_interface):
        self.db = db_interface # Guardamos la instancia de la BD
        print("Modelo de inventario inicializado.")

    def get_item(self, collection, item_id):
        """Pasa la solicitud de 'get_item' a la base de datos."""
        return self.db.get_item(collection, item_id)

    def get_inventory(self, collection):
        """Pasa la solicitud de 'get_inventory_list' a la base de datos."""
        return self.db.get_inventory_list(collection)

    def get_history(self):
        """Pasa la solicitud de 'get_history_list' a la base de datos."""
        return self.db.get_history_list()

    def process_inventory_change(self, collection, item_id, item_name, change_amount, action_type):
        """
        Esta es la lógica de 'handleUpdateQuantity' del código original.
        Aplica todas las reglas de negocio antes de llamar a la BD.
        """

        # SIAM-CP3-CU01: Validación de cantidad negativa
        if change_amount < 0:
            raise ValueError("Error: No se permiten cantidades negativas.")

        if change_amount == 0:
            raise ValueError("Error: La cantidad debe ser mayor a cero.")

        # 1. Obtener el estado actual
        item = self.db.get_item(collection, item_id)
        current_quantity = 0

        if item:
            current_quantity = item.get('quantity', 0)
        elif action_type == 'salida':
            # Validación: No se puede dar salida a un ítem que no existe
            raise ValueError(f"Error: El artículo {item_id} no existe para registrar una Salida.")

        # 2. Calcular el cambio
        # El 'change_amount' del formulario siempre es positivo.
        # Lo convertimos a negativo si es una salida.
        final_change = change_amount if action_type == 'entrada' else -change_amount
        
        new_quantity = current_quantity + final_change
        action_label = "Entrada" if action_type == 'entrada' else "Salida"

        # 3. VALIDACIÓN CRÍTICA (del código original)
        if new_quantity < 0:
            raise ValueError("Error: La cantidad no puede ser menor a cero.")

        # 4. Preparar los datos para la BD
        
        # Datos para el documento del ítem
        item_data = {
            "name": item_name,
            "quantity": new_quantity,
            "lastAction": action_label
        }
        
        # Datos para el log de historial
        history_log = {
            "action": action_label,
            "itemCollection": collection,
            "itemId": item_id,
            "itemName": item_name,
            "quantityChange": final_change,
            "oldQuantity": current_quantity,
            "newQuantity": new_quantity,
        }
        
        # 5. Ejecutar la transacción en la BD
        self.db.update_item_and_log_history(collection, item_id, item_data, history_log)
        
        return f"¡{action_label} de {change_amount} unidades registrada!"