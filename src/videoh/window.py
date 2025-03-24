# window.py
#
# Copyright 2025 koyu.space
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import json
import requests
import subprocess
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk, Gio, GLib, GdkPixbuf, Pango, Gdk
from gettext import gettext as _
from videoh.imdb import IMDb
from videoh.tvmaze import TVMaze  # Replace TVDB import
from .item import VideohItem
from .player import VideohPlayer
from .episodes import EpisodesUI
import re

@Gtk.Template(resource_path='/space/koyu/videoh/settings.ui')
class VideohPreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'VideohPreferencesWindow'
    
    imdb_switch = Gtk.Template.Child()
    tvmaze_switch = Gtk.Template.Child()
    mal_switch = Gtk.Template.Child()
    auto_fetch_switch = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Gio.Settings.new('space.koyu.videoh')
        
        self.imdb_switch.set_active(self.settings.get_boolean('use-imdb'))
        self.tvmaze_switch.set_active(self.settings.get_boolean('use-tvmaze'))  # Update setting name
        self.mal_switch.set_active(self.settings.get_boolean('use-mal'))
        self.auto_fetch_switch.set_active(self.settings.get_boolean('auto-fetch'))
        
        self.imdb_switch.connect('notify::active', self.on_imdb_switch_active)
        self.tvmaze_switch.connect('notify::active', self.on_tvmaze_switch_active)  # Update method name
        self.mal_switch.connect('notify::active', self.on_mal_switch_active)
        self.auto_fetch_switch.connect('notify::active', self.on_auto_fetch_switch_active)
    
    def on_imdb_switch_active(self, switch, _):
        self.settings.set_boolean('use-imdb', switch.get_active())
    
    def on_tvmaze_switch_active(self, switch, _):  # Rename method
        self.settings.set_boolean('use-tvmaze', switch.get_active())
    
    def on_mal_switch_active(self, switch, _):
        self.settings.set_boolean('use-mal', switch.get_active())
    
    def on_auto_fetch_switch_active(self, switch, _):
        self.settings.set_boolean('auto-fetch', switch.get_active())

