import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import HomeTheaterWindow

class HomeTheaterApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id='space.koyu.hometheater',
                        flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        
    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = HomeTheaterWindow(application=self)
        win.present()

def main(version):
    app = HomeTheaterApplication()
    return app.run(sys.argv)