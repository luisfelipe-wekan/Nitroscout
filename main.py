import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from rich.console import Console
from rich.panel import Panel

# Import Agents
from agents.scout import HackerNewsScout
from agents.reddit_scout import RedditScout
from agents.librarian import LibrarianAgent
from agents.reviewer import ReviewerAgent

console = Console()

async def main():
    """
    The Heartbeat of NitroScout.
    """
    console.print(Panel.fit("🚀 NitroScout Protocol Initiated...", style="bold green"))
    
    # 1. Librarian: Update knowledge from docs
    librarian = LibrarianAgent()
    try:
        await librarian.update_knowledge()
    except Exception as e:
        console.print(f"[bold red]❌ Librarian failed: {e}[/bold red]")

    today_str = datetime.now().strftime("%Y-%m-%d")

    # ╔══════════════════════════════════════════╗
    # ║  HACKER NEWS PIPELINE                    ║
    # ╚══════════════════════════════════════════╝
    console.print(Panel("📰 Phase 1: Hacker News", style="bold cyan"))
    
    scout = HackerNewsScout()
    hn_leads = scout.scan(hours_back=24)
    
    if hn_leads:
        hn_dir = Path("agents/scouts/hackernews_posts")
        hn_dir.mkdir(parents=True, exist_ok=True)
        hn_json = hn_dir / f"{today_str}_HN_post.json"
        hn_report = hn_dir / f"{today_str}_HN_report.md"
        
        hn_data = {}
        for lead in hn_leads:
            hn_data[lead["title"]] = {
                "date": lead["date"],
                "url": lead["url"],
                "matched_keywords": [lead["keyword_found"]],
                "post": lead["text"],
                "comments": lead["comments"]
            }
        
        with open(hn_json, "w", encoding="utf-8") as f:
            json.dump(hn_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[bold green]💾 HN data saved to: {hn_json}[/bold green]")

        console.print(Panel("🧠 Analyzing HN leads...", style="bold magenta"))
        reviewer = ReviewerAgent(str(hn_json))
        hn_high_signal = reviewer.analyze_leads()
        reviewer.display_report(hn_high_signal, output_path=str(hn_report))
        console.print(f"[cyan]🎯 HN High-Signal: {len(hn_high_signal)} leads[/cyan]")
    else:
        console.print("[yellow]😴 No HN activity found.[/yellow]")

    # ╔══════════════════════════════════════════╗
    # ║  REDDIT PIPELINE (Two-Phase)             ║
    # ╚══════════════════════════════════════════╝
    console.print(Panel("🟠 Phase 2: Reddit", style="bold yellow"))
    
    reddit_scout = RedditScout(subreddits=["mcp"])
    reddit_leads = reddit_scout.scan(limit=50, sort="hot")
    
    if reddit_leads:
        reddit_dir = Path("agents/scouts/reddit_posts")
        reddit_dir.mkdir(parents=True, exist_ok=True)
        reddit_json = reddit_dir / f"{today_str}_Reddit_post.json"
        reddit_report = reddit_dir / f"{today_str}_Reddit_report.md"

        # Phase 1 save: posts WITHOUT comments (lightweight)
        reddit_data = {}
        for lead in reddit_leads:
            reddit_data[lead["title"]] = {
                "date": lead["date"],
                "url": lead["url"],
                "subreddit": lead["subreddit"],
                "reddit_id": lead["reddit_id"],
                "upvotes": lead["upvotes"],
                "post": lead["text"],
                "comment_count": lead["comment_count"],
                "comments": []  # Empty for now
            }

        # Phase 1 analysis: LLM scores posts based on titles + snippets
        with open(reddit_json, "w", encoding="utf-8") as f:
            json.dump(reddit_data, f, indent=2, ensure_ascii=False)

        console.print(f"[bold green]💾 Reddit data saved to: {reddit_json}[/bold green]")

        console.print(Panel("🧠 Analyzing Reddit leads...", style="bold magenta"))
        reviewer = ReviewerAgent(str(reddit_json))
        reddit_high_signal = reviewer.analyze_leads()

        # Phase 2: Fetch comments ONLY for high-signal posts
        if reddit_high_signal:
            high_signal_titles = [lead["title"] for lead in reddit_high_signal]
            console.print(f"[cyan]🔍 Fetching comments for {len(high_signal_titles)} high-signal posts...[/cyan]")
            reddit_scout.enrich_leads(reddit_leads, high_signal_titles)
            
            # Update JSON with comments
            for lead in reddit_leads:
                if lead["title"] in reddit_data:
                    reddit_data[lead["title"]]["comments"] = lead["comments"]

            with open(reddit_json, "w", encoding="utf-8") as f:
                json.dump(reddit_data, f, indent=2, ensure_ascii=False)

        reviewer.display_report(reddit_high_signal, output_path=str(reddit_report))
        console.print(f"[cyan]🎯 Reddit High-Signal: {len(reddit_high_signal)} leads[/cyan]")
    else:
        console.print("[yellow]😴 No Reddit activity found.[/yellow]")

    console.print(Panel.fit("💤 Heartbeat cycle complete. Sleeping.", style="bold blue"))

if __name__ == "__main__":
    asyncio.run(main())