@Gtk.Template(resource_path='/space/koyu/videoh/window.ui')
class VideohWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'VideohWindow'

    navigation_view = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    movies_box = Gtk.Template.Child()
    shows_box = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Gio.Settings.new('space.koyu.videoh')
        self.config_dir = Path(GLib.get_user_config_dir()) / "videoh"
        self.cache_dir = Path(GLib.get_user_cache_dir()) / "videoh"
        self.videos_dir = Path.home() / "Videos"
        self.metadata_file = self.config_dir / "metadata.json"
        self.setup_directories()
        self.setup_actions()
        self.load_library()
        self.populate_ui()
        
        # Check for auto-fetch setting
        if self.settings.get_boolean('auto-fetch'):
            GLib.idle_add(self.on_fetch_metadata, None, None)

    def setup_actions(self):
        # Add actions to the application
        actions = [
            ('fetch-metadata', self.on_fetch_metadata),
            ('settings', self.on_settings),
            ('help', self.on_help),
            ('about', self.on_about),
            ('open-folder', self.on_open_folder)
        ]
        
        for action_name, callback in actions:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect('activate', callback)
            self.get_application().add_action(action)

    def setup_directories(self):
        # Create necessary directories if they don't exist
        for directory in [self.config_dir, self.cache_dir, 
                         self.videos_dir / "Movies", 
                         self.videos_dir / "Shows"]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create metadata file if it doesn't exist
        if not self.metadata_file.exists():
            self.metadata_file.write_text("{}")

    def load_library(self):
        # Load existing metadata
        try:
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        except json.JSONDecodeError:
            self.metadata = {}

        # Scan Movies directory
        movies_path = self.videos_dir / "Movies"
        self.movies = []
        for movie_file in movies_path.glob("**/*"):
            if movie_file.is_file() and movie_file.suffix.lower() in ['.mp4', '.mkv', '.avi']:
                movie_data = {
                    'path': str(movie_file),
                    'title': movie_file.stem,
                    'metadata': self.metadata.get(str(movie_file), {})
                }
                self.movies.append(movie_data)

        # Scan Shows directory with seasons support
        shows_path = self.videos_dir / "Shows"
        self.shows = {}
        for show_dir in shows_path.iterdir():
            if show_dir.is_dir():
                seasons = {}
                # Look for season directories or episodes
                for item in show_dir.iterdir():
                    if item.is_dir() and item.name.lower().startswith("season"):
                        # This is a season directory
                        season_num = item.name.lower().replace("season", "").strip()
                        episodes = []
                        for episode_file in item.glob("*"):
                            if episode_file.is_file() and episode_file.suffix.lower() in ['.mp4', '.mkv', '.avi']:
                                episode_data = {
                                    'path': str(episode_file),
                                    'title': episode_file.stem,
                                    'season': season_num,
                                    'metadata': self.metadata.get(str(episode_file), {})
                                }
                                episodes.append(episode_data)
                        if episodes:
                            seasons[season_num] = episodes
                    elif item.is_file() and item.suffix.lower() in ['.mp4', '.mkv', '.avi']:
                        # Episode directly in show directory - assume season 1
                        if "1" not in seasons:
                            seasons["1"] = []
                        episode_data = {
                            'path': str(item),
                            'title': item.stem,
                            'season': "1",
                            'metadata': self.metadata.get(str(item), {})
                        }
                        seasons["1"].append(episode_data)
                
                if seasons:
                    self.shows[show_dir.name] = seasons

    def save_metadata(self):
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def update_metadata(self, file_path, metadata):
        self.metadata[file_path] = metadata
        self.save_metadata()
        # Reload library and update UI
        self.load_library()
        self.populate_ui()

    def download_poster(self, url, movie_title):
        """Download and cache a poster image"""
        if not url:
            return None
            
        # Create a safe filename from the movie title
        safe_title = "".join(c for c in movie_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        poster_filename = f"{safe_title}.jpg"
        poster_path = self.cache_dir / "posters" / poster_filename
        
        # Create posters directory if it doesn't exist
        (self.cache_dir / "posters").mkdir(exist_ok=True)
        
        # Download and save the poster if it doesn't exist
        if not poster_path.exists():
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with open(poster_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                return str(poster_path)
            except Exception as e:
                print(f"Error downloading poster for {movie_title}: {e}")
                return None
        
        return str(poster_path)

    def download_person_image(self, url, person_name, role):
        if not url:
            return None
        safe_name = "".join(c for c in person_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        image_filename = f"{safe_name}.jpg"
        image_path = self.cache_dir / role / image_filename
        
        # Create subdirectory for the role (e.g. "directors" or "cast")
        (self.cache_dir / role).mkdir(exist_ok=True)
        
        if not image_path.exists():
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(image_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return str(image_path)
            except Exception as e:
                print(f"Error downloading {role} image for {person_name}: {e}")
                return None
        return str(image_path)

    def on_fetch_metadata(self, action, param):
        settings = Gio.Settings.new('space.koyu.videoh')
        
        # Fetch movie metadata using IMDb
        if settings.get_boolean('use-imdb'):
            imdb = self.get_imdb()
            
            progress_dialog = Adw.MessageDialog.new(
                self,
                _("Fetching Metadata"),
                _("Please wait while fetching metadata...")
            )
            progress_dialog.present()
            
            try:
                # Fetch movie metadata
                for movie in self.movies:
                    try:
                        results = imdb.search_movie(movie['title'])
                        if results:
                            first_result = results[0]
                            details = imdb.get_movie(first_result['movieID'])
                            
                            if details:
                                # Download and cache the poster
                                poster_url = details.get('full-size cover url', '')
                                local_poster = self.download_poster(poster_url, details.get('title', movie['title']))
                                
                                # Cache director images
                                director_images = []
                                directors = []
                                for director in details.get('directors', []):
                                    if isinstance(director, dict):
                                        director_name = director.get('name', '')
                                        director_img_url = director.get('image', '')
                                        local_dir_img = self.download_person_image(
                                            director_img_url, director_name, "directors"
                                        )
                                        director_images.append(local_dir_img)
                                        directors.append(director_name)
                                
                                # Cache cast images
                                cast_images = []
                                cast = []
                                for actor in details.get('cast', [])[:10]:  # Limit to top 10 cast members
                                    if isinstance(actor, dict):
                                        actor_name = actor.get('name', '')
                                        actor_img_url = actor.get('image', '')
                                        local_cast_img = self.download_person_image(
                                            actor_img_url, actor_name, "cast"
                                        )
                                        cast_images.append(local_cast_img)
                                        cast.append(actor_name)
                                
                                metadata = {
                                    'title': details.get('title', movie['title']),
                                    'plot': details.get('plot outline', ''),
                                    'poster': local_poster,
                                    'poster_url': poster_url,
                                    'rating': details.get('rating', ''),
                                    'genre': details.get('genres', []),
                                    'year': details.get('year', ''),
                                    'directors': directors,
                                    'director_images': director_images,
                                    'cast': cast,
                                    'cast_images': cast_images
                                }
                                
                                # Update movie object with new metadata
                                movie['metadata'] = metadata
                                self.update_metadata(movie['path'], metadata)
                                
                    except Exception as e:
                        print(f"Error fetching metadata for {movie['title']}: {e}")
                        continue
                
                # Fetch TV show metadata
                for show_name, seasons in self.shows.items():
                    try:
                        # Search for show
                        results = imdb.search_tv(show_name)
                        if results:
                            first_result = results[0]
                            show_details = imdb.get_show(first_result['seriesID'])
                            
                            if show_details:
                                # Download and cache show poster
                                poster_url = show_details.get('full-size cover url', '')
                                local_poster = self.download_poster(poster_url, show_name)
                                
                                # Cache creator/showrunner images
                                creator_images = []
                                creators = []
                                for creator in show_details.get('creators', []):
                                    if isinstance(creator, dict):
                                        creator_name = creator.get('name', '')
                                        creator_img_url = creator.get('image', '')
                                        local_creator_img = self.download_person_image(
                                            creator_img_url, creator_name, "creators"
                                        )
                                        creator_images.append(local_creator_img)
                                        creators.append(creator_name)
                                
                                # Cache main cast images
                                cast_images = []
                                cast = []
                                for actor in show_details.get('cast', [])[:10]:
                                    if isinstance(actor, dict):
                                        actor_name = actor.get('name', '')
                                        actor_img_url = actor.get('image', '')
                                        local_cast_img = self.download_person_image(
                                            actor_img_url, actor_name, "cast"
                                        )
                                        cast_images.append(local_cast_img)
                                        cast.append(actor_name)
                                
                                # Create base show metadata
                                show_metadata = {
                                    'title': show_details.get('title', show_name),
                                    'plot': show_details.get('plot outline', ''),
                                    'poster': local_poster,
                                    'poster_url': poster_url,
                                    'rating': show_details.get('rating', ''),
                                    'genre': show_details.get('genres', []),
                                    'year': show_details.get('year', ''),
                                    'creators': creators,
                                    'creator_images': creator_images,
                                    'cast': cast,
                                    'cast_images': cast_images,
                                    'number_of_seasons': show_details.get('number of seasons', 0),
                                    'type': 'show'
                                }
                                
                                # Fetch episode-specific metadata
                                for season_num, episodes in seasons.items():
                                    season_details = imdb.get_season(first_result['seriesID'], int(season_num))
                                    
                                    for episode in episodes:
                                        episode_title = episode['title']
                                        # Find matching episode in season details
                                        for ep_details in season_details.get('episodes', []):
                                            if self._title_matches(episode_title, ep_details.get('title', '')):
                                                episode_metadata = show_metadata.copy()
                                                episode_metadata.update({
                                                    'episode_title': ep_details.get('title', episode_title),
                                                    'episode_plot': ep_details.get('plot', ''),
                                                    'episode_number': ep_details.get('episode number', 0),
                                                    'season_number': season_num,
                                                    'air_date': ep_details.get('original air date', ''),
                                                    'rating': ep_details.get('rating', '')
                                                })
                                                self.update_metadata(episode['path'], episode_metadata)
                                                break
                        
                    except Exception as e:
                        print(f"Error fetching metadata for show {show_name}: {e}")
                        continue

                # Show success toast
                progress_dialog.close()
                toast = Adw.Toast.new(_("Successfully fetched metadata"))
                toast.set_timeout(3)
                self.toast_overlay.add_toast(toast)
                
            except Exception as e:
                progress_dialog.close()
                error_dialog = Adw.MessageDialog.new(
                    self,
                    _("Error"),
                    _("Failed to fetch metadata: {}").format(str(e))
                )
                error_dialog.add_response("ok", _("OK"))
                error_dialog.present()

        # Fetch TV show metadata using TVMaze
        if settings.get_boolean('use-tvmaze'):
            tvmaze = self.get_tvmaze()
            if not tvmaze:
                return
                
            progress_dialog = Adw.MessageDialog.new(
                self,
                _("Fetching Metadata"),
                _("Please wait while fetching metadata from TVMaze...")
            )
            progress_dialog.present()
            
            try:
                for show_name, seasons in self.shows.items():
                    try:
                        # Search for show
                        results = tvmaze.search_tv(show_name)
                        if results:
                            first_result = results[0]
                            show_details = tvmaze.get_show(first_result['seriesID'])
                            
                            if show_details:
                                # Process show metadata first
                                poster_url = show_details.get('full-size cover url', '')
                                local_poster = self.download_poster(poster_url, show_name)
                                
                                # Process cast
                                cast_images = []
                                cast = []
                                for actor in show_details.get('cast', []):
                                    actor_name = actor['name']
                                    actor_img_url = actor.get('image')
                                    if actor_img_url:
                                        local_cast_img = self.download_person_image(
                                            actor_img_url, actor_name, "cast"
                                        )
                                        cast_images.append(local_cast_img)
                                    cast.append(actor_name)
                                
                                # Create show metadata
                                show_metadata = {
                                    'title': show_details['title'],
                                    'plot': show_details['plot outline'],
                                    'poster': local_poster,
                                    'poster_url': poster_url,
                                    'genres': show_details['genres'],
                                    'year': show_details['year'],
                                    'type': 'show',
                                    'is_show': True,
                                    'show_name': show_name,
                                    'rating': show_details.get('rating'),
                                    'cast': cast,
                                    'cast_images': cast_images,
                                    'episodes': {}  # Initialize episodes dict
                                }
                                
                                # Process episodes for each season
                                for season_num, episodes in seasons.items():
                                    # Initialize season array in episodes dictionary
                                    show_metadata['episodes'][str(season_num)] = []

                                    # Get season episodes from TVMaze
                                    season_details = tvmaze.get_season(first_result['seriesID'], int(season_num))

                                    if season_details and 'episodes' in season_details:
                                        tvmaze_episodes = season_details['episodes']

                                        for episode_file in episodes:
                                            ep_num = self._get_episode_number(episode_file['title'])
                                            print(f"Extracted episode number for {episode_file['title']}: {ep_num}")  # Debug print
                                            if ep_num is None:
                                                continue

                                            # Find matching episode in TVMaze data
                                            matching_ep = next(
                                                (ep for ep in tvmaze_episodes 
                                                if ep.get('episode_number') == ep_num),
                                                None
                                            )

                                            if matching_ep:
                                                print(f"Found matching episode for {episode_file['title']}: {matching_ep}")  # Debug print
                                                # Create episode metadata using TVMaze data format
                                                episode_metadata = {
                                                    'type': 'episode',
                                                    'is_episode': True,
                                                    'show_name': show_name,
                                                    'show_title': show_details['title'],
                                                    'episode_title': matching_ep.get('episode_title', episode_file['title']),  # Use TVMaze field name
                                                    'title': matching_ep.get('title', episode_file['title']),
                                                    'episode_number': matching_ep.get('episode_number', ''),
                                                    'season_number': matching_ep.get('season_number', season_num),
                                                    'air_date': matching_ep.get('air_date', ''),
                                                    'rating': matching_ep.get('rating', None),
                                                    'plot': matching_ep.get('plot', ''),
                                                    'image_url': matching_ep.get('image_url', None),
                                                    'runtime': matching_ep.get('runtime', None),
                                                    'poster': local_poster,
                                                    'poster_url': poster_url,
                                                    'file_path': episode_file['path']
                                                }

                                                # Add to show's episode list
                                                show_metadata['episodes'][str(season_num)].append(episode_metadata)

                                                # Also save episode-specific metadata
                                                self.metadata[episode_file['path']] = episode_metadata

                                # Save show metadata
                                show_key = f"show:{show_name}"
                                self.metadata[show_key] = show_metadata

                                # Save to disk
                                self.save_metadata()
                
                    except Exception as e:
                        print(f"Error fetching metadata for show {show_name}: {e}")
                        continue
                
                progress_dialog.close()
                
                # Reload UI
                self.load_library()
                self.populate_ui()
                
            except Exception as e:
                progress_dialog.close()
                error_dialog = Adw.MessageDialog.new(
                    self,
                    _("Error"),
                    _("Failed to fetch metadata from TVMaze: {}").format(str(e))
                )
                error_dialog.add_response("ok", _("OK"))
                error_dialog.present()

    def get_imdb(self):
        """Initialize IMDb client if enabled in settings"""
        if self.settings.get_boolean('use-imdb'):
            try:
                return IMDb()
            except Exception as e:
                dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading=_("IMDb Error"),
                    body=_("Failed to initialize IMDb client: {}").format(str(e))
                )
                dialog.add_response("close", _("Close"))
                dialog.present()
                return None
        return None

    def get_tvmaze(self):  # Rename from get_tvdb
        """Initialize TVMaze client if enabled in settings"""
        if self.settings.get_boolean('use-tvmaze'):  # Update setting name
            try:
                return TVMaze()
            except Exception as e:
                dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading=_("TVMaze Error"),
                    body=_("Failed to initialize TVMaze client: {}").format(str(e))
                )
                dialog.add_response("close", _("Close"))
                dialog.present()
                return None
        return None

    def on_settings(self, action, param):
        settings = VideohPreferencesWindow(transient_for=self)
        settings.present()

    def on_about(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self,
            application_name='Vide OH!',
            application_icon='space.koyu.videoh',
            developer_name='koyu.space',
            version='1.0',
            developers=['Leonie'],
            copyright='© 2025 koyu.space'
        )
        about.present()

    def on_help(self, action, param):
        dialog = Adw.MessageDialog.new(
            self,
            _("Folder Structure"),
            _("Videoh looks for your videos in the following locations:\n\n"
              "~/Videos/Movies/\n"
              "    Place your movie files here\n\n"
              "~/Videos/Shows/\n"
              "    ShowName/\n"
              "        Season 1/\n"
              "            episode1.mp4\n"
              "            episode2.mkv\n"
              "        Season 2/\n"
              "            episode1.mp4\n\n"
              "Files are supported in MP4, MKV and AVI formats.")
        )
        dialog.add_response("ok", _("OK"))
        dialog.present()

    def on_open_folder(self, action, param):
        subprocess.run(['xdg-open', str(self.videos_dir)])

    def populate_ui(self):
        # Clear existing content from FlowBoxes
        self.movies_box.remove_all()
        self.shows_box.remove_all()
        
        # Common function to create poster card
        def create_poster_card(title, metadata, on_click, is_show=False):
            overlay = Gtk.Overlay()
            overlay.add_css_class('poster-box')
            
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.add_css_class('card')
            
            # Add poster image
            poster = metadata.get('poster')
            if (poster and Path(poster).exists()):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    poster, 200, 300, False)
                image = Gtk.Picture.new_for_pixbuf(pixbuf)
            else:
                # Use different fallback icons for shows and movies
                icon_name = "video-television" if is_show else "image-missing"
                image = Gtk.Image.new_from_icon_name(icon_name)
                image.set_pixel_size(200)
            
            image.add_css_class('poster-image')
            box.append(image)
            
            # Add title label
            label = Gtk.Label(label=title)
            label.set_wrap(True)
            label.set_max_width_chars(20)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.add_css_class('heading')
            label.add_css_class('poster-label')
            box.append(label)
            
            # Add info button overlay
            info_button = Gtk.Button()
            info_button.set_icon_name('info-outline-symbolic' if not is_show else 'view-list-symbolic')
            info_button.add_css_class('circular')
            info_button.add_css_class('osd')
            info_button.set_valign(Gtk.Align.START)
            info_button.set_halign(Gtk.Align.END)
            info_button.set_margin_top(6)
            info_button.set_margin_end(6)
            
            # Connect info button click
            info_button.connect('clicked', on_click)
            
            # Add main box and button to overlay
            overlay.set_child(box)
            overlay.add_overlay(info_button)
            
            # Make box clickable
            click = Gtk.GestureClick.new()
            click.connect('pressed', lambda g, n, x, y: on_click(None))
            box.add_controller(click)
            
            return overlay
        
        # Add movies
        for movie in self.movies:
            title = movie.get('metadata', {}).get('title', movie['title'])
            card = create_poster_card(
                title,
                movie.get('metadata', {}),
                lambda _, m=movie: self.show_movie_details(m)
            )
            self.movies_box.append(card)
        
        # Add TV shows
        for show_name, seasons in self.shows.items():
            # Get show metadata from first episode or dedicated show entry
            show_key = f"show:{show_name}"
            show_metadata = self.metadata.get(show_key, {})
            if not show_metadata:
                # Fallback to first episode's metadata if no show metadata exists
                first_season = next(iter(seasons.values()))
                first_episode = first_season[0]
                show_metadata = first_episode.get('metadata', {})
            
            # Create show card
            card = create_poster_card(
                show_name,
                show_metadata,
                lambda _, s=show_name, seas=seasons: self.show_episodes(s, seas),
                is_show=True
            )
            self.shows_box.append(card)

    def show_movie_details(self, movie):
        # Create item view using template
        item_view = VideohItem(self, movie)
        
        # Create navigation page
        page = Adw.NavigationPage(
            title=movie.get('metadata', {}).get('title', movie['title']),
            child=item_view
        )
        
        self.navigation_view.push(page)

    def edit_metadata(self, movie, key, current_value):
        dialog = Adw.MessageDialog(
            transient_for=self,
            title=_("Edit {}").format(key.title()),
            body=_("Enter new value:")
        )
        
        # Add entry for new value
        entry = Gtk.Entry()
        entry.set_text(str(current_value))
        dialog.set_extra_child(entry)
        
        # Add dialog buttons
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("save", _("Save"))
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        
        # Handle response
        def on_response(dialog, response):
            if response == "save":
                new_value = entry.get_text()
                metadata = movie.get('metadata', {}).copy()
                metadata[key] = new_value
                self.update_metadata(movie['path'], metadata)
            dialog.close()
            
        dialog.connect("response", on_response)
        dialog.present()

    def edit_poster(self, movie):
        # Create file chooser
        file_chooser = Gtk.FileChooserNative.new(
            title=_("Choose Poster Image"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label=_("Open"),
            cancel_label=_("Cancel")
        )
        
        # Add file filters
        filter_images = Gtk.FileFilter()
        filter_images.set_name(_("Image files"))
        filter_images.add_mime_type("image/jpeg")
        filter_images.add_mime_type("image/png")
        file_chooser.add_filter(filter_images)  # Changed from set_filters to add_filter
        
        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file_path = dialog.get_file().get_path()
                # Copy image to cache directory
                safe_title = "".join(c for c in movie['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                poster_filename = f"{safe_title}.jpg"
                poster_path = self.cache_dir / "posters" / poster_filename
                
                # Create posters directory if it doesn't exist
                (self.cache_dir / "posters").mkdir(exist_ok=True)
                
                # Convert and save image
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_path)
                    pixbuf = pixbuf.scale_simple(200, 300, GdkPixbuf.InterpType.BILINEAR)
                    pixbuf.savev(str(poster_path), "jpeg", [], [])
                    
                    # Update metadata
                    metadata = movie.get('metadata', {}).copy()
                    metadata['poster'] = str(poster_path)
                    self.update_metadata(movie['path'], metadata)
                    
                    # Show success toast
                    toast = Adw.Toast.new(_("Poster updated successfully"))
                    toast.set_timeout(3)
                    self.toast_overlay.add_toast(toast)
                    
                except Exception as e:
                    error_dialog = Adw.MessageDialog.new(
                        self,
                        _("Error"),
                        _("Failed to update poster: {}").format(str(e))
                    )
                    error_dialog.add_response("ok", _("OK"))
                    error_dialog.present()
        
        file_chooser.connect("response", on_response)
        file_chooser.show()

    def on_movie_activated(self, movie):
        item_window = VideohItem(self, movie)
        item_window.present()

    def on_movie_clicked(self, gesture, n_press, x, y, movie):
        if n_press == 1:  # Only respond to single clicks
            self.show_movie_details(movie)

    def show_video(self, video_path, name):
        """Show video in player view"""
        player_view = VideohPlayer(self, video_path)
        page = Adw.NavigationPage(
            title=name,
            child=player_view
        )
        self.navigation_view.push(page)

    def show_episodes(self, show_name, seasons):
        """Show episodes list for a TV show"""
        episodes_view = EpisodesUI(self, show_name, seasons)
        page = Adw.NavigationPage(
            title=show_name,
            child=episodes_view
        )
        self.navigation_view.push(page)

    def on_show_clicked(self, gesture, n_press, x, y, show_name, seasons):
        if n_press == 1:  # Only respond to single clicks
            self.show_episodes(show_name, seasons)

    def _title_matches(self, file_title, imdb_title):
        """Compare file name with IMDb title, ignoring case and special characters"""
        def clean_title(title):
            return ''.join(c.lower() for c in title if c.isalnum())
        
        return clean_title(file_title) == clean_title(imdb_title)

    def _get_episode_number(self, filename):
        """Extract episode number from filename"""
        try:
            match = re.search(r'[Ss]\d+[Ee](\d+)|[Ee](\d+)|(\d+)$', filename)
            if match:
                return int(match.group(1) or match.group(2) or match.group(3))
        except Exception as e:
            print(f"Error extracting episode number from {filename}: {e}")  # Debug print
        return None

    def get_episode_metadata(self, episode_path):
        """Get combined show and episode metadata"""
        metadata = self.metadata.get(episode_path, {})
        if metadata.get('is_episode'):
            show_key = f"show:{metadata.get('show_name')}"
            show_metadata = self.metadata.get(show_key, {})
            # Merge show and episode metadata
            return {**show_metadata, **metadata}
        return metadata
