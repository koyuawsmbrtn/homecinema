import gi
import subprocess
from pathlib import Path
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gio, GLib, GdkPixbuf, Gdk

class PersonWidget(Gtk.Box):
    def __init__(self, name, image_path):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        self.name = name  # Store name for later access
        
        # Create image
        self.image = Gtk.Picture()
        if image_path and Path(image_path).exists():
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image_path, 60, 60)
            self.image.set_pixbuf(pixbuf)
        else:
            # Create default avatar using Image widget instead of Picture
            self.image = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
            self.image.set_pixel_size(60)
        
        self.image.set_size_request(60, 60)
        
        # Create label
        self.label = Gtk.Label(label=name)
        self.label.set_wrap(True)
        self.label.set_max_width_chars(15)
        
        self.append(self.image)
        self.append(self.label)

    def get_name(self):
        """Get the name of the person"""
        return self.name

@Gtk.Template(resource_path='/space/koyu/videoh/item.ui')
class VideohItem(Gtk.Box):
    __gtype_name__ = 'VideohItem'

    # Define signals
    __gsignals__ = {
        'refresh-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'metadata-changed': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    # Template children
    refresh_button = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    poster_button = Gtk.Template.Child()
    poster_image = Gtk.Template.Child()
    
    title_row = Gtk.Template.Child()
    title_label = Gtk.Template.Child()
    edit_title_button = Gtk.Template.Child()
    
    year_row = Gtk.Template.Child()
    year_label = Gtk.Template.Child()
    edit_year_button = Gtk.Template.Child()
    
    plot_row = Gtk.Template.Child()
    plot_label = Gtk.Template.Child()
    edit_plot_button = Gtk.Template.Child()
    
    genre_row = Gtk.Template.Child()
    genre_label = Gtk.Template.Child()
    
    directors_flowbox = Gtk.Template.Child()
    cast_flowbox = Gtk.Template.Child()

    def __init__(self, window, movie_data, **kwargs):
        super().__init__(**kwargs)
        
        self.window = window
        self.movie_data = movie_data
        self.video_path = movie_data['path']
        
        # Connect button signals
        self.edit_title_button.connect('clicked', self._on_edit_title_clicked)
        self.edit_year_button.connect('clicked', self._on_edit_year_clicked)
        self.edit_plot_button.connect('clicked', self._on_edit_plot_clicked)

    @Gtk.Template.Callback()
    def on_refresh_clicked(self, button):
        """Handler for refresh button clicks"""
        # Emit a signal that will be handled by the main application
        self.emit('refresh-requested')
    
    @Gtk.Template.Callback()
    def on_play_clicked(self, button):
        """Handler for play button clicks"""
        # Launch video player (using xdg-open for Linux)
        if hasattr(self, 'video_path') and self.video_path:
            try:
                subprocess.Popen(['xdg-open', self.video_path])
            except Exception as e:
                dialog = Adw.MessageDialog(
                    transient_for=self.get_root(),
                    heading="Error Playing Video",
                    body=str(e)
                )
                dialog.add_response("ok", "OK")
                dialog.present()

    @Gtk.Template.Callback()
    def on_poster_clicked(self, button):
        """Handler for poster image clicks"""
        dialog = Gtk.FileChooserDialog(
            title="Select Poster Image",
            transient_for=self.get_root(),
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Open", Gtk.ResponseType.OK)
        
        # Add file filters
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Image files")
        filter_images.add_mime_type("image/*")
        dialog.add_filter(filter_images)
        
        dialog.connect("response", self._on_poster_dialog_response)
        dialog.present()

    def _on_poster_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file:
                path = file.get_path()
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, 100, 150)
                self.set_poster(pixbuf)
                
                # Update metadata in window
                metadata = self.movie_data.get('metadata', {}).copy()
                metadata['poster'] = path
                self.window.update_metadata(self.movie_data['path'], metadata)
        dialog.destroy()

    @Gtk.Template.Callback()
    def on_cast_activated(self, flowbox, child):
        """Handler for cast member selection"""
        person_widget = child.get_child()
        if isinstance(person_widget, PersonWidget):
            name = person_widget.get_name()
            bio = self.movie_data.get('metadata', {}).get('cast_bios', {}).get(name)
            
            if bio:
                # Create a dialog with scrollable biography
                dialog = Adw.MessageDialog(
                    transient_for=self.get_root(),
                    heading=name,
                )
                
                scrolled = Gtk.ScrolledWindow()
                scrolled.set_min_content_height(200)
                scrolled.set_min_content_width(400)
                
                text_view = Gtk.TextView()
                text_view.set_wrap_mode(Gtk.WrapMode.WORD)
                text_view.set_editable(False)
                text_view.get_buffer().set_text(bio)
                
                scrolled.set_child(text_view)
                dialog.set_extra_child(scrolled)
                
                dialog.add_response("ok", _("OK"))
                dialog.present()

    def _show_edit_dialog(self, title, current_text, callback):
        """Helper to show an edit dialog"""
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=f"Edit {title}",
        )
        
        entry = Gtk.Entry()
        entry.set_text(current_text)
        dialog.set_extra_child(entry)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.connect("response", callback, entry)
        dialog.present()

    def _on_edit_title_clicked(self, button):
        """Handler for title edit button"""
        current_title = self.title_label.get_label()
        self._show_edit_dialog("Title", current_title, self._on_title_dialog_response)

    def _on_title_dialog_response(self, dialog, response, entry):
        if response == "ok":
            new_title = entry.get_text()
            self.title_label.set_label(new_title)
            # Update metadata in window
            metadata = self.movie_data.get('metadata', {}).copy()
            metadata['title'] = new_title
            self.window.update_metadata(self.movie_data['path'], metadata)
        dialog.destroy()

    def _on_edit_year_clicked(self, button):
        """Handler for year edit button"""
        current_year = self.year_label.get_label()
        self._show_edit_dialog("Year", current_year, self._on_year_dialog_response)

    def _on_year_dialog_response(self, dialog, response, entry):
        if response == "ok":
            year_text = entry.get_text()
            if year_text.isdigit():
                self.year_label.set_label(year_text)
                # Update metadata in window
                metadata = self.movie_data.get('metadata', {}).copy()
                metadata['year'] = int(year_text)
                self.window.update_metadata(self.movie_data['path'], metadata)
        dialog.destroy()

    def _on_edit_plot_clicked(self, button):
        """Handler for plot edit button"""
        current_plot = self.plot_label.get_label()
        
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Edit Plot",
        )
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(100)
        
        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.get_buffer().set_text(current_plot)
        
        scrolled.set_child(text_view)
        dialog.set_extra_child(scrolled)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("ok", "OK")
        dialog.connect("response", self._on_plot_dialog_response, text_view)
        dialog.present()

    def _on_plot_dialog_response(self, dialog, response, text_view):
        if response == "ok":
            buffer = text_view.get_buffer()
            text = buffer.get_text(
                buffer.get_start_iter(),
                buffer.get_end_iter(),
                True
            )
            self.plot_label.set_label(text)
            # Update metadata in window
            metadata = self.movie_data.get('metadata', {}).copy()
            metadata['plot'] = text
            self.window.update_metadata(self.movie_data['path'], metadata)
        dialog.destroy()

    def update_metadata(self, title="", year="", plot="", genres=None):
        """Update the widget with new metadata"""
        self.title_label.set_label(title)
        self.year_label.set_label(str(year))
        self.plot_label.set_label(plot)
        if genres:
            self.genre_label.set_label(", ".join(genres))

    def set_poster(self, pixbuf):
        """Set the poster image"""
        self.poster_image.set_pixbuf(pixbuf)

    def clear_cast(self):
        """Remove all cast members from the flowbox"""
        while True:
            child = self.cast_flowbox.get_first_child()
            if child is None:
                break
            self.cast_flowbox.remove(child)

    def add_cast_member(self, name, image_path):
        """Add a cast member to the flowbox"""
        person = PersonWidget(name, image_path)
        self.cast_flowbox.append(person)

    def clear_directors(self):
        """Remove all directors from the flowbox"""
        while True:
            child = self.directors_flowbox.get_first_child()
            if child is None:
                break
            self.directors_flowbox.remove(child)

    def add_director(self, name, image_path):
        """Add a director to the flowbox"""
        person = PersonWidget(name, image_path)
        self.directors_flowbox.append(person)