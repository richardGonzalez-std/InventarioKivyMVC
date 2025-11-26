# vista/screens/__init__.py
"""
Módulo de pantallas de la aplicación.
Centraliza las importaciones para facilitar el uso desde el controlador.
"""

from vista.screens.camera_screen import CameraScreen
from vista.screens.inventory_screen import InventoryScreen

__all__ = ['CameraScreen', 'InventoryScreen']