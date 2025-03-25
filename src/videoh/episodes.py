import gi
import re
import html
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Pango, GdkPixbuf
from pathlib import Path

@Gtk.Template(resource_path='/space/koyu/videoh/episodes.ui')
class EpisodesUI(Gtk.Box):
    __gtype_name__ = 'EpisodesUI'

    # Add template children
    season_selector = Gtk.Template.Child()
    episodes_box = Gtk.Template.Child()
    show_poster = Gtk.Template.Child()
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
                self.show_poster.set_pixbuf(pixbuf)
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
        }
        
        .episode-row:hover {
            background-color: alpha(@accent_color, 0.08);
        }
        
        .episode-row:active {
            background-color: alpha(@accent_color, 0.12);
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css_string.encode(), -1)
        self.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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
            
            # Create row with episode info
            row = Adw.ActionRow()
            row.add_css_class('episode-row')  # Add class for hover styling
            
            # Make entire row clickable
            click = Gtk.GestureClick.new()
            click.connect('pressed', 
                lambda g, n, x, y, e: self.parent_window.show_movie_details(e), 
                episode)
            row.add_controller(click)
            
            # Add episode number button on the left
            ep_button = Gtk.Button()
            ep_button.set_label(str(ep_num))
            ep_button.add_css_class('circular')
            ep_button.add_css_class('episode-number')
            ep_button.set_sensitive(False)  # Make it non-clickable
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
            play_button.add_css_class('circular')
            play_button.connect('clicked', 
                lambda b, e: self.parent_window.show_video(e['path'], episode_title), 
                episode)
            row.add_suffix(play_button)
            
            # Remove the info button since row is now clickable
            
            self.episodes_box.append(row)

    def on_season_changed(self, dropdown, *args):
        # Get selected season number from dropdown
        selected = dropdown.get_selected()
        if selected != Gtk.INVALID_LIST_POSITION:
            season_text = dropdown.get_model().get_string(selected)
            season_num = season_text.split()[-1]
            self.populate_season(season_num)