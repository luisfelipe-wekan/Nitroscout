import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from rich.console import Console

console = Console()

class HackerNewsScout:
    """
    Scouts Hacker News using the Algolia API (No Auth required).
    """
    BASE_URL = "http://hn.algolia.com/api/v1/search_by_date"
    
    def __init__(self):
        self.keywords = [
            "Model Context Protocol", 
            "MCP server", 
            "Nitrostack",
            "mcp-server"
        ]

    def get_comments(self, object_id: str) -> List[Dict]:
        """
        Fetches all comments for a specific story/item.
        """
        try:
            url = f"http://hn.algolia.com/api/v1/items/{object_id}"
            response = requests.get(url)
            data = response.json()
            
            comments = []
            def flatten_comments(children):
                for child in children:
                    comments.append({
                        "author": child.get("author"),
                        "text": child.get("text"),
                        "created_at": child.get("created_at")
                    })
                    if child.get("children"):
                        flatten_comments(child["children"])
            
            flatten_comments(data.get("children", []))
            return comments
        except Exception as e:
            console.print(f"[dim red]   ⚠️ Failed to fetch comments for {object_id}[/dim red]")
            return []

    def scan(self, hours_back: int = 24) -> List[Dict]:
        """
        Fetches mentions of keywords and their full thread context.
        """
        leads = []
        now_utc = datetime.now(timezone.utc)
        time_threshold = now_utc - timedelta(hours=hours_back)
        
        console.print(f"[cyan]🔭 Scouting Hacker News for: {self.keywords}...[/cyan]")

        for keyword in self.keywords:
            try:
                params = {
                    "query": keyword,
                    "tags": "story", # We focus on stories to get the full thread
                    "hitsPerPage": 50 # Increased from 10 to get more results
                }
                response = requests.get(self.BASE_URL, params=params)
                data = response.json()
                
                for hit in data.get("hits", []):
                    created_at_str = hit["created_at"].replace("Z", "+00:00")
                    created_at = datetime.fromisoformat(created_at_str)
                    
                    if created_at > time_threshold:
                        object_id = hit['objectID']
                        title = hit.get("title") or "No Title"
                        
                        console.print(f"   [dim]Fetching comments for: {title[:50]}...[/dim]")
                        comments = self.get_comments(object_id)
                        
                        leads.append({
                            "source": "HackerNews",
                            "keyword_found": keyword,
                            "title": title,
                            "url": f"https://news.ycombinator.com/item?id={object_id}",
                            "date": hit["created_at"],
                            "text": hit.get("story_text") or "",
                            "comments": comments
                        })
                        
            except Exception as e:
                console.print(f"[bold red]⚠️ Error scanning HN for {keyword}: {e}[/bold red]")

        console.print(f"[green]✅ Processed {len(leads)} stories with comment threads.[/green]")
        return leads
