# vista/components/form_bottom_sheet.py
"""
Bottom Sheet reutilizable para formularios.
Usado en operaciones de entrada/salida de materiales.
"""

from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.bottomsheet import MDBottomSheet, MDBottomSheetDragHandle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText, MDTextFieldLeadingIcon


class FormBottomSheet(MDBottomSheet):
    """
    Bottom Sheet generico para formularios.

    Proporciona:
    - Titulo y subtitulo
    - Contenedor para campos de formulario
    - Botones de accion (Cancelar/Confirmar)
    - Callback para confirmacion

    Uso:
        sheet = FormBottomSheet(
            title="Registrar Entrada",
            subtitle="Ingrese los datos del material",
            on_confirm=self.handle_confirm
        )
        sheet.add_field("codigo", "Codigo", "barcode")
        sheet.add_field("cantidad", "Cantidad", "numeric", input_type="number")
        sheet.open()
    """

    title = StringProperty("Formulario")
    subtitle = StringProperty("")
    on_confirm = ObjectProperty(None)
    fields = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = "modal"
        self.adaptive_height = True
        self._field_widgets = {}
        Clock.schedule_once(self._build_content, 0)

    def _build_content(self, dt):
        """Construye el contenido del bottom sheet."""
        # Contenedor principal
        content = MDBoxLayout(
            orientation="vertical",
            padding=[dp(20), dp(10), dp(20), dp(20)],
            spacing=dp(15),
            adaptive_height=True,
        )

        # Drag handle
        content.add_widget(MDBottomSheetDragHandle())

        # Titulo
        content.add_widget(
            MDLabel(
                text=self.title,
                font_style="Headline",
                role="small",
                halign="center",
                adaptive_height=True,
            )
        )

        # Subtitulo (si existe)
        if self.subtitle:
            content.add_widget(
                MDLabel(
                    text=self.subtitle,
                    font_style="Body",
                    role="medium",
                    halign="center",
                    theme_text_color="Secondary",
                    adaptive_height=True,
                )
            )

        # Contenedor de campos
        self._fields_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            adaptive_height=True,
        )
        content.add_widget(self._fields_container)

        # Botones de accion
        buttons = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(10),
            adaptive_height=True,
            padding=[0, dp(15), 0, 0],
        )

        # Boton Cancelar
        cancel_btn = MDButton(
            style="outlined",
            on_release=lambda x: self.dismiss(),
        )
        cancel_btn.add_widget(MDButtonText(text="Cancelar"))
        buttons.add_widget(cancel_btn)

        # Boton Confirmar
        confirm_btn = MDButton(
            style="filled",
            on_release=self._handle_confirm,
        )
        confirm_btn.add_widget(MDButtonText(text="Confirmar"))
        buttons.add_widget(confirm_btn)

        content.add_widget(buttons)

        # Agregar al bottom sheet
        self.add_widget(content)

        # Agregar campos predefinidos
        for field in self.fields:
            self.add_field(**field)

    def add_field(
        self,
        field_id: str,
        hint_text: str,
        icon: str = None,
        input_type: str = "text",
        required: bool = True,
    ):
        """
        Agrega un campo al formulario.

        Args:
            field_id: Identificador unico del campo
            hint_text: Texto de ayuda/placeholder
            icon: Icono opcional (nombre de Material Design)
            input_type: Tipo de entrada ("text", "number", "password")
            required: Si el campo es obligatorio
        """
        field = MDTextField(
            mode="outlined",
            size_hint_x=1,
        )
        field.add_widget(MDTextFieldHintText(text=hint_text))

        if icon:
            field.add_widget(MDTextFieldLeadingIcon(icon=icon))

        if input_type == "number":
            field.input_filter = "float"

        if input_type == "password":
            field.password = True

        self._field_widgets[field_id] = {
            "widget": field,
            "required": required,
        }
        self._fields_container.add_widget(field)

    def get_values(self) -> dict:
        """
        Obtiene los valores de todos los campos.

        Returns:
            dict: Diccionario {field_id: valor}
        """
        return {
            field_id: info["widget"].text.strip()
            for field_id, info in self._field_widgets.items()
        }

    def validate(self) -> tuple[bool, str]:
        """
        Valida los campos requeridos.

        Returns:
            tuple: (es_valido, mensaje_error)
        """
        for field_id, info in self._field_widgets.items():
            if info["required"] and not info["widget"].text.strip():
                return False, f"El campo es requerido"
        return True, ""

    def _handle_confirm(self, instance):
        """Maneja la confirmacion del formulario."""
        is_valid, error = self.validate()
        if not is_valid:
            # TODO: Mostrar error en snackbar
            print(f"Validacion fallida: {error}")
            return

        if self.on_confirm:
            self.on_confirm(self.get_values())

        self.dismiss()

    def clear_fields(self):
        """Limpia todos los campos del formulario."""
        for info in self._field_widgets.values():
            info["widget"].text = ""
