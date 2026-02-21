# 🚀 NitroScout

**Automated community intelligence for the NitroStack ecosystem.**

NitroScout is an agentic system that monitors developer communities (Hacker News, Reddit), identifies high-signal conversations about MCP, AI agents, and TypeScript frameworks, and drafts ready-to-use campaign playbooks — replies and new posts — for the team to review and publish.

---

## 🤖 The Agent Team

### 1. 🔭 Scout (Swarm)
Monitors real-time discussions across platforms using keyword heuristics and lightweight pre-filtering.

- **Hacker News** — via Algolia Search API (no auth required)
- **Reddit** — two-phase scraping: scores posts first, then fetches comments only for high-signal threads

**Output:** `agents/scouts/{platform}/YYYY-MM-DD_*_post.json`

---

### 2. 🧠 Reviewer
Analyzes scout data **one community at a time** — one focused LLM call per subreddit (~25 posts, ~3k tokens each), instead of one giant call with all candidates. Shows live progress per community, then merges all results into a final report.

**Per community:**
- Shows: `🧠 Analyzing r/mcp [1/11] (23 candidates, ~2,550 tokens)...`
- Writes: `YYYY-MM-DD_{sub}_scored.md` — lightweight scored list for that community

**Final output:** `agents/scouts/{platform}/YYYY-MM-DD_*_report.md`

---

### 3. 🎯 Campaign Manager
Reads **all platform reports** for the day alongside the team's `brain/` context — product knowledge, marketing strategy PDF, persona guidelines, and competitor notes — then produces a concrete, copy-paste-ready campaign playbook.

**Playbook includes:**
- 💬 **Reply drafts** for the highest-signal existing threads
- 📝 **New post drafts** for content gaps the community is asking about
- 🏆 **Priority ranking** — ordered by impact × urgency

**Output:** `agents/scouts/campaign_manager/YYYY-MM-DD_campaign.md`

> ⚠️ **Draft-only mode** — NitroScout never posts autonomously. A human reviews and fires.

---

## 🧠 The Brain (`brain/`)

The agents read this folder for context. You maintain it manually.

| File | Purpose |
|------|---------|
| `nitro_marketing.md` | Product knowledge base (auto-updated or manual) |
| `marketing_strategy.pdf` | Full marketing strategy — read by Campaign Manager |
| `SOUL.md` | Persona: "Show, don't sell." — the writing voice for all drafts |
| `COMPETITORS.md` | Competing tools and monitoring keywords |
| `AGENTS.md` | Agent operational manual |
| `HEARTBEAT.md` | Loop architecture reference |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Google Gemini API Key

### Installation
```bash
git clone https://github.com/luisfelipe-wekan/Nitroscout.git
cd nitroscout
pip install -r requirements.txt
```

Set up your `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
# Optional — additional keys for rotation on rate limits:
# GOOGLE_API_KEY1=...
# GOOGLE_API_KEY2=...
```

### Running
```bash
python main.py
```

You'll be prompted to select a mode:

```
1 → Hacker News only
2 → Reddit only
3 → Both (full scan)
4 → Campaign Manager only   ← uses existing reports, no new scouting
5 → Full scan + Campaign Manager
```

---

## 📂 Project Structure

```
nitroscout/
├── agents/
│   ├── hn_scout.py             # Hacker News Scout
│   ├── reddit_scout.py       # Reddit Scout (two-phase)
│   ├── reviewer.py           # Reviewer Agent (LLM scoring + briefing)
│   └── scouts/
│       ├── campaign_manager.py           # Campaign Manager Agent
│       ├── hackernews_posts/             # HN raw data + reports
│       ├── reddit_posts/                 # Reddit raw data + reports
│       └── campaign_manager/             # Campaign playbooks
├── brain/                    # Knowledge base (maintained manually)
├── main.py                   # Heartbeat orchestrator
└── requirements.txt
```

---

*Built for the NitroStack ecosystem. Professionalizing AI-assisted community growth.*

