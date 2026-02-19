import asyncio
import os
from crawl4ai import AsyncWebCrawler
from pathlib import Path
from rich.console import Console

console = Console()

class LibrarianAgent:
    """
    Scrapes the Nitrostack documentation to maintain the local knowledge base.
    """
    DOCS_URL = "https://docs.nitrostack.ai"
    KNOWLEDGE_FILE = Path(__file__).parent.parent / "brain" / "nitro_marketing.md"

    async def update_knowledge(self, force: bool = False):
        """
        Crawls the docs and updates the brain only if not present or forced.
        """
        if self.KNOWLEDGE_FILE.exists() and not force:
            console.print(f"[dim cyan]📚 Librarian: Knowledge file already exists at {self.KNOWLEDGE_FILE.name}. Skipping scrape.[/dim cyan]")
            return

        console.print(f"[yellow]📚 Librarian starting crawl of {self.DOCS_URL}...[/yellow]")
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=self.DOCS_URL)
            
            if result.success:
                content = f"# NITROSTACK KNOWLEDGE BASE\n*Last Updated: {os.popen('date').read().strip()}*\n\n"
                # Updated for Crawl4AI 0.8.0+
                content += result.markdown.raw_markdown
                
                self.KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
                self.KNOWLEDGE_FILE.write_text(content, encoding="utf-8")
                
                console.print(f"[green]✅ Librarian updated knowledge base ({len(content)} bytes).[/green]")
            else:
                console.print(f"[bold red]❌ Librarian failed to crawl: {result.error_message}[/bold red]")
