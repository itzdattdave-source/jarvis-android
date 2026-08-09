from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class JarvisApp(App):
    def build(self):
        box = BoxLayout(orientation="vertical", padding=24)
        box.add_widget(Label(
            text="JARVIS\nAndroid build scaffold ready",
            halign="center",
            valign="middle",
            font_size="24sp"
        ))
        return box

if __name__ == "__main__":
    JarvisApp().run()
