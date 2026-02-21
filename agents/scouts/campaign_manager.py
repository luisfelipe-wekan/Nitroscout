import os
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import google.generativeai as genai
from rich.console import Console
from rich.panel import Panel

console = Console()

# ---------------------------------------------------------------------------
# API Key helpers (same pattern as ReviewerAgent)
# ---------------------------------------------------------------------------

def _load_api_keys() -> List[str]:
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


def _read_pdf(pdf_path: Path) -> str:
    """Extracts plain text from a PDF using pypdf. Returns empty string on failure."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        console.print(f"[dim]📄 PDF loaded: {len(text):,} chars from {pdf_path.name}[/dim]")
        return text
    except ImportError:
        console.print("[yellow]⚠️  pypdf not installed — run: pip install pypdf[/yellow]")
        return ""
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not read PDF ({pdf_path.name}): {e}[/yellow]")
        return ""


# ---------------------------------------------------------------------------
# Campaign Manager Agent
# ---------------------------------------------------------------------------

class CampaignManagerAgent:
    """
    Phase 4 of the NitroScout heartbeat.

    Reads all daily scout reports (*.md) from agents/scouts/*/,
    loads the brain/ context (SOUL, COMPETITORS, nitro_marketing, marketing_strategy.pdf),
    and produces a concrete campaign playbook in:
        agents/scouts/campaign_manager/YYYY-MM-DD_campaign.md

    The playbook contains:
      - REPLY drafts for the highest-signal existing threads
      - NEW POST drafts for identified content gaps
      - A priority ranking of all actions
    """

    SCOUTS_DIR = Path(__file__).parent          # agents/scouts/
    BRAIN_DIR = Path(__file__).parent.parent.parent / "brain"   # brain/
    OUTPUT_DIR = Path(__file__).parent / "campaign_manager"     # agents/scouts/campaign_manager/

    def __init__(self):
        self._api_keys = _load_api_keys()
        self._current_key_index = 0
        self.model = None

        if not self._api_keys:
            console.print("[bold red]❌ No API keys found. Campaign Manager cannot use LLM.[/bold red]")
        else:
            console.print(f"[dim]🔑 Campaign Manager: {len(self._api_keys)} API key(s) loaded.[/dim]")
            self._init_model(self._current_key_index)

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _init_model(self, key_index: int):
        if key_index >= len(self._api_keys):
            console.print("[bold red]❌ All API keys exhausted.[/bold red]")
            self.model = None
            return
        genai.configure(api_key=self._api_keys[key_index])
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
        console.print(f"[dim]🔄 Campaign Manager using API key #{key_index + 1}[/dim]")

    def _rotate_key(self) -> bool:
        self._current_key_index += 1
        if self._current_key_index >= len(self._api_keys):
            console.print("[bold red]🚫 All API keys exhausted.[/bold red]")
            self.model = None
            return False
        console.print(f"[yellow]🔄 Rotating to API key #{self._current_key_index + 1}...[/yellow]")
        self._init_model(self._current_key_index)
        return True

    def _call_llm(self, prompt: str) -> Optional[str]:
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
                    console.print(f"[yellow]⚠️  Key #{self._current_key_index + 1} exhausted. Rotating...[/yellow]")
                    if not self._rotate_key():
                        break
                    time.sleep(3)
                    attempt += 1
                else:
                    console.print(f"[bold red]❌ LLM error: {str(e)[:120]}[/bold red]")
                    break
        return None

    # ------------------------------------------------------------------
    # Context loaders
    # ------------------------------------------------------------------

    def _load_text_file(self, path: Path, label: str) -> str:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            console.print(f"[dim]📂 Loaded {label} ({len(text):,} chars)[/dim]")
            return text
        console.print(f"[yellow]⚠️  {label} not found at {path}[/yellow]")
        return ""

    def _load_brain(self) -> Dict[str, str]:
        """Loads all relevant brain/ context files."""
        brain = {}
        brain["soul"] = self._load_text_file(self.BRAIN_DIR / "SOUL.md", "SOUL.md")
        brain["competitors"] = self._load_text_file(self.BRAIN_DIR / "COMPETITORS.md", "COMPETITORS.md")
        brain["product"] = self._load_text_file(self.BRAIN_DIR / "nitro_marketing.md", "nitro_marketing.md")

        pdf_path = self.BRAIN_DIR / "marketing_strategy.pdf"
        brain["strategy"] = _read_pdf(pdf_path) if pdf_path.exists() else ""

        return brain

    def _collect_reports(self, date_str: str) -> List[Dict[str, str]]:
        """
        Globs today's *_report.md files from all platform subdirectories.
        Returns a list of {platform, path, content} dicts.
        """
        reports = []
        for subdir in sorted(self.SCOUTS_DIR.iterdir()):
            # Skip the campaign_manager output folder itself
            if not subdir.is_dir() or subdir.name == "campaign_manager":
                continue
            # Look for today's report first, fall back to any report
            pattern = f"{date_str}_*_report.md"
            matches = sorted(subdir.glob(pattern))
            if not matches:
                # Fallback: most recent report in this folder
                matches = sorted(subdir.glob("*_report.md"))

            if matches:
                report_path = matches[-1]   # most recent
                content = report_path.read_text(encoding="utf-8")
                platform = subdir.name.replace("_posts", "").replace("_", " ").title()
                reports.append({
                    "platform": platform,
                    "path": str(report_path),
                    "content": content,
                })
                console.print(f"[dim]📰 Loaded report: {report_path.name} ({len(content):,} chars)[/dim]")

        return reports

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def _build_prompt(self, reports: List[Dict], brain: Dict[str, str]) -> str:
        """Assembles the full prompt for the Campaign Manager LLM call."""

        # Concatenate all reports, trimmed to avoid token overflow
        reports_block = ""
        for r in reports:
            reports_block += f"\n\n---\n### Platform: {r['platform']}\n{r['content'][:6000]}"

        product_ctx = brain["product"][:800]
        strategy_ctx = (brain["strategy"][:1200] if brain["strategy"]
                        else "No marketing strategy PDF loaded.")
        soul_ctx = brain["soul"][:400]
        competitors_ctx = brain["competitors"][:400]

        return f"""You are the Campaign Manager for NitroStack — the team's elite Developer Relations strategist.

== YOUR PERSONA (non-negotiable) ==
{soul_ctx}

== PRODUCT CONTEXT ==
{product_ctx}

== MARKETING STRATEGY ==
{strategy_ctx}

== COMPETITIVE LANDSCAPE ==
{competitors_ctx}

== TODAY'S SCOUT REPORTS (across all platforms) ==
{reports_block}

---

YOUR TASK:
Produce a concrete, actionable **Campaign Playbook** for today in two parts:

PART 1 — STRATEGIC BRIEF (think, don't just list)
PART 2 — TACTICAL DRAFTS (ready-to-post content)

STRICT RULES:
- Max 5 REPLY opportunities, max 3 NEW POST opportunities (quality > quantity)
- Persona is ALWAYS "Show, don't sell" — answer the real question first, mention NitroStack only when naturally relevant
- NEVER hallucinate features — only reference what is in the Product Context
- Each draft must be complete and ready to copy-paste (not a template)
- Rank all actions by impact × urgency at the end

OUTPUT FORMAT (use exactly this Markdown structure):

# 🗓️ NitroStack Campaign Playbook — {datetime.now().strftime("%B %d, %Y")}

---

## 🧭 Strategic Brief

### 📍 Community Focus
[Rank the top 3–4 communities/platforms from today's reports by opportunity level.
For each: 1 sentence on WHY it's worth attention right now and what signal you saw.]

### 🔑 Brand Relevance Intel
[2–3 sentences: what developer pain points are trending today that NitroStack directly addresses?
Be specific — cite actual thread topics or language from the reports.]

### 💡 New Marketing Angles
[3 concrete, fresh marketing tactics or content angles suggested by today's data.
These should be things the team hasn't necessarily tried — surface insights from the reports.
Format as a short numbered list.]

---

## 💬 Reply Opportunities

### Reply #N — [Platform] · [Score]/10
**Thread:** [Title](URL)
**Why engage:** [1 sentence — the specific pain point this developer has]
**Draft reply:**
> [Full reply text, 3–8 sentences, first-person, helpful tone]

---

## 📝 New Post Opportunities

### Post #N — [Suggested community, e.g. r/mcp or Hacker News]
**Suggested title:** "[Title]"
**Why now:** [1 sentence — what gap this fills based on today's reports]
**Draft post:**
> [Full post body, ready to publish]

---

## 🏆 Priority Ranking
| Priority | Action | Platform | Expected Impact |
|----------|--------|----------|----------------|
| 1 | ... | ... | ... |

---

*Generated by NitroScout Campaign Manager*
"""


    def generate_playbook(self, date_str: str) -> Optional[str]:
        """Full pipeline: load context → call LLM → return markdown string."""
        console.print(Panel("🎯 Campaign Manager — Generating Playbook", style="bold magenta"))

        brain = self._load_brain()
        reports = self._collect_reports(date_str)

        if not reports:
            console.print("[yellow]⚠️  No scout reports found for today. Run scouts first, or check date.[/yellow]")
            return None

        console.print(f"[cyan]📊 Synthesizing {len(reports)} platform report(s) into campaign playbook...[/cyan]")

        prompt = self._build_prompt(reports, brain)
        playbook_md = self._call_llm(prompt)

        if not playbook_md:
            console.print("[bold red]❌ LLM returned no content. Campaign playbook not generated.[/bold red]")
            return None

        return playbook_md

    def run(self, date_str: str) -> Optional[Path]:
        """
        Main entry point. Generates and saves the campaign playbook.
        Returns the output Path on success, None on failure.
        """
        playbook_md = self.generate_playbook(date_str)
        if not playbook_md:
            return None

        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = self.OUTPUT_DIR / f"{date_str}_campaign.md"
        output_path.write_text(playbook_md, encoding="utf-8")

        console.print(f"[bold green]📄 Campaign playbook saved → {output_path}[/bold green]")
        return output_path
