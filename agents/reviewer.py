import json
import os
import time
import re
import google.generativeai as genai
from datetime import datetime
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
    Produces a rich Markdown report with a community insights summary.
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
        """Fast keyword pre-filter before the LLM call."""
        candidates = {}
        for title, info in data.items():
            combined = (title + " " + info.get("post", "")).lower()
            if any(kw in combined for kw in self.PREFILTER_KEYWORDS):
                candidates[title] = info
        console.print(f"[dim]🔎 Pre-filter: {len(data)} posts → {len(candidates)} candidates for LLM.[/dim]")
        return candidates

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Calls the LLM with automatic key rotation on 429. Returns raw text or None."""
        max_retries = len(self._api_keys) * 2
        attempt = 0
        while attempt < max_retries:
            try:
                if not self.model:
                    break
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    console.print(f"[yellow]⚠️ Key #{self._current_key_index + 1} exhausted. Rotating...[/yellow]")
                    if not self._rotate_key():
                        break
                    time.sleep(3)
                    attempt += 1
                else:
                    console.print(f"[bold red]❌ LLM error: {str(e)[:120]}[/bold red]")
                    break
        return None

    def _batch_analyze(self, candidates: Dict, knowledge_context: str) -> List[Dict]:
        """Sends ALL candidates in a SINGLE API call. Returns a list of scored results."""
        if not self.model:
            return []

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
For each post, assign a Relevance Score from 0–10 and write a 1-sentence "Main Idea" analysis.

HIGH scores (7–10) for posts where:
- Developers are building, choosing, or struggling with MCP servers/agents
- New competing tools or MCP frameworks being discussed
- People asking "how do I" / "what's the best" for AI infrastructure
- High-engagement threads on AI tooling

LOW scores (0–4) for:
- Totally unrelated topics (finance, politics, gaming)
- Vague lifestyle/business posts with no technical depth

OUTPUT: Return ONLY a valid JSON array, no markdown fences. Example:
[
  {{"index": 1, "score": 8, "analysis": "Developers debating MCP transport choices — high need for a structured framework like NitroStack."}},
  {{"index": 2, "score": 3, "analysis": "General security scanner with no AI agent angle."}}
]"""

        raw = self._call_llm(prompt)
        if not raw:
            return []

        try:
            text = re.sub(r"^```(?:json)?\s*", "", raw)
            text = re.sub(r"\s*```$", "", text)
            results = json.loads(text)
            scored = []
            for item in results:
                idx = item.get("index", 0) - 1
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
            console.print("[yellow]⚠️ LLM returned non-JSON for batch analysis.[/yellow]")
            return []

    def _generate_insights(self, high_signal: List[Dict], candidates: Dict, knowledge_context: str) -> str:
        """
        Second LLM call: synthesizes all high-signal leads into a strategic
        community intelligence briefing for the NitroStack team.
        """
        if not self.model or not high_signal:
            return ""

        # Build a rich context from the top leads
        lead_summaries = []
        for lead in high_signal[:15]:  # Cap at 15 to save tokens
            info = candidates.get(lead["title"], {})
            top_comments = " | ".join([
                c.get("text", "")[:150]
                for c in info.get("comments", [])[:4]
                if c.get("text")
            ])
            lead_summaries.append(
                f"• [{lead['score']}/10] {lead['title']}\n"
                f"  Analysis: {lead['analysis']}\n"
                f"  Top comments: {top_comments or 'N/A'}"
            )

        leads_text = "\n\n".join(lead_summaries)

        prompt = f"""You are a senior Developer Relations strategist at NitroStack — an open-source TypeScript framework for building production-ready MCP (Model Context Protocol) servers.

NitroStack CONTEXT:
{knowledge_context[:600]}

---
TODAY'S HIGH-SIGNAL COMMUNITY INTELLIGENCE ({len(high_signal)} leads):

{leads_text}

---
YOUR TASK:
Write a sharp, insightful **Community Intelligence Briefing** for the NitroStack founding team. This is an internal strategic document, not marketing copy. Be direct, specific, and actionable.

Structure your response in clean Markdown with these exact sections:

## 🌐 What the Community Is Talking About
A 2-3 sentence synthesis of the dominant themes and conversations happening right now in this space.

## 🔥 Why This Matters for NitroStack
How do these conversations connect to NitroStack's vision and opportunity? What pain points are developers expressing that NitroStack directly solves?

## 🏆 Competitive Landscape
What tools, frameworks, or alternatives are being discussed? What are their perceived strengths/weaknesses compared to NitroStack?

## 🎯 Top 3 Actionable Opportunities
Numbered list. Each opportunity should be specific: which thread, what to say, why it would resonate. Be tactical.

## 💡 Strategic Takeaway
One punchy paragraph: what is the single most important insight from today's scouting that the team should act on this week?

Keep the tone sharp, confident, and data-driven. No fluff."""

        console.print("[cyan]🧠 Generating community insights summary...[/cyan]")
        return self._call_llm(prompt) or ""

    def analyze_leads(self) -> List[Dict]:
        """
        Reads the JSON, pre-filters, then sends ONE batch call to Gemini.
        Returns (high_signal_leads, raw_candidates) for use in report generation.
        """
        if not self.json_path.exists():
            console.print(f"[bold red]❌ JSON file not found: {self.json_path}[/bold red]")
            return []

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        knowledge_base = self._load_knowledge()
        self._candidates = self._prefilter(data)  # Store for later use in report

        if not self._candidates:
            console.print("[yellow]⚠️ No candidates passed pre-filter.[/yellow]")
            return []

        console.print(f"[cyan]🧠 Reviewer sending 1 batch call to Gemini for {len(self._candidates)} candidates...[/cyan]")
        all_scored = self._batch_analyze(self._candidates, knowledge_base)

        high_signal = [lead for lead in all_scored if lead["score"] >= 5]
        high_signal.sort(key=lambda x: x["score"], reverse=True)
        
        self._knowledge_base = knowledge_base  # Store for insights generation
        return high_signal

    def display_report(self, leads: List[Dict], output_path: Optional[str] = None, platform: str = "Hacker News"):
        """Prints a rich table and saves a full Markdown report."""
        if not leads:
            console.print("[yellow]⚠️ No high-signal leads identified in this batch.[/yellow]")
            return

        # --- Console Table (unchanged, great UX) ---
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

        # --- Markdown Report ---
        if output_path:
            # Generate insights (second LLM call)
            candidates = getattr(self, "_candidates", {})
            knowledge_base = getattr(self, "_knowledge_base", "")
            insights_md = self._generate_insights(leads, candidates, knowledge_base)

            date_str = datetime.now().strftime("%B %d, %Y – %H:%M")
            md_lines = [
                f"# 🚀 NitroScout Intelligence Report",
                f"**Date:** {date_str}  |  **Platform:** {platform}  |  **High-Signal Leads:** {len(leads)}",
                "",
                "---",
                "",
                "## 📊 Lead Scoreboard",
                "",
                "| Score | Title | Main Idea | 💬 |",
                "|-------|-------|-----------|-----|",
            ]

            for lead in leads:
                title = lead["title"].replace("|", "\\|")
                analysis = lead["analysis"].replace("|", "\\|")
                url = lead.get("url", "")
                md_lines.append(
                    f"| **{lead['score']}/10** | [{title}]({url}) | {analysis} | {lead['comment_count']} |"
                )

            md_lines += [
                "",
                "---",
                "",
            ]

            if insights_md:
                md_lines += [
                    "## 🧠 Community Intelligence Briefing",
                    "",
                    insights_md,
                    "",
                    "---",
                    "",
                ]

            md_lines += [
                f"*Generated by NitroScout at {date_str}*",
            ]

            report_content = "\n".join(md_lines)
            export_path = Path(output_path)
            export_path.write_text(report_content, encoding="utf-8")
            console.print(f"[bold green]📄 Markdown report saved to: {output_path}[/bold green]")
