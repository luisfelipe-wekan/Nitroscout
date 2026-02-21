import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Load environment variables first
load_dotenv()

from agents.hn_scout import HackerNewsScout
from agents.reddit_scout import RedditScout
from agents.reviewer import ReviewerAgent
from agents.scouts.campaign_manager import CampaignManagerAgent

console = Console()

def ensure_dir(path: Path) -> Path:
    """Creates the directory (and parents) if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def select_platforms() -> list[str]:
    """
    Interactive terminal menu to select which platforms to scout.
    Options: HackerNews, Reddit, both, Campaign Manager only, or full scan + campaign.
    """
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🎯 NitroScout — Platform Selection[/bold cyan]\n\n"
        "[white]1[/white] → Hacker News only\n"
        "[white]2[/white] → Reddit only\n"
        "[white]3[/white] → Both (full scan)\n"
        "[white]4[/white] → [bold magenta]Campaign Manager[/bold magenta] only (uses existing reports)\n"
        "[white]5[/white] → [bold magenta]Full scan + Campaign Manager[/bold magenta]",
        title="Select Platform",
        border_style="cyan"
    ))

    choice = Prompt.ask(
        "[bold yellow]Your choice[/bold yellow]",
        choices=["1", "2", "3", "4", "5"],
        default="3"
    )

    return {
        "1": ["hackernews"],
        "2": ["reddit"],
        "3": ["hackernews", "reddit"],
        "4": ["campaign_manager"],
        "5": ["hackernews", "reddit", "campaign_manager"],
    }[choice]


async def run_hackernews(today_str: str):
    """Runs the full Hacker News scouting pipeline."""
    console.print(Panel("📰 Hacker News Pipeline", style="bold cyan"))

    scout = HackerNewsScout()
    leads = scout.scan(hours_back=24)

    if not leads:
        console.print("[yellow]😴 No HN activity found.[/yellow]")
        return

    save_dir = ensure_dir(Path("agents/scouts/hackernews_posts"))
    json_file = save_dir / f"{today_str}_HN_post.json"
    report_file = save_dir / f"{today_str}_HN_report.md"

    hn_data = {}
    for lead in leads:
        hn_data[lead["title"]] = {
            "date": lead["date"],
            "url": lead["url"],
            "matched_keywords": [lead["keyword_found"]],
            "post": lead["text"],
            "comments": lead["comments"],
        }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(hn_data, f, indent=2, ensure_ascii=False)
    console.print(f"[bold green]💾 HN data saved to: {json_file}[/bold green]")

    reviewer = ReviewerAgent(str(json_file))
    high_signal = reviewer.analyze_leads(output_dir=save_dir)
    reviewer.display_report(high_signal, output_path=str(report_file), platform="Hacker News")


async def run_reddit(today_str: str):
    """Runs the full Reddit scouting pipeline (two-phase, tiered subreddits)."""
    console.print(Panel("🟠 Reddit Pipeline", style="bold yellow"))

    # ── Tier 1: High-signal, 50 posts each ────────────────────────────────
    # Direct MCP/agent builder communities — maximum relevance.
    tier1 = RedditScout(subreddits=[
        "mcp",                  # The MCP community
        "AI_Agents",            # AI agent builders
        "LLMDevs",              # Building with LLMs
        "ClaudeAI",             # MCP is Claude's native protocol
        "aiengineering",        # Applied AI engineering
        "typescript",           # NitroStack's language
        "LocalLLaMA",           # Largest technical AI community
        "OpenAIDev",            # API developers
        "LangChain",            # Agent framework users (potential migrants)
        "RAG",                  # Pipeline builders
        "softwarearchitecture", # Architecture decisions = NitroStack's pitch
    ])

    # ── Tier 2: Adjacent signal, 15 posts each ──────────────────────────────
    # Useful for launch visibility and broader ecosystem, but noisier.
    tier2 = RedditScout(subreddits=[
        "startups",         # Launch visibility
        "indiehackers",     # Launch visibility
        "node",             # Runtime ecosystem
        "MachineLearning",  # Technical depth
        "devops",           # Infrastructure angle
        "selfhosted",       # Self-hosted MCP servers niche
        "AutoGPT",          # Agent builders
        "LanguageModels",   # Technical LLM discussions
    ])

    console.print("[dim]🔍 Scanning Tier 1 (11 subs × 50 posts)...[/dim]")
    leads_t1 = tier1.scan(limit=50, sort="hot")

    console.print("[dim]🔍 Scanning Tier 2 (8 subs × 15 posts)...[/dim]")
    leads_t2 = tier2.scan(limit=15, sort="hot")

    leads = leads_t1 + leads_t2
    console.print(f"[dim]📥 Total raw leads: {len(leads_t1)} (T1) + {len(leads_t2)} (T2) = {len(leads)}[/dim]")


    if not leads:
        console.print("[yellow]😴 No Reddit activity found.[/yellow]")
        return

    save_dir = ensure_dir(Path("agents/scouts/reddit_posts"))
    json_file = save_dir / f"{today_str}_Reddit_post.json"
    report_file = save_dir / f"{today_str}_Reddit_report.md"

    # Phase 1: Save lightweight data (no comments yet)
    reddit_data = {}
    for lead in leads:
        reddit_data[lead["title"]] = {
            "date": lead["date"],
            "url": lead["url"],
            "subreddit": lead["subreddit"],
            "reddit_id": lead["reddit_id"],
            "upvotes": lead["upvotes"],
            "post": lead["text"],
            "comment_count": lead["comment_count"],
            "comments": [],
        }

    ensure_dir(save_dir)  # Guarantee dir exists before every write
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(reddit_data, f, indent=2, ensure_ascii=False)
    console.print(f"[bold green]💾 Reddit data saved to: {json_file}[/bold green]")

    # LLM scoring pass (per-subreddit mini-batches)
    reviewer = ReviewerAgent(str(json_file))
    high_signal = reviewer.analyze_leads(output_dir=save_dir)

    # Phase 2: Fetch comments only for high-signal posts
    if high_signal:
        high_signal_titles = {lead["title"] for lead in high_signal}
        console.print(f"[cyan]🔍 Fetching comments for {len(high_signal_titles)} high-signal posts...[/cyan]")
        tier1.enrich_leads(leads, list(high_signal_titles))

        # Update JSON with enriched comments
        for lead in leads:
            if lead["title"] in reddit_data:
                reddit_data[lead["title"]]["comments"] = lead.get("comments", [])

        ensure_dir(save_dir)  # Ensure dir before second write too
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(reddit_data, f, indent=2, ensure_ascii=False)

    subs = ', r/'.join(tier1.subreddits + tier2.subreddits)
    reviewer.display_report(high_signal, output_path=str(report_file), platform=f"Reddit r/{subs}")
    console.print(f"[cyan]🎯 Reddit High-Signal leads found: {len(high_signal)}[/cyan]")


async def run_campaign_manager(today_str: str):
    """Runs the Campaign Manager: reads all scout reports and generates a campaign playbook."""
    console.print(Panel("🎯 Campaign Manager Pipeline", style="bold magenta"))
    agent = CampaignManagerAgent()
    output_path = agent.run(today_str)
    if output_path:
        console.print(f"[bold magenta]✅ Campaign playbook ready: {output_path}[/bold magenta]")
    else:
        console.print("[yellow]⚠️  Campaign Manager produced no output.[/yellow]")


async def main():
    """The Heartbeat of NitroScout."""
    console.print(Panel.fit("🚀 NitroScout Protocol Initiated...", style="bold green"))

    # 1. Select platforms
    platforms = select_platforms()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # 2. Run selected scout pipelines
    if "hackernews" in platforms:
        await run_hackernews(today_str)

    if "reddit" in platforms:
        await run_reddit(today_str)

    # 3. Campaign Manager (standalone or after scouts)
    if "campaign_manager" in platforms:
        await run_campaign_manager(today_str)

    console.print(Panel.fit("💤 Heartbeat cycle complete. Sleeping.", style="bold blue"))


if __name__ == "__main__":
    asyncio.run(main())
