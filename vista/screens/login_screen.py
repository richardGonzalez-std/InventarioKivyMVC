# vista/screens/login_screen.py
"""
Pantalla de inicio de sesión para SIAM.
Implementa autenticación de usuarios con validación.
"""

from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText


class LoginScreen(MDScreen):
    """
    Pantalla de login con campos de usuario y contraseña.

    Flujo:
    1. Usuario ingresa credenciales
    2. Validación de campos
    3. Autenticación contra modelo
    4. Navegación a pantalla principal o error
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "login"

    def on_enter(self, *args):
        """Se ejecuta al entrar a la pantalla."""
        print("✓ Entrando a LoginScreen")
        # Limpiar campos al entrar
        Clock.schedule_once(self._clear_fields, 0.1)

    def _clear_fields(self, dt):
        """Limpia los campos de texto."""
        if 'username_field' in self.ids:
            self.ids.username_field.text = ""
        if 'password_field' in self.ids:
            self.ids.password_field.text = ""

    def validate_login(self):
        """
        Valida las credenciales ingresadas.

        Reglas de validación:
        - Usuario no vacío
        - Contraseña no vacía
        - Mínimo 4 caracteres en contraseña
        """
        username = self.ids.username_field.text.strip()
        password = self.ids.password_field.text.strip()

        # Validación de campos vacíos
        if not username:
            self._show_error("Ingrese su nombre de usuario")
            return False

        if not password:
            self._show_error("Ingrese su contraseña")
            return False

        if len(password) < 4:
            self._show_error("La contraseña debe tener al menos 4 caracteres")
            return False

        return True

    def attempt_login(self):
        """
        Intenta iniciar sesión con las credenciales proporcionadas.
        """
        if not self.validate_login():
            return

        username = self.ids.username_field.text.strip()
        password = self.ids.password_field.text.strip()

        print(f"✓ Intentando login: {username}")

        # TODO: Integrar con modelo de autenticación real
        # Por ahora, credenciales de prueba
        if self._authenticate(username, password):
            self._on_login_success(username)
        else:
            self._show_error("Usuario o contraseña incorrectos")

    def _authenticate(self, username: str, password: str) -> bool:
        """
        Autentica al usuario contra el modelo.

        TODO: Reemplazar con autenticación real (Active Directory - SIAM-RC-04)
        """
        # Usuarios de prueba para desarrollo
        test_users = {
            "admin": "1234",
            "almacen": "1234",
            "cocina": "1234",
        }
        return test_users.get(username) == password

    def _on_login_success(self, username: str):
        """
        Maneja el login exitoso.
        Navega a la pantalla principal.
        """
        print(f"✓ Login exitoso: {username}")

        # Guardar usuario en la app
        from kivy.app import App
        app = App.get_running_app()
        app.current_user = username

        # Navegar a pantalla principal
        if hasattr(self.manager, 'current'):
            self.manager.current = "main"

    def _show_error(self, message: str):
        """Muestra un mensaje de error con Snackbar."""
        MDSnackbar(
            MDSnackbarText(text=message),
            y="24dp",
            pos_hint={"center_x": 0.5},
            size_hint_x=0.9,
        ).open()

    def on_password_enter(self):
        """Se ejecuta al presionar Enter en el campo de contraseña."""
        self.attempt_login()
