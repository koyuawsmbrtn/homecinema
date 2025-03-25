import gi
import subprocess
from pathlib import Path

from .player import HomeTheaterPlayer
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gio, GLib, GdkPixbuf, Gdk, Gsk, Graphene

# First, add this CSS to the parent window's CSS provider (in the main window class):
css_string = """
.avatar-image {
    border-radius: 9999px;
    background: alpha(@window_fg_color, 0.1);
    overflow: hidden;  /* Ensure content is clipped to circle */
    margin: 6px;
}

.avatar-image picture {
    margin: 0;
}

.avatar-image picture image {
    object-fit: cover;  /* Make image cover the container */
}

.person-name {
    font-size: 0.9em;
    margin-top: 6px;
}

flowbox {
    padding: 6px;
}

flowbox > flowboxchild {
    padding: 6px;
    min-height: 100px;  /* Ensure enough height for avatar + label */
}
"""

class AvatarPicture(Gtk.DrawingArea):
    def __init__(self, size=60):
        super().__init__()
        self.size = size
        self.set_size_request(size, size)
        self.set_draw_func(self._draw)
        self.pixbuf = None
        
    def set_image(self, path):
        if path and Path(path).exists():
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path,
                self.size,
                self.size,
                False
            )
        else:
            # Load default avatar icon
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            self.pixbuf = icon_theme.load_icon(
                "avatar-default-symbolic",
                48,
                Gtk.IconLookupFlags.FORCE_SYMBOLIC
            )
        self.queue_draw()

    def _draw(self, area, cr, width, height):
        if not self.pixbuf:
            return

        # Create a circular clip path
        cr.arc(width/2, height/2, width/2, 0, 2 * 3.14159)
        cr.clip()
        
        # Draw background
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.1)
        cr.paint()
        
        # Calculate scaling to cover the circle while maintaining aspect ratio
        scale_x = width / self.pixbuf.get_width()
        scale_y = height / self.pixbuf.get_height()
        scale = max(scale_x, scale_y)  # Use the larger scale to ensure coverage
        
        # Calculate translation to center the image
        scaled_width = self.pixbuf.get_width() * scale
        scaled_height = self.pixbuf.get_height() * scale
        x_offset = (width - scaled_width) / 2
        y_offset = (height - scaled_height) / 2
        
        # Apply transformation
        cr.scale(scale, scale)
        cr.translate(x_offset/scale, y_offset/scale)
        
        # Draw the image
        Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
        cr.paint()

class PersonWidget(Gtk.Box):
    def __init__(self, name, image_path):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        
        self.name = name
        
        # Create avatar picture
        self.avatar = AvatarPicture(60)
        self.avatar.set_margin_top(6)
        self.avatar.set_margin_bottom(6)
        self.avatar.set_halign(Gtk.Align.CENTER)
        self.avatar.set_image(image_path)
        
        # Create label
        self.label = Gtk.Label(label=name)
        self.label.set_wrap(True)
        self.label.set_max_width_chars(15)
        self.label.set_halign(Gtk.Align.CENTER)
        self.label.add_css_class('person-name')
        
        self.append(self.avatar)
        self.append(self.label)

    def get_name(self):
        """Get the name of the person"""
        return self.name

@Gtk.Template(resource_path='/space/koyu/hometheater/item.ui')
class HomeTheaterItem(Gtk.Box):
    __gtype_name__ = 'HomeTheaterItem'

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
    cast_group = Gtk.Template.Child()
    directors_group = Gtk.Template.Child()
    people_group = Gtk.Template.Child()

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
                player = HomeTheaterPlayer(self.window, self.video_path)
                player.present()
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

    def _update_people_section_visibility(self):
        """Update visibility of the people section based on content"""
        has_cast = self.cast_flowbox.get_first_child() is not None
        has_directors = self.directors_flowbox.get_first_child() is not None
        
        # Show/hide individual groups
        self.cast_group.set_visible(has_cast)
        self.directors_group.set_visible(has_directors)
        
        # Show/hide the main people group
        self.people_group.set_visible(has_cast or has_directors)

    def clear_cast(self):
        """Remove all cast members from the flowbox"""
        while True:
            child = self.cast_flowbox.get_first_child()
            if child is None:
                break
            self.cast_flowbox.remove(child)
        self._update_people_section_visibility()

    def add_cast_member(self, name, image_path):
        """Add a cast member to the flowbox"""
        person = PersonWidget(name, image_path)
        self.cast_flowbox.append(person)
        self._update_people_section_visibility()

    def clear_directors(self):
        """Remove all directors from the flowbox"""
        while True:
            child = self.directors_flowbox.get_first_child()
            if child is None:
                break
            self.directors_flowbox.remove(child)
        self._update_people_section_visibility()

    def add_director(self, name, image_path):
        """Add a director to the flowbox"""
        person = PersonWidget(name, image_path)
        self.directors_flowbox.append(person)
        self._update_people_section_visibility()