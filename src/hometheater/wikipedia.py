import requests
from typing import Dict, List, Optional
from pathlib import Path
import re

class Wikipedia:
    """Wikipedia API wrapper for searching cast member information"""
    
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"

    def __init__(self):
        """Initialize with proper headers"""
        self.headers = {
            'User-Agent': self.USER_AGENT
        }

    def _clean_name(self, title: str) -> str:
        """Clean up article title to get just the person's name"""
        # Remove common suffixes
        suffixes = [
            "filmography",
            "bibliography",
            "discography",
            "career",
            "awards",
            "performances",
            "Emmy",
            "Comedy",
            "Drama",
        ]
        name = title
        for suffix in suffixes:
            name = re.sub(rf"\s+{suffix}.*$", "", name, flags=re.IGNORECASE)
        
        # Remove parenthetical clarifications
        name = re.sub(r"\s*\([^)]+\)", "", name)
        
        return name.strip()

    def _validate_person(self, text: str) -> bool:
        """Check if the article is about a person"""
        # Common biographical markers
        markers = [
            r"born",
            r"actor\b",
            r"actress\b",
            r"director\b",
            r"producer\b",
            r"performer\b",
            r"career",
        ]
        
        return any(re.search(marker, text, re.IGNORECASE) for marker in markers)

    def search_person(self, name: str) -> Optional[Dict]:
        """
        Search for a person on Wikipedia
        
        Args:
            name: Name of the person to search for
            
        Returns:
            Dictionary containing person info or None if not found
        """
        # Search Wikipedia API with specific search terms
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f'"{name}" (actor OR actress OR director OR producer)',
            "srlimit": 10  # Get more results to filter
        }

        response = requests.get(self.BASE_URL, params=params, headers=self.headers)
        data = response.json()

        if not data.get("query", {}).get("search"):
            return None

        # Find best matching result
        search_name_parts = set(name.lower().split())
        best_result = None
        best_score = 0
        
        for result in data["query"]["search"]:
            clean_title = self._clean_name(result["title"]).lower()
            title_parts = set(clean_title.split())
            
            # Calculate match score
            score = 0
            
            # Exact match gets highest score
            if clean_title == name.lower():
                score = 100
            else:
                # Add points for each matching word
                matching_words = search_name_parts & title_parts
                score = len(matching_words) * 10
                
                # Bonus points for words in same order
                if all(p in clean_title for p in name.lower().split()):
                    score += 20
                
                # Penalty for extra words
                extra_words = len(title_parts - search_name_parts)
                score -= extra_words * 5
            
            if score > best_score:
                best_score = score
                best_result = result

        if not best_result or best_score < 20:  # Minimum score threshold
            return None

        # Get full article content
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts|pageimages",
            "exintro": True,
            "explaintext": True,
            "piprop": "original",
            "pageids": best_result["pageid"]
        }

        response = requests.get(self.BASE_URL, params=params, headers=self.headers)
        data = response.json()
        page = data["query"]["pages"][str(best_result["pageid"])]
        
        # Validate that this is actually about a person
        if not self._validate_person(page.get("extract", "")):
            return None

        return {
            "name": self._clean_name(best_result["title"]),
            "description": page.get("extract", ""),
            "image_url": page.get("original", {}).get("source"),
            "wikipedia_url": f"https://en.wikipedia.org/?curid={best_result['pageid']}"
        }

    def get_person_image(self, name: str) -> Optional[str]:
        """
        Get the image URL for a person
        
        Args:
            name: Name of the person
            
        Returns:
            Image URL or None if not found
        """
        person = self.search_person(name)
        if person and person.get("image_url"):
            return person["image_url"]
        return None

    def get_person_bio(self, name: str) -> Optional[str]:
        """
        Get a person's biography
        
        Args:
            name: Name of the person
            
        Returns:
            Biography text or None if not found
        """
        person = self.search_person(name)
        if person:
            return person.get("description")
        return None

if __name__ == "__main__":
    wiki = Wikipedia()
    test_names = [
        "Tom Hanks",
        "Sylvester Stallone",
        "Morgan Freeman",
        "Meryl Streep",
        "Leonardo DiCaprio",
        "Brad Pitt"
    ]
    
    for name in test_names:
        person = wiki.search_person(name)
        if person:
            print(f"Search: {name}")
            print(f"Found: {person['name']}")
            print(f"Description: {person['description'][:100]}...\n")
        else:
            print(f"Person not found: {name}\n")