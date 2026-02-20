# HEARTBEAT: The Loop

**Frequency:** Recurring (Cron/While Loop).

**Phase 1: Recon (The Scout Swarm)**
- **Hacker News:** Scan top 200 stories for "MCP", "SDK".
- **Bluesky:** Watch "dev feed" for keywords.
- **Stack Overflow:** Check `nitrostack` or `mcp` tags.
- **GitHub:** Watch relevant repository Discussions.
- Filter: High-signal technical discussions only.

**Phase 3: Review (The Reviewer)**
- **Model:** Gemini 2.5 Flash
- Action: Scores leads 0–10 (batched, 1 API call). Generates Community Intelligence Briefing.
- Output: `agents/scouts/{platform}/YYYY-MM-DD_*_report.md`

**Phase 4: Campaign (The Campaign Manager)**
- **Model:** Gemini 2.5 Flash
- **Constraint:** DRAFT ONLY MODE — never posts autonomously.
- Action: Reads all platform reports + brain/ context. Generates campaign playbook.
- Output: `agents/scouts/campaign_manager/YYYY-MM-DD_campaign.md`
- **Playbook:** REPLY drafts for high-signal threads + NEW POST drafts + priority ranking.

