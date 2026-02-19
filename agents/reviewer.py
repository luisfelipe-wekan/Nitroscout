import json
import os
import time
import re
import google.generativeai as genai
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()

# --- API Key Rotation Pool ---
def _load_api_keys() -> List[str]:
    """Loads all Gemini API keys from environment, deduplicating them."""
    key_names = [
        "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "GOOGLE_API_KEY1", "GOOGLE_API_KEY2",
        "GOOGLE_API_KEY3", "GOOGLE_API_KEY4", "GOOGLE_API_KEY5",
    ]
    seen = set()
    keys = []
    for name in key_names:
        val = os.getenv(name)
        if val and val not in seen:
            seen.add(val)
            keys.append(val)
    return keys

class ReviewerAgent:
    """
    Analyzes the JSON findings using a SINGLE batched LLM call with API key rotation.
    """

    # Cheap pre-filter: only posts containing these go to the LLM
    PREFILTER_KEYWORDS = [
        "mcp", "model context protocol", "agent", "llm", "ai ", "typescript",
        "server", "sdk", "plugin", "tool", "framework", "infrastructure",
        "nitrostack", "nitro", "openai", "anthropic", "gemini", "cursor"
    ]

    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self._api_keys = _load_api_keys()
        self._current_key_index = 0
        self.model = None

        if not self._api_keys:
            console.print("[bold red]❌ No API keys found. Reviewer cannot use LLM.[/bold red]")
        else:
            console.print(f"[dim]🔑 Loaded {len(self._api_keys)} unique API key(s) for rotation.[/dim]")
            self._init_model(self._current_key_index)

    def _init_model(self, key_index: int):
        """Initialises Gemini with the key at the given index."""
        if key_index >= len(self._api_keys):
            console.print("[bold red]❌ All API keys exhausted.[/bold red]")
            self.model = None
            return
        genai.configure(api_key=self._api_keys[key_index])
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        console.print(f"[dim]🔄 Using API key #{key_index + 1}[/dim]")

    def _rotate_key(self) -> bool:
        """Rotates to the next API key. Returns False if all keys are exhausted."""
        self._current_key_index += 1
        if self._current_key_index >= len(self._api_keys):
            console.print("[bold red]🚫 All API keys have been exhausted.[/bold red]")
            self.model = None
            return False
        console.print(f"[yellow]🔄 Rotating to API key #{self._current_key_index + 1}...[/yellow]")
        self._init_model(self._current_key_index)
        return True

    def _load_knowledge(self) -> str:
        """Loads the scraped knowledge base once."""
        kb_path = Path(__file__).parent.parent / "brain" / "nitro_marketing.md"
        if kb_path.exists():
            return kb_path.read_text(encoding="utf-8")
        return "NitroStack is a TypeScript framework for building production-ready MCP servers."

    def _prefilter(self, data: Dict) -> Dict:
        """
        Fast keyword pre-filter to eliminate clearly irrelevant posts.
        Cuts API token cost significantly before the LLM even sees the data.
        """
        candidates = {}
        for title, info in data.items():
            combined = (title + " " + info.get("post", "")).lower()
            if any(kw in combined for kw in self.PREFILTER_KEYWORDS):
                candidates[title] = info
        console.print(f"[dim]🔎 Pre-filter: {len(data)} posts → {len(candidates)} candidates for LLM.[/dim]")
        return candidates

    def _batch_analyze(self, candidates: Dict, knowledge_context: str) -> List[Dict]:
        """
        Sends ALL candidates in a SINGLE API call.
        Returns a list of scored results.
        """
        if not self.model:
            return []

        # Build the numbered list of posts for the prompt
        post_list = []
        titles = list(candidates.keys())
        for i, title in enumerate(titles, 1):
            info = candidates[title]
            snippet = info.get("post", "")[:300] or "[No post body — comments-only thread]"
            comment_count = len(info.get("comments", []))
            post_list.append(f"{i}. TITLE: {title}\n   SNIPPET: {snippet}\n   COMMENTS: {comment_count}")

        posts_text = "\n\n".join(post_list)

        prompt = f"""You are an elite Tech Reviewer for NitroStack, an open-source TypeScript framework for building production-ready MCP (Model Context Protocol) servers.

                YOUR PRODUCT CONTEXT:
                {knowledge_context[:800]}

                ---
                POSTS TO ANALYZE ({len(titles)} total):

                {posts_text}

                ---
                TASK:
                For each post above, determine its relevance and assign a score from 0–10.

                HIGH scores (7–10) go to posts where:
                - Developers are building, choosing, or struggling with MCP servers/agents
                - New competing tools or MCP frameworks are being discussed
                - People are asking "how do I" or "what's the best" for AI infrastructure
                - High-engagement technical threads (many comments) on AI tooling

                LOW scores (0–4) go to:
                - Totally unrelated topics (finance, politics, gaming, etc.)
                - Pure security scanner tools with no MCP/agent angle
                - Vague lifestyle or business posts

                OUTPUT: Return ONLY a valid JSON array, no extra text or markdown fences. Example:
                [
                {{"index": 1, "score": 8, "analysis": "Developers debating MCP transport layer options — high need for a structured framework."}},
                {{"index": 2, "score": 3, "analysis": "Security scanner unrelated to AI agent frameworks."}}
                ]"""

        max_retries = len(self._api_keys) * 2  # Try each key at most twice
        attempt = 0
        while attempt < max_retries:
            try:
                if not self.model:
                    break
                response = self.model.generate_content(prompt)
                text = response.text.strip()

                # Strip markdown fences if model wraps response anyway
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)

                results = json.loads(text)
                scored = []
                for item in results:
                    idx = item.get("index", 0) - 1  # 1-indexed → 0-indexed
                    if 0 <= idx < len(titles):
                        title = titles[idx]
                        info = candidates[title]
                        scored.append({
                            "title": title,
                            "url": info.get("url"),
                            "score": int(item.get("score", 0)),
                            "analysis": item.get("analysis", ""),
                            "comment_count": len(info.get("comments", []))
                        })
                return scored

            except json.JSONDecodeError:
                console.print("[yellow]⚠️ LLM returned non-JSON. Retrying with next key...[/yellow]")
                if not self._rotate_key():
                    break
                attempt += 1

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    console.print(f"[yellow]⚠️ Key #{self._current_key_index + 1} exhausted. Rotating...[/yellow]")
                    if not self._rotate_key():
                        break
                    time.sleep(3)
                    attempt += 1
                else:
                    console.print(f"[bold red]❌ Unexpected LLM error: {str(e)[:120]}[/bold red]")
                    break

        console.print("[bold red]❌ Could not complete LLM analysis after all retries.[/bold red]")
        return []

    def analyze_leads(self) -> List[Dict]:
        """
        Reads the JSON, pre-filters with keywords, then sends ONE batch call to Gemini.
        """
        if not self.json_path.exists():
            console.print(f"[bold red]❌ JSON file not found: {self.json_path}[/bold red]")
            return []

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        knowledge_base = self._load_knowledge()

        # Step 1: Cheap pre-filter
        candidates = self._prefilter(data)
        if not candidates:
            console.print("[yellow]⚠️ No candidates passed pre-filter.[/yellow]")
            return []

        # Step 2: Single batch LLM call
        console.print(f"[cyan]🧠 Reviewer sending 1 batch call to Gemini for {len(candidates)} candidates...[/cyan]")
        all_scored = self._batch_analyze(candidates, knowledge_base)

        # Step 3: Filter to high-signal only (score >= 5)
        high_signal = [lead for lead in all_scored if lead["score"] >= 5]
        high_signal.sort(key=lambda x: x["score"], reverse=True)
        return high_signal

    def display_report(self, leads: List[Dict], output_path: Optional[str] = None):
        """Prints and optionally saves a table of the selected leads."""
        if not leads:
            console.print("[yellow]⚠️ No high-signal leads identified in this batch.[/yellow]")
            return

        table = Table(
            title="🎯 High-Signal Technical Leads (LLM Verified)",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Score", style="bold green", width=6)
        table.add_column("Title", style="white", max_width=45)
        table.add_column("Main Idea / Analysis", style="cyan")
        table.add_column("💬", justify="right", width=5)

        for lead in leads:
            title = lead["title"]
            if len(title) > 45:
                title = title[:42] + "..."
            table.add_row(
                str(lead["score"]),
                title,
                lead["analysis"],
                str(lead["comment_count"])
            )

        console.print(table)

        if output_path:
            file_console = Console(record=True, width=140)
            file_console.print(table)
            export_path = Path(output_path)
            export_path.write_text(file_console.export_text(), encoding="utf-8")
            console.print(f"[dim]📄 Report saved to: {output_path}[/dim]")
