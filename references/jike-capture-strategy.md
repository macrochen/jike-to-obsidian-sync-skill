# Jike Capture Strategy

This skill separates capture from archive rendering so the archive pipeline stays stable even if the Jike site changes.

## Recommended Adapter Order

1. `json`
   Use when the user already has exported data or when prototyping the archive pipeline.
2. `jike-web`
   Use a browser automation flow with saved login state when live sync is required. Prefer the authenticated web API and keep DOM parsing only as fallback.

## Target Normalized Schema

Each item should be converted into this shape before entering the archive pipeline:

```json
{
  "id": "unique-post-id",
  "created_at": "2026-03-28T21:14:00+08:00",
  "content": "Plain text body",
  "source_url": "https://m.okjike.com/originalPosts/...",
  "media_links": ["https://..."],
  "topic": "optional",
  "raw_type": "note"
}
```

## Browser Adapter Notes

- Prefer Playwright with a persistent browser profile.
- Capture only the user's own posts for the first version.
- Prefer the authenticated `https://api.ruguoapp.com/1.0/personalUpdate/single` endpoint.
- Reuse the `x-jike-access-token` header already sent by the web app.
- Paginate with `loadMoreKey`.
- Stop once the newest seen item from `state.json` is encountered.
- Keep the DOM parser as a fallback when the API contract changes.
- Save only stable fields needed by the archive pipeline.
- Treat selectors as fragile. Keep extraction logic in one script so it can be patched quickly when the page changes.
- Default to a visible browser on the first run because login, CAPTCHA, or profile navigation may require manual action.

## Incremental Sync Rules

- Use `id` as the primary dedupe key.
- Track both `latest_seen_created_at` and `latest_seen_post_id`.
- Keep a short `seen_ids_recent` list to handle same-timestamp items and list order shifts.
- Re-render a month if an item is new or its normalized content changed.

## Failure Handling

- If login expires, pause and ask the user to refresh the session.
- If the page shape changes, fail fast with a clear parser error.
- Never overwrite the sync store with an empty fetch unless the user explicitly confirms a reset.
