import gi
import re
import html
import json
import os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, GdkPixbuf, Gdk
from pathlib import Path
import subprocess

@Gtk.Template(resource_path='/space/koyu/hometheater/episodes.ui')
class EpisodesUI(Gtk.Box):
    __gtype_name__ = 'EpisodesUI'

    # Add template children
    season_selector = Gtk.Template.Child()
    episodes_box = Gtk.Template.Child()
    poster_container = Gtk.Template.Child()
    show_title = Gtk.Template.Child()
    show_year = Gtk.Template.Child()
    show_genres = Gtk.Template.Child()
    show_plot = Gtk.Template.Child()
    show_rating = Gtk.Template.Child()
    show_cast = Gtk.Template.Child()
    
    def __init__(self, parent_window, show_name, seasons, **kwargs):
        super().__init__(**kwargs)
        self.parent_window = parent_window
        self.show_name = show_name
        self.seasons = seasons
        
        # Load show metadata
        show_key = f"show:{show_name}"
        show_metadata = self.parent_window.metadata.get(show_key, {})
        
        # Update show info with safe HTML unescaping
        title = show_metadata.get('title') or show_name
        self.show_title.set_label(html.unescape(str(title)))
        
        # Handle other metadata safely
        year = show_metadata.get('year', '')
        self.show_year.set_label(str(year) if year else '')
        
        genres = show_metadata.get('genres', [])
        self.show_genres.set_label(', '.join(genres) if genres else '')
        
        # Clean and set plot safely
        plot = show_metadata.get('plot', '')
        if plot:
            # Remove HTML tags and unescape
            plot = re.sub(r'<[^>]+>', '', str(plot))
            plot = html.unescape(plot)
        self.show_plot.set_label(plot)
        
        # Set rating with star symbol
        rating = show_metadata.get('rating')
        if rating and str(rating).lower() != 'none':
            self.show_rating.set_label(f"★ {rating}")
        else:
            self.show_rating.set_visible(False)
        
        # Set cast info safely
        cast = show_metadata.get('cast', [])
        if cast and isinstance(cast, list):
            cast_text = "Cast: " + ", ".join(cast[:5])  # Show first 5 cast members
            if len(cast) > 5:
                cast_text += f" and {len(cast) - 5} more"
            self.show_cast.set_label(cast_text)
        else:
            self.show_cast.set_visible(False)
        
        # Load show poster
        poster_path = show_metadata.get('poster')
        if poster_path and Path(poster_path).exists():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    poster_path, 150, 225, True)
                rounded_poster = RoundedPicture()
                rounded_poster.set_size_request(150, 225)
                rounded_poster.set_pixbuf(pixbuf)
                self.poster_container.append(rounded_poster)
            except Exception as e:
                print(f"Error loading show poster: {e}")
        
        # Create string list model for seasons
        season_strings = [f"Season {season}" for season in sorted(seasons.keys(), key=int)]
        string_list = Gtk.StringList.new(season_strings)
        
        # Setup dropdown with model
        self.season_selector.set_model(string_list)
        self.season_selector.set_selected(0)  # Select first season
        self.season_selector.connect('notify::selected', self.on_season_changed)
        
        # Show first season
        self.populate_season(next(iter(seasons.keys())))

        # Apply CSS styling
        css_string = """
        .episode-number {
            min-width: 32px;
            min-height: 32px;
            padding: 0;
            margin: 8px;
            font-size: 14px;
            font-weight: bold;
            /* Use halign instead of text-align */
            halign: center;
            background: alpha(@accent_color, 0.15);
            color: @accent_color;
            border-radius: 50%;
        }

        .episode-number:disabled {
            opacity: 1.0;
        }

        .episode-list row {
            padding: 12px;
            margin: 2px;
        }

        .episode-list row > box {
            margin-start: 12px;
            margin-end: 12px;
        }

        .rounded-corners {
            border-radius: 12px;
        }

        .episode-row {
            transition: background-color 200ms ease;
            padding: 0;  /* Remove padding from row */
            margin: 2px;
            border-radius: 12px;
            overflow: hidden;
        }
        
        .episode-content {
            padding: 12px;  /* Add padding to content box instead */
        }
        
        .episode-progress {
            min-height: 3px;
            background-color: @accent_color;
            margin: 0;
            padding: 0;
        }

        .episode-progress trough {
            min-height: 3px;
            background-color: alpha(@accent_color, 0.1);
            border: none;
            border-radius: 0;
            margin: 0;
            padding: 0;
        }

        .episode-progress progress {
            min-height: 3px;
            background-color: @accent_color;
            border-radius: 0;
            margin: 0;
            padding: 0;
        }

        .circular {
            padding: 8px;
            min-width: 36px;
            min-height: 36px;
            margin: 4px;
            border-radius: 9999px;
        }

        .episode-list progressbar {
            margin: 0;
            padding: 0;
            min-height: 3px;
        }
        
        .episode-list progressbar.episode-progress {
            margin-top: -12px;  /* Negative margin to position at top */
            margin-bottom: 12px;
            margin-start: -12px;
            margin-end: -12px;
        }
        
        .episode-list progressbar > trough {
            min-height: 3px;
            border: none;
            background-color: transparent;
        }
        
        .episode-list progressbar > trough > progress {
            min-height: 3px;
            background-color: @accent_color;
            border-radius: 0;
        }
        
        .episode-progress-container {
            padding: 0;
            margin: 0;
        }

        .episode-overlay {
            margin: 0;
            padding: 0;
            border-radius: 12px; /* Match the row's rounded corners */
            overflow: hidden;    /* Ensure the progress bar stays within bounds */
        }

        .episode-progress {
            min-height: 4px;
            margin: 0;
            padding: 0;
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
        }

        .episode-progress > trough {
            min-height: 4px;
            background-color: alpha(@accent_color, 0.1);
            border: none;
        }

        .episode-progress > trough > progress {
            min-height: 4px;
            background-color: @accent_color;
            border-radius: 0;
        }

        .episode-overlay {
            border-radius: 12px;
            overflow: hidden;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css_string.encode(), -1)
        self.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def get_episode_progress(self, episode_path):
        """Get progress percentage for an episode"""
        try:
            xdg_config = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
            config_dir = os.path.join(xdg_config, 'hometheater')
            timestamps_file = os.path.join(config_dir, 'timestamps.json')
            
            if os.path.exists(timestamps_file):
                with open(timestamps_file, 'r') as f:
                    timestamps = json.load(f)
                    if str(episode_path) in timestamps:
                        position = float(timestamps[str(episode_path)])
                        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', episode_path], capture_output=True, text=True)
                        duration = float(result.stdout.strip())
                        if position > 0:
                            progress = min(position / duration, 1.0)
                            return progress
        except Exception as e:
            print(f"Error loading progress: {e}")
        return 0

    def populate_season(self, season_num):
        """Populate episodes for given season"""
        episodes = self.seasons[season_num]
        
        # Clear existing episodes
        while (child := self.episodes_box.get_first_child()):
            self.episodes_box.remove(child)
        
        # Sort episodes by episode number
        sorted_episodes = []
        for episode in episodes:
            try:
                filename = Path(episode['path']).stem
                ep_match = re.search(r'[Ss]\d+[Ee](\d+)|[Ee](\d+)|(\d+)$', filename)
                if ep_match:
                    ep_num = int(ep_match.group(1) or ep_match.group(2) or ep_match.group(3))
                    sorted_episodes.append((ep_num, episode))
            except Exception as e:
                print(f"Error parsing episode number: {e}")
                # Add episodes without numbers to the end
                sorted_episodes.append((float('inf'), episode))
        
        # Sort by episode number
        sorted_episodes.sort(key=lambda x: x[0])
        
        for ep_num, episode in sorted_episodes:
            # Get combined show and episode metadata
            episode_path = episode['path']
            metadata = self.parent_window.get_episode_metadata(episode_path)
            
            # Create content box for padding
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            content_box.add_css_class('episode-content')

            progress = self.get_episode_progress(episode_path)
            if progress > 0:
                # Create the progress bar at the top
                progress_bar = Gtk.ProgressBar()
                progress_bar.set_fraction(progress)
                progress_bar.add_css_class('episode-progress')
                content_box.append(progress_bar)

            # Add episode number and title
            row = Adw.ActionRow()
            row.add_css_class('episode-row')

            # Add episode number button
            ep_button = Gtk.Button()
            ep_button.set_label(str(ep_num))
            ep_button.add_css_class('circular')
            ep_button.add_css_class('episode-number')
            ep_button.set_valign(Gtk.Align.CENTER)
            ep_button.add_css_class('flat')
            ep_button.set_sensitive(False)
            row.add_prefix(ep_button)

            # Get episode title without the episode number prefix
            if metadata:
                if metadata.get('episode_title'):
                    episode_title = metadata['episode_title']
                elif metadata.get('title'):
                    episode_title = metadata['title']
                else:
                    episode_title = f"Episode {ep_num}"
            else:
                episode_title = f"Episode {ep_num}"
                
            row.set_title(episode_title)
            
            # Add episode metadata if available
            if metadata:
                subtitle_parts = []
                if metadata.get('air_date'):
                    subtitle_parts.append(metadata['air_date'])
                if metadata.get('rating'):
                    subtitle_parts.append(f"★ {metadata['rating']}")
                
                # Add episode guest cast if available
                if metadata.get('guest_cast'):
                    guest_cast = metadata['guest_cast'][:3]  # Show up to 3 guest stars
                    if guest_cast:
                        subtitle_parts.append("Guest starring: " + ", ".join(guest_cast))
                
                if subtitle_parts:
                    row.set_subtitle(' • '.join(subtitle_parts))
                
                # Add plot as subtitle if available
                if metadata.get('plot'):
                    plot = metadata['plot']
                    # Clean HTML from plot
                    plot = re.sub(r'<[^>]+>', '', plot)
                    plot = html.unescape(plot)
                    if len(plot) > 200:
                        plot = plot[:197] + "..."
                    if subtitle_parts:
                        row.set_subtitle(row.get_subtitle() + "\n" + plot)
                    else:
                        row.set_subtitle(plot)

            # Add play button
            play_button = Gtk.Button()
            play_button.set_icon_name('media-playback-start-symbolic')
            play_button.set_valign(Gtk.Align.CENTER)
            play_button.add_css_class('circular')
            play_button.add_css_class('flat')
            # Create a closure to properly capture the episode
            def make_click_handler(ep):
                return lambda b: self.on_episode_clicked(ep)
            play_button.connect('clicked', make_click_handler(episode))
            row.add_suffix(play_button)

            # Add row to content box
            content_box.append(row)

            # Add content box to episodes box
            self.episodes_box.append(content_box)

    def on_season_changed(self, dropdown, *args):
        # Get selected season number from dropdown
        selected = dropdown.get_selected()
        if selected != Gtk.INVALID_LIST_POSITION:
            season_text = dropdown.get_model().get_string(selected)
            season_num = season_text.split()[-1]
            self.populate_season(season_num)

    def on_episode_clicked(self, episode):
        show_metadata = episode["metadata"]
        self.parent_window.show_video(
            episode['path'],
            title=self.show_title.get_label() + " - " + episode['metadata']['title'],
            show_metadata=show_metadata
        )

class RoundedPicture(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.pixbuf = None
        self.set_draw_func(self._draw)
        
    def set_pixbuf(self, pixbuf):
        self.pixbuf = pixbuf
        self.queue_draw()
        
    def _draw(self, area, cr, width, height):
        if not self.pixbuf:
            return
            
        # Create rounded rectangle path
        radius = 12
        degrees = 3.14159 / 180.0
        
        cr.new_path()
        cr.arc(radius, radius, radius, 180 * degrees, 270 * degrees)
        cr.arc(width - radius, radius, radius, -90 * degrees, 0 * degrees)
        cr.arc(width - radius, height - radius, radius, 0 * degrees, 90 * degrees)
        cr.arc(radius, height - radius, radius, 90 * degrees, 180 * degrees)
        cr.close_path()
        
        cr.clip()
        
        # Scale and draw the image
        scale_x = width / self.pixbuf.get_width()
        scale_y = height / self.pixbuf.get_height()
        cr.scale(scale_x, scale_y)
        
        Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
        cr.paint()