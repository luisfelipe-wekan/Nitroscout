import requests
import time
from datetime import datetime, timezone
from typing import List, Dict
from rich.console import Console

console = Console()


class RedditScout:
    """
    Scouts Reddit subreddits using the public .json endpoints.
    No API key or OAuth required.
    
    Two-phase design:
      Phase 1: Fetch post listing (titles + snippets) — 1 HTTP request
      Phase 2: Fetch comments ONLY for posts the Reviewer marks as high-signal
    """

    HEADERS = {"User-Agent": "NitroScout/1.0 (community research bot)"}
    REQUEST_DELAY = 1.5  # seconds between requests to be polite

    def __init__(self, subreddits: List[str] = None):
        self.subreddits = subreddits or ["mcp"]

    def scan(self, limit: int = 50, sort: str = "hot") -> List[Dict]:
        """
        Phase 1: Fetches post listings from all configured subreddits.
        Returns lightweight lead dicts (no comments yet — those come in Phase 2).
        """
        leads = []

        for subreddit in self.subreddits:
            console.print(f"[cyan]🔭 Scouting Reddit r/{subreddit} ({sort}, limit={limit})...[/cyan]")

            try:
                url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
                params = {"limit": limit, "raw_json": 1}
                response = requests.get(url, headers=self.HEADERS, params=params, timeout=15)

                if response.status_code == 429:
                    console.print("[yellow]⏳ Reddit rate limit hit. Sleeping 10s...[/yellow]")
                    time.sleep(10)
                    response = requests.get(url, headers=self.HEADERS, params=params, timeout=15)

                if response.status_code != 200:
                    console.print(f"[bold red]⚠️ Reddit returned {response.status_code} for r/{subreddit}[/bold red]")
                    continue

                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    p = post.get("data", {})

                    # Skip stickied mod posts
                    if p.get("stickied", False):
                        continue

                    leads.append({
                        "source": "Reddit",
                        "subreddit": subreddit,
                        "title": p.get("title", "No Title"),
                        "url": f"https://www.reddit.com{p.get('permalink', '')}",
                        "reddit_id": p.get("id", ""),
                        "date": datetime.fromtimestamp(
                            p.get("created_utc", 0), tz=timezone.utc
                        ).isoformat(),
                        "text": p.get("selftext", ""),
                        "upvotes": p.get("score", 0),
                        "comment_count": p.get("num_comments", 0),
                        "comments": [],  # Empty — filled in Phase 2
                    })

                console.print(f"[green]   ✅ Fetched {len(posts)} posts from r/{subreddit}[/green]")
                time.sleep(self.REQUEST_DELAY)

            except Exception as e:
                console.print(f"[bold red]⚠️ Error scouting r/{subreddit}: {e}[/bold red]")

        console.print(f"[green]✅ Reddit Scout total: {len(leads)} posts (comments pending).[/green]")
        return leads

    def fetch_comments(self, lead: Dict, max_comments: int = 20) -> List[Dict]:
        """
        Phase 2: Fetches the comment tree for a single post.
        Called only for posts the Reviewer has marked as high-signal.
        """
        subreddit = lead.get("subreddit", "mcp")
        reddit_id = lead.get("reddit_id", "")
        if not reddit_id:
            return []

        try:
            url = f"https://www.reddit.com/r/{subreddit}/comments/{reddit_id}/.json"
            params = {"limit": max_comments, "sort": "best", "raw_json": 1}
            response = requests.get(url, headers=self.HEADERS, params=params, timeout=15)

            if response.status_code != 200:
                console.print(f"[dim red]   ⚠️ Failed to fetch comments for {reddit_id}[/dim red]")
                return []

            data = response.json()
            # data[0] = post info, data[1] = comment listing
            comment_listing = data[1].get("data", {}).get("children", [])

            comments = []
            def flatten(children_list, depth=0):
                for child in children_list:
                    if child.get("kind") != "t1":  # t1 = comment
                        continue
                    cd = child.get("data", {})
                    comments.append({
                        "author": cd.get("author", "[deleted]"),
                        "text": cd.get("body", ""),
                        "score": cd.get("score", 0),
                        "depth": depth,
                    })
                    # Recurse into replies
                    replies = cd.get("replies")
                    if replies and isinstance(replies, dict):
                        reply_children = replies.get("data", {}).get("children", [])
                        flatten(reply_children, depth + 1)

            flatten(comment_listing)
            return comments[:max_comments]  # Cap

        except Exception as e:
            console.print(f"[dim red]   ⚠️ Error fetching comments for {reddit_id}: {e}[/dim red]")
            return []

    def enrich_leads(self, leads: List[Dict], high_signal_titles: List[str]) -> Dict:
        """
        Phase 2 orchestrator: fetches comments only for high-signal leads.
        Returns the enriched JSON data dict keyed by title.
        """
        enriched_count = 0
        for lead in leads:
            if lead["title"] in high_signal_titles:
                console.print(f"   [dim]Fetching comments for: {lead['title'][:50]}...[/dim]")
                lead["comments"] = self.fetch_comments(lead)
                enriched_count += 1
                time.sleep(self.REQUEST_DELAY)

        console.print(f"[green]✅ Enriched {enriched_count} high-signal posts with comments.[/green]")
        return leads
