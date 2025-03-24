import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GdkPixbuf, Gio, GLib
from pathlib import Path
from gettext import gettext as _
import html
import datetime

@Gtk.Template(resource_path='/space/koyu/videoh/item.ui')
class VideohItem(Gtk.Box):
    __gtype_name__ = 'VideohItem'

    # Template children
    title_label = Gtk.Template.Child()
    year_label = Gtk.Template.Child()
    plot_label = Gtk.Template.Child()
    genre_label = Gtk.Template.Child()
    cast_flowbox = Gtk.Template.Child()
    directors_flowbox = Gtk.Template.Child()
    poster_image = Gtk.Template.Child()
    poster_button = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    refresh_button = Gtk.Template.Child()

    def __init__(self, parent_window, metadata):
        super().__init__()
        self.parent_window = parent_window
        self.metadata = metadata
        self.movie_data = metadata

        # Connect signals
        self.poster_button.connect('clicked', self.on_poster_clicked)
        self.play_button.connect('clicked', self.on_play_clicked)
        self.refresh_button.connect('clicked', self.on_refresh_clicked)

        # Load initial metadata
        self.load_metadata()

    def load_metadata(self):
        """Load metadata into widgets"""
        try:
            # Check if this is a show episode
            is_episode = self.metadata.get('is_episode', False)
            
            if is_episode:
                # Episode specific formatting
                show_title = self.metadata.get('show_title', '')
                season_num = self.metadata.get('season_number', '')
                episode_title = self.metadata.get('episode_title', '')
                title = f"{show_title} - S{season_num:02d} - {episode_title}"
                
                # Get air date and calculate year
                air_date = self.metadata.get('air_date', '')
                year = ''
                if air_date:
                    try:
                        year = datetime.datetime.strptime(air_date, '%Y-%m-%d').year
                    except ValueError:
                        print(f"Error parsing air date: {air_date}")
            else:
                # Movie formatting
                title = html.unescape(self.metadata.get('title', ''))
                year = self.metadata.get('year', '')

            # Common metadata
            plot = html.unescape(self.metadata.get('plot', ''))
            genres = self.metadata.get('genres', [])
            rating = self.metadata.get('rating', '')
            
            # Update UI elements
            if rating:
                title = f"{title} (★ {rating})"
            
            self.title_label.set_label(title)
            self.year_label.set_label(str(year))
            self.plot_label.set_label(plot)
            self.genre_label.set_label(', '.join(genres))
            
            # Load poster
            self.load_poster()
            
            # Update cast/crew
            self.update_person_images()

        except Exception as e:
            print(f"Error loading metadata: {e}")

    def load_poster(self):
        """Load poster image"""
        try:
            poster = self.metadata.get('poster')
            if poster and Path(poster).exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    poster, 100, 150, True)
                self.poster_image.set_pixbuf(pixbuf)
        except Exception as e:
            print(f"Error loading poster: {e}")

    def update_person_images(self):
        """Update cast and crew images"""
        try:
            # Clear existing
            while (child := self.cast_flowbox.get_first_child()):
                self.cast_flowbox.remove(child)

            # Add cast
            cast = self.metadata.get('cast', [])
            cast_images = self.metadata.get('cast_images', [])
            if cast and cast_images and len(cast) == len(cast_images):
                for name, image_path in zip(cast, cast_images):
                    if image_path and Path(image_path).exists():
                        self.add_person_image(name, image_path, self.cast_flowbox)

        except Exception as e:
            print(f"Error updating person images: {e}")

    def add_person_image(self, name, image_path, flowbox):
        """Add a person image to the flowbox"""
        try:
            # Create image container
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.set_size_request(80, 120)

            # Load and scale image
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                image_path, 80, 80, True)
            image = Gtk.Picture.new_for_pixbuf(pixbuf)
            image.set_size_request(80, 80)
            
            # Add name label
            label = Gtk.Label(label=name)
            label.set_wrap(True)
            label.set_max_width_chars(15)
            label.set_lines(2)
            
            # Pack widgets
            box.append(image)
            box.append(label)
            flowbox.append(box)
        except Exception as e:
            print(f"Error adding person image: {e}")

    @Gtk.Template.Callback()
    def on_poster_clicked(self, button):
        """Handle poster click"""
        if hasattr(self.parent_window, 'edit_poster'):
            self.parent_window.edit_poster(self.metadata)

    @Gtk.Template.Callback()
    def on_play_clicked(self, button):
        """Handle play button click"""
        file_path = self.metadata.get('file_path')
        if file_path:
            self.parent_window.show_video(file_path, self.metadata.get('title', ''))

    @Gtk.Template.Callback()
    def on_refresh_clicked(self, button):
        """Handle refresh button click"""
        try:
            if self.metadata.get('is_episode'):
                # Refresh show episode metadata
                self.refresh_show_metadata()
            else:
                # Refresh movie metadata
                self.refresh_movie_metadata()
        except Exception as e:
            self.show_error_dialog(_("Failed to refresh metadata: {}").format(str(e)))

    def show_error_dialog(self, message):
        """Show error dialog"""
        dialog = Adw.MessageDialog(
            transient_for=self.parent_window,
            heading=_("Error"),
            body=message
        )
        dialog.add_response("close", _("Close"))
        dialog.present()

    @Gtk.Template.Callback()
    def on_cast_activated(self, flowbox, child):
        """Handle cast member selection"""
        pass  # Implement if needed