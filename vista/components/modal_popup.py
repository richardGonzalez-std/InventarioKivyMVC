# /view/components/modal_popup.py
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty

class ModalPopup(Popup):
    title = StringProperty("Mensaje")
    message = StringProperty("")

    def __init__(self, **kwargs):
        super(ModalPopup, self).__init__(**kwargs)
        
        # Contenido del Popup
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        
        # Mensaje
        content.add_widget(Label(text=self.message, font_size='16sp'))
        
        # Botón de Cierre
        close_button = Button(
            text="Entendido",
            size_hint_y=None,
            height='48dp'
        )
        close_button.bind(on_press=self.dismiss)
        content.add_widget(close_button)
        
        self.content = content
        self.size_hint = (0.8, 0.4)
        self.auto_dismiss = False