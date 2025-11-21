# /main.py
import os
import sys

# --- OPTIMIZACIÓN: INICIO DE CONFIGURACIÓN ---
# Estas configuraciones deben ejecutarse ANTES de importar Kivy
# Soluciona problemas de cámara en Windows y compatibilidad de GPU

from kivy.config import Config
# 3. Evita problemas con ZBarCam en algunas GPUs
Config.set('graphics','multisamples','0')
# --- FIN DE CONFIGURACIÓN ---


# Agrega los subdirectorios al path de Python
# (Usa 'modelo' y 'vista' como en tu código)
sys.path.append(os.path.join(os.path.dirname(__file__), 'controlador'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'modelo'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'vista'))

# Importa y ejecuta la aplicación
# Esta importación DEBE ir DESPUÉS de las configuraciones de os.environ y Config
from controlador.app_controller import InventoryApp

if __name__ == "__main__":
    InventoryApp().run()