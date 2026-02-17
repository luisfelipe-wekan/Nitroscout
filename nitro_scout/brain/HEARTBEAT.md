# HEARTBEAT: The Loop

**Frequency:** Recurring (Cron/While Loop).

**Phase 1: Ingest (The Librarian)**
- Target: `docs.nitrostack.ai`
- Action: Crawl and diff against local knowledge.

**Phase 2: Recon (The Scout Swarm)**
- **Hacker News:** Scan top 200 stories for "MCP", "SDK".
- **Bluesky:** Watch "dev feed" for keywords.
- **Stack Overflow:** Check `nitrostack` or `mcp` tags.
- **GitHub:** Watch relevant repository Discussions.
- Filter: High-signal technical discussions only.

**Phase 3: Response (The Liaison)**
- Constraint: **DRAFT ONLY MODE.**
- Action: Draft helpful response based on `SOUL.md`.
- Output: `/workspace/drafts/{platform}_response_{timestamp}.md`.
