# vista/screens/__init__.py
"""
Módulo de pantallas de la aplicación.
Centraliza las importaciones para facilitar el uso desde el controlador.
"""

from vista.screens.camera_screen import CameraScreen
from vista.screens.inventory_screen import InventoryScreen
from vista.screens.admin_screen import AdminScreen
from vista.screens.login_screen import LoginScreen

__all__ = ['CameraScreen', 'InventoryScreen', 'AdminScreen', 'LoginScreen']