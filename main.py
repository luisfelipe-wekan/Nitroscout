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

    # 2. Scout: Fetch real HN Data
    scout = HackerNewsScout()
    leads = scout.scan(hours_back=24)
    
    if not leads:
        console.print("[yellow]😴 No new activity found. Shutting down.[/yellow]")
        return

    # 3. Save Findings to JSON
    today_str = datetime.now().strftime("%Y-%m-%d")
    save_dir = Path("agents/scouts/hackernews_posts")
    save_dir.mkdir(parents=True, exist_ok=True)
    json_filename = save_dir / f"{today_str}_HN_post.json"
    report_filename = save_dir / f"{today_str}_HN_report.md"
    
    # Structure data: Keys are titles
    json_data = {}
    for lead in leads:
        json_data[lead["title"]] = {
            "date": lead["date"],
            "url": lead["url"],
            "matched_keywords": [lead["keyword_found"]],
            "post": lead["text"],
            "comments": lead["comments"]
        }
    
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    console.print(f"[bold green]💾 Saved all findings to: {json_filename}[/bold green]")

    # 4. Reviewer: Analysis and selection
    console.print(Panel("🧠 Analyzing leads for high-signal matches...", style="bold magenta"))
    reviewer = ReviewerAgent(str(json_filename))
    high_signal_leads = reviewer.analyze_leads()
    
    # Display and Save the beautiful report
    reviewer.display_report(high_signal_leads, output_path=str(report_filename))

    console.print(f"\n[cyan]🎯 Total High-Signal Leads found: {len(high_signal_leads)}[/cyan]")
    console.print("[bold blue]💤 Heartbeat cycle complete. Sleeping.[/bold blue]")

if __name__ == "__main__":
    asyncio.run(main())
