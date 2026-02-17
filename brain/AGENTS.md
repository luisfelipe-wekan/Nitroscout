# AGENTS: Operational Manual

## 1. The Librarian
- **Lib:** `Crawl4AI`
- **Task:** Maintains `nitro_marketing.md`.

## 2. The Scout (Swarm)
- **Hacker News:** Uses Algolia Search API (Unauthenticated).
- **Bluesky:** Uses `atproto` (Authenticated).
- **Stack Overflow:** Uses `stackapi`.
- **Logic:** Aggregates leads into a unified `found_leads.json` list.

## 3. The Liaison
- **Model:** `Gemini 2.0 Flash`
- **Task:** Synthesis. Reads `found_leads.json` and drafts responses.
