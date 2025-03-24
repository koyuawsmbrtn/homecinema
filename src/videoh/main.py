import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import VideohWindow

class VideohApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id='space.koyu.videoh',
                        flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        
    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = VideohWindow(application=self)
        win.present()

def main(version):
    app = VideohApplication()
    return app.run(sys.argv)