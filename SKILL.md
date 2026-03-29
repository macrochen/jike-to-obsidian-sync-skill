---
name: jike-to-obsidian-sync-skill
description: Sync a user's Jike posts into an Obsidian vault as monthly Markdown archives with incremental state tracking. Use when exporting, syncing, or organizing Jike content into Markdown for long-term personal knowledge management.
---

# Jike To Obsidian Sync

Use this skill when the user wants to archive their own Jike content into Obsidian and keep it synced over time.

## Workflow

1. Confirm the Obsidian vault output directory.
2. Collect Jike items from the selected source adapter.
3. Normalize each item into the archive schema.
4. Merge items into the local sync store and update `state.json`.
5. Re-render only the affected monthly Markdown files.
6. Refresh the monthly summary for each changed month.
7. Rebuild the Obsidian archive index page.

## Current Source Adapters

- `json`: Ready now. Reads normalized or lightly structured JSON exported from another tool.
- `jike-web`: Uses Playwright with a persistent Chromium profile, captures the authenticated Jike web API response, and falls back to DOM parsing only if the API path fails.

Read [references/jike-capture-strategy.md](references/jike-capture-strategy.md) before building or updating the live Jike capture adapter.

## Commands

Bootstrap the live browser adapter:

```bash
./scripts/bootstrap.sh
```

Run the default live sync for the current Jike account and Obsidian vault:

```bash
./scripts/sync-now.sh
```

Override defaults when needed:

```bash
JKE_START_URL="https://web.okjike.com/u/your-profile" \
JKE_OUTPUT_ROOT="/path/to/Obsidian/Jike" \
./scripts/sync-now.sh
```

Create or update archives from JSON input:

```bash
./.venv/bin/python scripts/sync_jike.py \
  --source json \
  --input-json /path/to/jike-items.json \
  --output-root /path/to/Obsidian/Jike
```

Re-render a single month from the local sync store:

```bash
./.venv/bin/python scripts/render_month.py \
  --state-dir /path/to/Obsidian/Jike/.jike-sync \
  --month 2026-03 \
  --output /path/to/Obsidian/Jike/2026-03.md
```

Re-render the archive index page:

```bash
./.venv/bin/python scripts/render_index.py \
  --state-dir /path/to/Obsidian/Jike/.jike-sync \
  --output /path/to/Obsidian/Jike/即刻归档索引.md
```

Generate a summary from normalized month data:

```bash
./.venv/bin/python scripts/summarize_month.py \
  --input-json /path/to/month-items.json
```

Run a live sync from Jike Web:

```bash
./.venv/bin/python scripts/sync_jike.py \
  --source jike-web \
  --start-url https://web.okjike.com/u/your-profile \
  --output-root /path/to/Obsidian/Jike
```

On the first run, log in to Jike in the opened browser and use your own profile or note stream URL as `--start-url` when possible. The browser profile is saved under `.jike-sync/browser-profile`.

The live adapter now prefers the authenticated `personalUpdate/single` API exposed by the web app. This provides stable post IDs, absolute timestamps, and cleaner media extraction than pure DOM scraping.

## Files Written

- `<output-root>/.jike-sync/state.json`: sync cursor and metadata
- `<output-root>/.jike-sync/items.jsonl`: normalized item store
- `<output-root>/.jike-sync/browser-profile/`: persistent browser login state for the live web adapter
- `<output-root>/assets/jike/YYYY-MM/`: downloaded local media backups
- `<output-root>/YYYY-MM.md`: monthly Obsidian archive
- `<output-root>/即刻归档索引.md`: Obsidian-friendly archive index page

## Output Rules

- Keep text content.
- Back up media to local files under `assets/jike/` by default for long-term preservation.
- Prefer rendering local media files in Markdown so Obsidian can preview them inline even if remote links expire.
- Keep source links lightweight by attaching them to the time heading instead of rendering a separate metadata block.
- Render the topic for each item as a lightweight bottom tag, close to the Jike post layout.
- Preserve video references as Markdown links when video items appear.
- Group entries by day inside each month file.
- Include a short monthly summary in simplified Chinese.
- Generate a vault-level index page with wikilinks to every archived month.
- Use item `id` as the dedupe key.

Read [references/obsidian-output-format.md](references/obsidian-output-format.md) for the item schema and Markdown layout.
