import requests
from pathlib import Path
from typing import Dict, List, Optional
import json

class TVMaze:
    def __init__(self):
        self.base_url = "https://api.tvmaze.com"
        self.headers = {
            'User-Agent': 'HomeTheater/1.0 (https://github.com/koyu/hometheater)',
            'Accept': 'application/json'
        }

    def search_tv(self, query: str) -> List[Dict]:
        """Search for TV shows"""
        url = f"{self.base_url}/search/shows"
        params = {'q': query}
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            results = response.json()
            
            cleaned_results = []
            for result in results:
                show = result['show']
                cleaned_results.append({
                    'seriesID': str(show['id']),
                    'title': show['name'],
                    'year': str(show['premiered'][:4]) if show.get('premiered') else '',
                    'url': show['url']
                })
            return cleaned_results
            
        except Exception as e:
            print(f"Error searching shows: {e}")
            return []

    def get_show(self, show_id: str) -> Optional[Dict]:
        """Get detailed show information"""
        try:
            # Get main show info
            show_url = f"{self.base_url}/shows/{show_id}"
            show_response = requests.get(show_url, headers=self.headers)
            show_response.raise_for_status()
            show = show_response.json()
            
            # Get cast info
            cast_url = f"{self.base_url}/shows/{show_id}/cast"
            cast_response = requests.get(cast_url, headers=self.headers)
            cast_response.raise_for_status()
            cast_data = cast_response.json()
            
            # Process cast information
            cast = []
            for member in cast_data[:10]:  # Limit to top 10
                person = member['person']
                cast.append({
                    'name': person['name'],
                    'image': person.get('image', {}).get('original') if person.get('image') else None
                })
            
            return {
                'title': show['name'],
                'plot outline': show.get('summary', '').replace('<p>', '').replace('</p>', ''),
                'full-size cover url': show.get('image', {}).get('original') if show.get('image') else None,
                'genres': show.get('genres', []),
                'year': str(show['premiered'][:4]) if show.get('premiered') else '',
                'cast': cast,
                'type': 'show',
                'rating': str(show.get('rating', {}).get('average', '')) if show.get('rating') else None
            }
            
        except Exception as e:
            print(f"Error fetching show data: {e}")
            return None

    def get_season(self, show_id: str, season_number: int) -> Dict:
        """Get episode information for a specific season"""
        try:
            # Get all episodes
            url = f"{self.base_url}/shows/{show_id}/episodes"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            all_episodes = response.json()
            
            # Filter episodes for specific season
            season_episodes = [ep for ep in all_episodes if ep['season'] == season_number]
            
            cleaned_episodes = []
            for ep in season_episodes:
                # Clean up HTML from summary
                summary = ep.get('summary', '')
                if summary:
                    summary = summary.replace('<p>', '').replace('</p>', '').replace('<br>', '\n')
                
                cleaned_episodes.append({
                    'episode_title': ep['name'],
                    'title': ep['name'],
                    'episode_number': ep['number'],
                    'season_number': season_number,
                    'air_date': ep.get('airdate', ''),
                    'rating': str(ep.get('rating', {}).get('average', '')) if ep.get('rating') else None,
                    'plot': summary,
                    'image_url': ep.get('image', {}).get('original') if ep.get('image') else None,
                    'runtime': ep.get('runtime'),
                    'type': 'episode',
                    'is_episode': True
                })
            
            return {
                'season_number': season_number,
                'episodes': sorted(cleaned_episodes, key=lambda x: x['episode_number'] or 0)
            }
            
        except Exception as e:
            print(f"Error fetching season data: {e}")
            return {'season_number': season_number, 'episodes': []}

    def download_image(self, url: str, save_path: str) -> Optional[str]:
        """Download and save an image from URL"""
        if not url or not save_path:
            return None
            
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(response.content)
                return str(save_path)
        except Exception as e:
            print(f"Error downloading image: {e}")
        return None


if __name__ == '__main__':
    # Test the API
    tvmaze = TVMaze()
    print("Searching for Breaking Bad...")
    results = tvmaze.search_tv("Breaking Bad")
    print(f"Search results: {json.dumps(results, indent=2)}\n")
    
    if results:
        show_id = results[0]['seriesID']
        print(f"Getting show details for ID {show_id}...")
        show = tvmaze.get_show(show_id)
        print(f"Show details: {json.dumps(show, indent=2)}\n")
        
        print("Getting season 1 episodes...")
        season = tvmaze.get_season(show_id, 1)
        print(f"Season details: {json.dumps(season, indent=2)}")

        print("Getting show episodes...")
        all_episodes = tvmaze.get_season(show_id, 1)
        print(f"Show episodes: {json.dumps(all_episodes, indent=2)}")