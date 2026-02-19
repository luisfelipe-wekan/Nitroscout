import json
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()

class ReviewerAgent:
    """
    Analyzes the JSON findings and selects the most high-signal technical leads.
    """

    def __init__(self, json_path: str):
        self.json_path = Path(json_path)

    def _load_knowledge(self) -> str:
        """
        Loads the scraped knowledge base if available.
        """
        kb_path = Path(__file__).parent.parent / "brain" / "nitro_marketing.md"
        if kb_path.exists():
            return kb_path.read_text(encoding="utf-8").lower()
        return ""

    def analyze_leads(self) -> List[Dict]:
        """
        Reads the JSON and filters leads based on signal strength.
        """
        if not self.json_path.exists():
            console.print(f"[bold red]❌ JSON file not found: {self.json_path}[/bold red]")
            return []

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        knowledge_base = self._load_knowledge()
        high_signal = []
        
        for title, info in data.items():
            score = 0
            reasons = []
            
            # Combine all text context (Title + Post + Comments)
            comments = info.get("comments", [])
            comment_text = " ".join([c.get("text", "") for c in comments if c.get("text")])
            full_context = (title + " " + info.get("post", "") + " " + comment_text).lower()

            # Criterion 1: Engagement
            comment_count = len(comments)
            if comment_count > 15:
                score += 4
                reasons.append(f"Hot thread ({comment_count} comments)")
            elif comment_count > 5:
                score += 2
                reasons.append(f"Active thread ({comment_count} comments)")

            # Criterion 2: Technical MCP/Protocol Match
            technical_keywords = ["mcp", "model context protocol", "mcp server", "mcp client", "sdk"]
            matches = [kw for kw in technical_keywords if kw in full_context]
            if matches:
                score += 3
                reasons.append(f"Technical MCP match: {', '.join(matches[:2])}")

            # Criterion 3: Market Intelligence (Competitors or Pain Points)
            market_keywords = ["alternative to", "vs", "better than", "struggling with", "how do i", "limitations", "issue"]
            found_market = [kw for kw in market_keywords if kw in full_context]
            if found_market:
                score += 2
                reasons.append(f"Market signal: {found_market[0]}")

            # Criterion 4: Knowledge Base Synergy (Nitrostack Match)
            # Simple check: if words from our docs appear in the discussion
            if knowledge_base:
                kb_keywords = ["fastapi", "typescript", "pydantic", "deployment", "setup", "quickstart"]
                kb_matches = [kw for kw in kb_keywords if kw in full_context and kw in knowledge_base]
                if kb_matches:
                    score += 2
                    reasons.append(f"Context matches Nitrostack tech stack: {kb_matches[0]}")

            # Final Selection Threshold: Score >= 5 for high quality
            if score >= 5:
                high_signal.append({
                    "title": title,
                    "url": info.get("url"),
                    "score": score,
                    "reasons": reasons,
                    "comment_count": comment_count
                })

        # Sort by score (descending)
        high_signal.sort(key=lambda x: x["score"], reverse=True)
        return high_signal

    def display_report(self, leads: List[Dict], output_path: Optional[str] = None):
        """
        Prints and optionally saves a beautiful table of the selected leads.
        """
        if not leads:
            console.print("[yellow]⚠️ No high-signal leads identified in this batch.[/yellow]")
            return

        table = Table(title="🎯 High-Signal Technical Leads", show_header=True, header_style="bold magenta")
        table.add_column("Score", style="dim", width=6)
        table.add_column("Title", style="white")
        table.add_column("Comments", justify="right")
        table.add_column("Analysis", style="cyan")

        for lead in leads:
            table.add_row(
                str(lead["score"]),
                lead["title"],
                str(lead["comment_count"]),
                ", ".join(lead["reasons"])
            )

        console.print(table)

        if output_path:
            from rich.console import Console as RichConsole
            file_console = RichConsole(record=True, width=120)
            file_console.print(table)
            export_path = Path(output_path)
            export_path.write_text(file_console.export_text(), encoding="utf-8")
            console.print(f"[dim]📄 Report saved to: {output_path}[/dim]")
