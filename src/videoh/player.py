import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from gettext import gettext as _

class VideohPlayer(Gtk.Box):
    def __init__(self, parent, video_path, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10, **kwargs)
        self.parent = parent
        self.video_path = video_path

        label = Gtk.Label(label=_("Playing video:\n") + video_path)
        self.append(label)

        launch_button = Gtk.Button(label=_("Launch in Clapper"))
        launch_button.connect("clicked", self.on_launch_clicked)
        self.append(launch_button)

        # Optionally, auto-launch the video when the widget is presented
        GLib.idle_add(self.on_launch_clicked, None)

    def on_launch_clicked(self, button):
        if not Path(self.video_path).exists():
            dialog = Adw.MessageDialog.new(
                self.parent,
                _("Error"),
                _("Video file not found:\n{}").format(self.video_path)
            )
            dialog.add_response("close", _("Close"))
            dialog.present()
            return

        cmd = [
            "flatpak-spawn", "--host", "flatpak",
            "run", "com.github.rafostar.Clapper", self.video_path
        ]
        try:
            subprocess.Popen(cmd)
            toast = Adw.Toast.new(_("Launching video in Clapper"))
            self.parent.toast_overlay.add_toast(toast)
            GLib.timeout_add(100, self.return_to_previous)
        except Exception as e:
            dialog = Adw.MessageDialog.new(
                self.parent,
                _("Error"),
                _("Failed to launch video:\n{}").format(str(e))
            )
            dialog.add_response("close", _("Close"))
            dialog.present()

    def return_to_previous(self):
        # Assuming the parent contains a navigation_view that supports pop()
        if hasattr(self.parent, 'navigation_view'):
            self.parent.navigation_view.pop()
        return False  # Stop the timeout callback