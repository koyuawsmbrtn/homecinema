import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk, GObject
from gettext import gettext as _
import sys
from .window import HomeTheaterWindow, HomeTheaterPreferencesWindow
from .item import HomeTheaterItem
from .imdb import IMDb
from .player import HomeTheaterPlayer
from .episodes import EpisodesUI

def main(version):
    """The main entry point for the application."""
    app = Adw.Application(application_id='space.koyu.hometheater')
    
    def on_activate(app):
        win = HomeTheaterWindow(application=app)
        win.present()
    
    app.connect('activate', on_activate)
    return app.run(sys.argv)

__all__ = ['HomeTheaterWindow', 'HomeTheaterPreferencesWindow', 'HomeTheaterItem', 'HomeTheaterPlayer', 'EpisodesUI', 'IMDb', 'main']