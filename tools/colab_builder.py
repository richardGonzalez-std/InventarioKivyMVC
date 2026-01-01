# tools/colab_builder.py
"""
DriveHelper para compilar APK en Google Colab.

Uso en Google Colab:
    1. Subir este archivo a tu Drive o clonar el repo
    2. Ejecutar las celdas en orden

Ejemplo de notebook:
    ```python
    # Celda 1: Montar Drive
    from google.colab import drive
    drive.mount('/content/drive')

    # Celda 2: Importar helper
    import sys
    sys.path.insert(0, '/content/drive/MyDrive/InventarioKivyMVC/tools')
    from colab_builder import ColabBuilder

    # Celda 3: Compilar
    builder = ColabBuilder()
    builder.setup()
    builder.build_apk()
    ```
"""

import os
import subprocess
import shutil
from pathlib import Path


class ColabBuilder:
    """
    Helper para compilar APK de Kivy en Google Colab.

    Automatiza:
    - Instalacion de dependencias (Buildozer, SDK, NDK)
    - Clonado/sincronizacion del proyecto
    - Compilacion del APK
    - Copia del APK a Google Drive
    """

    # Rutas por defecto
    DRIVE_PATH = "/content/drive/MyDrive"
    PROJECT_NAME = "InventarioKivyMVC"
    WORK_DIR = "/content"

    def __init__(self, drive_project_path: str = None):
        """
        Inicializa el builder.

        Args:
            drive_project_path: Ruta al proyecto en Drive (opcional)
        """
        self.drive_project_path = drive_project_path or f"{self.DRIVE_PATH}/{self.PROJECT_NAME}"
        self.work_path = f"{self.WORK_DIR}/{self.PROJECT_NAME}"
        self.is_colab = self._check_colab()

    def _check_colab(self) -> bool:
        """Verifica si estamos en Google Colab."""
        try:
            import google.colab
            return True
        except ImportError:
            return False

    def _run(self, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        """Ejecuta un comando en shell."""
        print(f">>> {cmd}")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}")
        return result

    def mount_drive(self):
        """Monta Google Drive (solo en Colab)."""
        if not self.is_colab:
            print("No estamos en Colab, saltando montaje de Drive")
            return

        from google.colab import drive
        drive.mount('/content/drive')
        print("Drive montado en /content/drive")

    def install_dependencies(self):
        """Instala Buildozer y dependencias del sistema."""
        print("Instalando dependencias del sistema...")

        # Dependencias de sistema para Buildozer
        self._run("apt-get update -qq")
        self._run(
            "apt-get install -y -qq "
            "python3-pip build-essential git python3-dev "
            "ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev "
            "libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev "
            "libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good "
            "libgstreamer-plugins-base1.0-dev libgstreamer-plugins-good1.0-dev "
            "zip unzip openjdk-17-jdk autoconf libtool pkg-config "
            "libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev"
        )

        # Instalar Buildozer y Cython
        print("Instalando Buildozer...")
        self._run("pip install --upgrade buildozer cython==0.29.33")

        print("Dependencias instaladas correctamente")

    def sync_project(self):
        """Sincroniza el proyecto desde Drive al directorio de trabajo."""
        print(f"Sincronizando proyecto desde {self.drive_project_path}...")

        if os.path.exists(self.work_path):
            shutil.rmtree(self.work_path)

        shutil.copytree(self.drive_project_path, self.work_path)
        os.chdir(self.work_path)
        print(f"Proyecto copiado a {self.work_path}")

    def setup(self):
        """Configuracion completa: montar, instalar, sincronizar."""
        self.mount_drive()
        self.install_dependencies()
        self.sync_project()
        print("Setup completado")

    def build_apk(self, debug: bool = True):
        """
        Compila el APK con Buildozer.

        Args:
            debug: True para debug APK, False para release
        """
        os.chdir(self.work_path)

        # Limpiar builds anteriores
        if os.path.exists(".buildozer"):
            print("Limpiando build anterior...")
            shutil.rmtree(".buildozer")

        # Compilar
        mode = "debug" if debug else "release"
        print(f"Compilando APK ({mode})... Esto puede tomar 15-30 minutos.")
        self._run(f"buildozer android {mode}")

        # Buscar APK generado
        apk_path = self._find_apk()
        if apk_path:
            print(f"APK generado: {apk_path}")
            self._copy_apk_to_drive(apk_path)
        else:
            print("ERROR: No se encontro el APK generado")

    def _find_apk(self) -> str:
        """Busca el APK generado."""
        bin_path = Path(self.work_path) / "bin"
        if bin_path.exists():
            apks = list(bin_path.glob("*.apk"))
            if apks:
                return str(apks[0])
        return None

    def _copy_apk_to_drive(self, apk_path: str):
        """Copia el APK a Google Drive."""
        output_dir = f"{self.DRIVE_PATH}/APKs"
        os.makedirs(output_dir, exist_ok=True)

        apk_name = os.path.basename(apk_path)
        dest_path = f"{output_dir}/{apk_name}"

        shutil.copy2(apk_path, dest_path)
        print(f"APK copiado a Drive: {dest_path}")

    def clean(self):
        """Limpia archivos temporales."""
        if os.path.exists(self.work_path):
            shutil.rmtree(self.work_path)
            print("Directorio de trabajo limpiado")


# Funciones de conveniencia para uso directo en Colab
def quick_build():
    """Compilacion rapida con configuracion por defecto."""
    builder = ColabBuilder()
    builder.setup()
    builder.build_apk()
    return builder


def rebuild_only():
    """Solo recompila sin reinstalar dependencias."""
    builder = ColabBuilder()
    builder.sync_project()
    builder.build_apk()
    return builder
