# AGENTS: Operational Manual

## 1. The Scout (Swarm)
- **Hacker News:** Uses Algolia Search API (Unauthenticated).
- **Bluesky:** Uses `atproto` (Authenticated).
- **Stack Overflow:** Uses `stackapi`.
- **Logic:** Aggregates leads into a unified `found_leads.json` list.

## 2. The Reviewer
- **Model:** `Gemini 2.5 Flash`
- **Task:** Scores leads 0–10 in a single batched LLM call. Generates a Community Intelligence Briefing.
- **Output:** `agents/scouts/{platform}/YYYY-MM-DD_*_report.md`

## 3. The Campaign Manager
- **Model:** `Gemini 2.5 Flash`
- **Task:** Reads all daily scout reports + brain/ context (SOUL, COMPETITORS, nitro_marketing, marketing_strategy.pdf) and produces a concrete campaign playbook.
- **Output:** `agents/scouts/campaign_manager/YYYY-MM-DD_campaign.md`
- **Playbook contains:** REPLY drafts for high-signal threads + NEW POST drafts for content gaps + priority ranking.
- **Runnable standalone** (option 4 in menu) using existing reports, or after scouts (option 5).

