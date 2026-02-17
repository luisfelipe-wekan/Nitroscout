import os
import sys
import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load Config
load_dotenv()
console = Console()

from agents.liaison import draft_response

async def main():
    """
    The Heartbeat of NitroScout.
    """
    console.print(Panel.fit("🚀 NitroScout Protocol Initiated...", style="bold green"))
    
    # 1. Librarian Update (Mocked for now)
    console.print("[yellow]📚 Librarian checking docs...[/yellow]")
    
    # 2. Scout Execution (Mocked for now)
    console.print("[cyan]🔭 Scout scanning frequencies (HN, Bsky, SO)...[/cyan]")
    mock_inquiry = "How does Nitrostack SDK compare to standard MCP servers for data persistence?"
    
    # 3. Liaison Drafting (Functional Test)
    console.print(f"[magenta]✍️ Liaison processing test lead...[/magenta]")
    try:
        draft_path = await draft_response("HackerNews", mock_inquiry)
        console.print(f"[bold green]✅ Draft created at: {draft_path}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Liaison failed: {e}[/bold red]")

    console.print("[bold blue]💤 Heartbeat cycle complete. Sleeping.[/bold blue]")

if __name__ == "__main__":
    asyncio.run(main())
