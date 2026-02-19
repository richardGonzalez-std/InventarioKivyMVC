# modelo/session_manager.py
"""
Gestión de sesiones persistentes para SIAM.
Permite que los trabajadores de almacén no tengan que hacer login
en cada turno (sesión válida por 8 horas).
"""

import json
import os
import time

SESSION_DURATION = 8 * 60 * 60  # 8 horas en segundos


def _get_session_path() -> str:
    """Ruta al archivo de sesión en el directorio de datos de la app."""
    from kivy.app import App
    app = App.get_running_app()
    return os.path.join(app.user_data_dir, 'siam_session.json')


def save_session(username: str):
    """Guarda sesión con timestamp actual (se mantiene 8 horas)."""
    try:
        data = {'user': username, 'ts': time.time()}
        with open(_get_session_path(), 'w') as f:
            json.dump(data, f)
        print(f"✓ Sesión guardada: {username} (válida 8h)")
    except Exception as e:
        print(f"⚠ Error guardando sesión: {e}")


def load_session() -> str | None:
    """
    Carga sesión activa si no ha expirado.
    Retorna el username si la sesión es válida, None si expiró o no existe.
    """
    try:
        path = _get_session_path()
        if not os.path.exists(path):
            return None

        with open(path) as f:
            data = json.load(f)

        elapsed = time.time() - data.get('ts', 0)
        if elapsed < SESSION_DURATION:
            horas_restantes = (SESSION_DURATION - elapsed) / 3600
            print(f"✓ Sesión activa: {data['user']} ({horas_restantes:.1f}h restantes)")
            return data.get('user')

        print("⚠ Sesión expirada, requiere nuevo login")
        clear_session()
        return None

    except Exception as e:
        print(f"⚠ Error cargando sesión: {e}")
        return None


def clear_session():
    """Elimina la sesión guardada (logout)."""
    try:
        path = _get_session_path()
        if os.path.exists(path):
            os.remove(path)
        print("✓ Sesión eliminada")
    except Exception as e:
        print(f"⚠ Error eliminando sesión: {e}")
