# /model/database_dummy.py
from modelo.database_abstract import DatabaseInterface
from datetime import datetime

class DummyDatabase(DatabaseInterface):
    """
    Implementación ficticia de la base de datos que usa diccionarios en memoria.
    Perfecto para desarrollo y pruebas.
    """
    def __init__(self):
        self._db = {
            "consumos_viveres": {
                "TONER-12A": {"name": "Tóner HP 12A", "quantity": 10, "lastAction": "Entrada"},
                "RESMA-CARTA": {"name": "Resma Papel Carta", "quantity": 50, "lastAction": "Entrada"}
            },
            "equipos_mantenimiento": {
                "MARTILLO-01": {"name": "Martillo", "quantity": 7, "lastAction": "Entrada"}
            },
            "equipo_oficina": {
                "SILLA-ERG": {"name": "Silla Ergonómica", "quantity": 5, "lastAction": "Salida"}
            },
            "inventory_history": []
        }
        self._user_id = None
        print("Base de datos ficticia inicializada.")

    def connect(self, user_id):
        self._user_id = user_id
        print(f"Usuario ficticio conectado: {self._user_id}")

    def get_item(self, collection, item_id):
        return self._db.get(collection, {}).get(item_id)

    def get_inventory_list(self, collection):
        # Devuelve datos en el formato que el RecycleView espera
        items_dict = self._db.get(collection, {})
        return [
            {
                'id': k,
                'name': v.get('name', 'N/A'),
                'quantity': v.get('quantity', 0),
                'lastAction': v.get('lastAction', '')
            }
            for k, v in items_dict.items()
        ]

    def get_history_list(self):
        # Devuelve la lista en orden cronológico inverso
        return sorted(self._db["inventory_history"], key=lambda x: x['timestamp'], reverse=True)

    def update_item_and_log_history(self, collection, item_id, item_data, history_log):
        # 1. Asegurarse de que la colección existe
        if collection not in self._db:
            self._db[collection] = {}

        # 2. Actualizar/Crear el artículo (como setDoc con merge=True)
        if item_id not in self._db[collection]:
            self._db[collection][item_id] = {}
        
        self._db[collection][item_id].update(item_data)
        
        # 3. Agregar el log de historial (como addDoc)
        # Añadimos datos que la BD real añadiría
        history_log['timestamp'] = datetime.now()
        history_log['userId'] = self._user_id
        
        self._db["inventory_history"].append(history_log)
        
        print(f"BD FICTICIA: Artículo {item_id} actualizado, historial registrado.")
        return True