# modelo/firebase_client.py
"""
Cliente de Firebase para SIAM usando REST API.
Funciona en Android y Desktop.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Para requests async en Kivy
from kivy.network.urlrequest import UrlRequest


class FirebaseClient:
    """
    Cliente REST para Firebase Firestore.

    Usa la API REST de Firestore que funciona en cualquier plataforma.
    https://firebase.google.com/docs/firestore/use-rest-api
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if FirebaseClient._initialized:
            return

        self.project_id = None
        self.api_key = None
        self.base_url = None
        self.is_connected = False
        FirebaseClient._initialized = True

    def connect(self, config_path: str = "firebase-config.json") -> bool:
        """
        Conecta con Firebase usando configuración.

        Args:
            config_path: Ruta al archivo de configuración
                         (diferente de credenciales admin)

        Returns:
            bool: True si se configuró correctamente
        """
        try:
            # Buscar archivo de config
            if not os.path.exists(config_path):
                from kivy.utils import platform
                if platform == "android":
                    from android.storage import app_storage_path
                    config_path = os.path.join(app_storage_path(), config_path)

            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.project_id = config.get('project_id')
                    self.api_key = config.get('api_key')
            else:
                # Configuración hardcodeada (para desarrollo)
                # REEMPLAZA con tus valores de Firebase Console
                print(f"⚠ No se encontró {config_path}, usando config por defecto")
                self.project_id = "TU_PROJECT_ID"  # Cambiar
                self.api_key = "TU_API_KEY"        # Cambiar

            if self.project_id and self.project_id != "TU_PROJECT_ID":
                self.base_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
                self.is_connected = True
                print(f"✓ Firebase configurado: {self.project_id}")
                return True
            else:
                print("✗ Firebase no configurado. Edita firebase-config.json")
                return False

        except Exception as e:
            print(f"✗ Error configurando Firebase: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    # PRODUCTOS - Métodos Síncronos
    # ─────────────────────────────────────────────────────────

    def get_producto_sync(self, codigo_barras: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene producto por código (síncrono).

        Args:
            codigo_barras: Código del producto

        Returns:
            Dict con datos o None
        """
        if not self.is_connected:
            return None

        try:
            url = f"{self.base_url}/productos/{codigo_barras}?key={self.api_key}"
            req = Request(url)
            response = urlopen(req, timeout=10)
            data = json.loads(response.read().decode())

            return self._firestore_to_dict(data, codigo_barras)

        except HTTPError as e:
            if e.code == 404:
                return None
            print(f"✗ HTTP Error: {e.code}")
            return None
        except Exception as e:
            print(f"✗ Error obteniendo producto: {e}")
            return None

    def get_todos_productos_sync(self) -> List[Dict[str, Any]]:
        """Obtiene todos los productos (síncrono)."""
        if not self.is_connected:
            return []

        try:
            url = f"{self.base_url}/productos?key={self.api_key}"
            req = Request(url)
            response = urlopen(req, timeout=15)
            data = json.loads(response.read().decode())

            productos = []
            for doc in data.get('documents', []):
                # Extraer ID del path
                doc_id = doc['name'].split('/')[-1]
                producto = self._firestore_to_dict(doc, doc_id)
                if producto:
                    productos.append(producto)

            return productos

        except Exception as e:
            print(f"✗ Error obteniendo productos: {e}")
            return []

    # ─────────────────────────────────────────────────────────
    # PRODUCTOS - Métodos Asíncronos (Kivy)
    # ─────────────────────────────────────────────────────────

    def get_producto_async(self, codigo_barras: str, on_success, on_error=None):
        """
        Obtiene producto por código (asíncrono).

        Args:
            codigo_barras: Código del producto
            on_success: Callback(producto_dict)
            on_error: Callback(error_msg)
        """
        if not self.is_connected:
            if on_error:
                on_error("Firebase no conectado")
            return

        url = f"{self.base_url}/productos/{codigo_barras}?key={self.api_key}"

        def success(req, result):
            producto = self._firestore_to_dict(result, codigo_barras)
            on_success(producto)

        def error(req, error):
            if on_error:
                on_error(str(error))
            else:
                print(f"✗ Error async: {error}")

        def failure(req, result):
            # 404 = no encontrado
            on_success(None)

        UrlRequest(url, on_success=success, on_error=error, on_failure=failure, timeout=10)

    def get_todos_productos_async(self, on_success, on_error=None):
        """Obtiene todos los productos (asíncrono)."""
        if not self.is_connected:
            if on_error:
                on_error("Firebase no conectado")
            return

        url = f"{self.base_url}/productos?key={self.api_key}"

        def success(req, result):
            productos = []
            for doc in result.get('documents', []):
                doc_id = doc['name'].split('/')[-1]
                producto = self._firestore_to_dict(doc, doc_id)
                if producto:
                    productos.append(producto)
            on_success(productos)

        def error(req, error):
            if on_error:
                on_error(str(error))

        UrlRequest(url, on_success=success, on_error=error, timeout=15)

    # ─────────────────────────────────────────────────────────
    # ESCRITURA
    # ─────────────────────────────────────────────────────────

    def crear_producto_sync(self, producto: Dict[str, Any]) -> bool:
        """Crea producto (síncrono)."""
        if not self.is_connected:
            return False

        try:
            codigo = producto.get('codigo_barras')
            url = f"{self.base_url}/productos?documentId={codigo}&key={self.api_key}"

            # Convertir a formato Firestore
            firestore_data = self._dict_to_firestore(producto)

            req = Request(
                url,
                data=json.dumps(firestore_data).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            response = urlopen(req, timeout=10)
            return response.status == 200

        except Exception as e:
            print(f"✗ Error creando producto: {e}")
            return False

    def actualizar_cantidad_sync(self, codigo_barras: str, cantidad: int) -> bool:
        """Actualiza cantidad de producto (síncrono)."""
        if not self.is_connected:
            return False

        try:
            url = f"{self.base_url}/productos/{codigo_barras}?updateMask.fieldPaths=cantidad&key={self.api_key}"

            data = {
                "fields": {
                    "cantidad": {"integerValue": str(cantidad)}
                }
            }

            req = Request(
                url,
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json'},
                method='PATCH'
            )
            response = urlopen(req, timeout=10)
            return response.status == 200

        except Exception as e:
            print(f"✗ Error actualizando cantidad: {e}")
            return False

    def registrar_movimiento_sync(
        self,
        codigo_barras: str,
        tipo: str,
        cantidad: int,
        usuario: str,
        notas: str = ""
    ) -> bool:
        """Registra movimiento en historial (síncrono)."""
        if not self.is_connected:
            return False

        try:
            url = f"{self.base_url}/movimientos?key={self.api_key}"

            data = self._dict_to_firestore({
                'codigo_barras': codigo_barras,
                'tipo': tipo,
                'cantidad': cantidad,
                'usuario': usuario,
                'notas': notas,
                'fecha': datetime.now().isoformat()
            })

            req = Request(
                url,
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            response = urlopen(req, timeout=10)
            return response.status == 200

        except Exception as e:
            print(f"✗ Error registrando movimiento: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    # CONVERSIÓN DE DATOS
    # ─────────────────────────────────────────────────────────

    def _firestore_to_dict(self, doc: Dict, doc_id: str) -> Optional[Dict[str, Any]]:
        """Convierte documento Firestore a dict Python."""
        try:
            fields = doc.get('fields', {})
            result = {'codigo_barras': doc_id}

            for key, value in fields.items():
                result[key] = self._parse_firestore_value(value)

            return result

        except Exception as e:
            print(f"✗ Error parseando documento: {e}")
            return None

    def _parse_firestore_value(self, value: Dict) -> Any:
        """Parsea valor de Firestore a Python."""
        if 'stringValue' in value:
            return value['stringValue']
        elif 'integerValue' in value:
            return int(value['integerValue'])
        elif 'doubleValue' in value:
            return float(value['doubleValue'])
        elif 'booleanValue' in value:
            return value['booleanValue']
        elif 'nullValue' in value:
            return None
        elif 'timestampValue' in value:
            return value['timestampValue']
        elif 'arrayValue' in value:
            return [self._parse_firestore_value(v) for v in value['arrayValue'].get('values', [])]
        elif 'mapValue' in value:
            return {k: self._parse_firestore_value(v) for k, v in value['mapValue'].get('fields', {}).items()}
        return None

    def _dict_to_firestore(self, data: Dict) -> Dict:
        """Convierte dict Python a formato Firestore."""
        fields = {}

        for key, value in data.items():
            if key == 'codigo_barras':
                continue  # Es el ID, no un campo
            fields[key] = self._to_firestore_value(value)

        return {"fields": fields}

    def _to_firestore_value(self, value: Any) -> Dict:
        """Convierte valor Python a Firestore."""
        if value is None:
            return {"nullValue": None}
        elif isinstance(value, bool):
            return {"booleanValue": value}
        elif isinstance(value, int):
            return {"integerValue": str(value)}
        elif isinstance(value, float):
            return {"doubleValue": value}
        elif isinstance(value, str):
            return {"stringValue": value}
        elif isinstance(value, list):
            return {"arrayValue": {"values": [self._to_firestore_value(v) for v in value]}}
        elif isinstance(value, dict):
            return {"mapValue": {"fields": {k: self._to_firestore_value(v) for k, v in value.items()}}}
        else:
            return {"stringValue": str(value)}


# Variable de disponibilidad
FIREBASE_AVAILABLE = True
