import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk, GObject
from gettext import gettext as _
import sys
from .window import VideohWindow, VideohPreferencesWindow
from .item import VideohItem
from .imdb import IMDb
from .player import VideohPlayer
from .episodes import EpisodesUI

def main(version):
    """The main entry point for the application."""
    app = Adw.Application(application_id='space.koyu.videoh')
    
    def on_activate(app):
        win = VideohWindow(application=app)
        win.present()
    
    app.connect('activate', on_activate)
    return app.run(sys.argv)

__all__ = ['VideohWindow', 'VideohPreferencesWindow', 'VideohItem', 'VideohPlayer', 'EpisodesUI', 'IMDb', 'main']