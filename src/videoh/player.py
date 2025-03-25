import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '4.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GObject, Gst, GstVideo, Adw, Gio, GLib, Gdk
from pathlib import Path
import json

@Gtk.Template(resource_path='/space/koyu/videoh/player.ui')
class VideohPlayer(Adw.Window):
    __gtype_name__ = 'VideohPlayer'

    # Template children
    video_area = Gtk.Template.Child()
    controls = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    position_scale = Gtk.Template.Child()
    time_label = Gtk.Template.Child()
    fullscreen_button = Gtk.Template.Child()
    header_bar = Gtk.Template.Child()  # Add this to template children at top

    def __init__(self, parent, path, title=None, show_metadata=None):
        super().__init__()
        
        self.parent = parent
        self.path = str(path)  # Ensure path is string
        self.duration = 0
        self.is_fullscreen = False
        
        # Add properties for UI hiding
        self.ui_timeout_id = None
        self.mouse_inside = False
        self.ui_visible = True
        
        # Set transient for parent
        self.set_transient_for(parent)
        
        # Set window title
        if title:
            if show_metadata:
                season = show_metadata['season']
                episode = show_metadata['episode']
                if int(season) < 10:
                    season = f"0{season}"
                if int(episode) < 10:
                    episode = f"0{episode}"
                if season and episode:
                    self.set_title(f"{title} - S{season}E{episode}")
                else:
                    self.set_title(title)
            else:
                self.set_title(title)
        else:
            # Use filename as title if none provided
            self.set_title(Path(path).stem)
        
        # Initialize GStreamer if needed
        if not Gst.is_initialized():
            Gst.init(None)
        
        # Create playbin
        self.playbin = Gst.ElementFactory.make('playbin', 'playbin')
        if not self.playbin:
            print("Error: Could not create playbin")
            return
            
        # Set the URI
        file_uri = Gst.filename_to_uri(self.path)
        self.playbin.set_property('uri', file_uri)
        
        # Create video sink
        self.sink = Gst.ElementFactory.make('gtk4paintablesink', 'sink')
        if not self.sink:
            print("Error: Could not create gtk4paintablesink")
            return
            
        self.playbin.set_property('video-sink', self.sink)
        
        # Get the paintable and add it to video area
        self.video_area.set_paintable(self.sink.get_property('paintable'))
        
        # Set up message bus
        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)
        
        # Connect signals
        self.play_button.connect('clicked', self.on_play)
        self.position_scale.connect('change-value', self.on_seek)
        self.fullscreen_button.connect('clicked', self.on_fullscreen)
        
        # Set up event controllers
        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect('enter', self.on_mouse_enter)
        motion_controller.connect('leave', self.on_mouse_leave)
        motion_controller.connect('motion', self.on_mouse_motion)
        self.add_controller(motion_controller)
        
        # Add motion controller to controls box specifically
        controls_motion = Gtk.EventControllerMotion.new()
        controls_motion.connect('enter', self.on_controls_enter)
        controls_motion.connect('leave', self.on_controls_leave)
        self.controls.add_controller(controls_motion)
        
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect('key-pressed', self.on_key_pressed)
        self.add_controller(key_controller)
        
        # Set up CSS provider for fullscreen
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .fullscreen-window {
                background-color: black;
            }
            .normal-window {
                background-color: @window_bg_color;
            }
        """)
        self.get_style_context().add_provider(
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.get_style_context().add_class('normal-window')
        
        # Update position every second
        GLib.timeout_add(1000, self.update_position)
        
        # Start playing
        self.playbin.set_state(Gst.State.PLAYING)
        self.play_button.set_icon_name('media-playback-pause-symbolic')

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.playbin.set_state(Gst.State.PAUSED)
            self.play_button.set_icon_name('media-playback-start-symbolic')
        elif t == Gst.MessageType.ERROR:
            self.playbin.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.playbin:
                old, new, pending = message.parse_state_changed()
                if new == Gst.State.PLAYING:
                    success, duration = self.playbin.query_duration(Gst.Format.TIME)
                    if success:
                        self.duration = duration / Gst.SECOND
                        self.position_scale.set_range(0, self.duration)
                        
    def on_play(self, button):
        if self.play_button.get_icon_name() == 'media-playback-start-symbolic':
            self.playbin.set_state(Gst.State.PLAYING)
            self.play_button.set_icon_name('media-playback-pause-symbolic')
        else:
            self.playbin.set_state(Gst.State.PAUSED)
            self.play_button.set_icon_name('media-playback-start-symbolic')
            
    def on_seek(self, scale, scroll_type, value):
        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(value * Gst.SECOND)
        )
        return True
        
    def on_fullscreen(self, button):
        if self.is_fullscreen:
            self.unfullscreen()
            self.fullscreen_button.set_icon_name('view-fullscreen-symbolic')
            self.get_style_context().remove_class('fullscreen-window')
            self.get_style_context().add_class('normal-window')
            self.show_ui()
            # Always show cursor in windowed mode
            window = self.get_root()
            if window:
                window.set_cursor(Gdk.Cursor.new_from_name("default"))
        else:
            self.fullscreen()
            self.fullscreen_button.set_icon_name('view-restore-symbolic')
            self.get_style_context().remove_class('normal-window')
            self.get_style_context().add_class('fullscreen-window')
            self.schedule_hide_ui()
        self.is_fullscreen = not self.is_fullscreen
        
    def update_position(self):
        success, position = self.playbin.query_position(Gst.Format.TIME)
        if success:
            position = position / Gst.SECOND
            self.position_scale.set_value(position)
            
            # Update time label
            pos_str = f"{int(position/60):02d}:{int(position%60):02d}"
            if self.duration > 0:
                dur_str = f"{int(self.duration/60):02d}:{int(self.duration%60):02d}"
                self.time_label.set_label(f"{pos_str} / {dur_str}")
            else:
                self.time_label.set_label(pos_str)
            
        return True
        
    def do_close_request(self):
        self.playbin.set_state(Gst.State.NULL)
        return False

    def on_mouse_enter(self, controller, x, y):
        print("Mouse entered")  # Debug
        self.mouse_inside = True
        self.show_ui()
        
    def on_mouse_leave(self, controller):
        print("Mouse left")  # Debug
        self.mouse_inside = False
        self.schedule_hide_ui()
        
    def on_mouse_motion(self, controller, x, y):
        print(f"Mouse motion at {x},{y}")  # Debug
        self.show_ui()
        self.schedule_hide_ui()
        
    def on_controls_enter(self, controller, x, y):
        print("Controls entered")  # Debug
        self.mouse_inside = True
        self.show_ui()
        
    def on_controls_leave(self, controller):
        print("Controls left")  # Debug
        self.mouse_inside = False
        if self.is_fullscreen:
            self.schedule_hide_ui()

    def show_ui(self):
        print("Showing UI")  # Debug
        self.header_bar.set_visible(True)
        self.controls.set_visible(True)
        self.ui_visible = True
        window = self.get_root()
        if window:
            window.set_cursor(Gdk.Cursor.new_from_name("default"))
        if self.is_fullscreen:
            self.schedule_hide_ui()

    def hide_ui(self):
        print("Hiding UI")  # Debug
        if self.is_fullscreen and not self.mouse_inside:
            self.header_bar.set_visible(False)
            self.controls.set_visible(False)
            self.ui_visible = False
            window = self.get_root()
            if window:
                window.set_cursor(Gdk.Cursor.new_from_name("none"))
            self.ui_timeout_id = None
            return False
        return True  # Keep timer running if conditions not met

    def schedule_hide_ui(self):
        print("Scheduling hide UI")  # Debug
        if not self.is_fullscreen:
            return
            
        # Remove existing timer if any
        if hasattr(self, 'ui_timeout_id') and self.ui_timeout_id is not None:
            GLib.source_remove(self.ui_timeout_id)
            self.ui_timeout_id = None
            
        # Set new timer
        self.ui_timeout_id = GLib.timeout_add(2000, lambda: self.hide_ui() or False)
        
    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape and self.is_fullscreen:
            self.unfullscreen()
            self.fullscreen_button.set_icon_name('view-fullscreen-symbolic')
            self.get_style_context().remove_class('fullscreen-window')
            self.get_style_context().add_class('normal-window')
            self.show_ui()
            self.is_fullscreen = False
            return True
        return False