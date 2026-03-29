# Obsidian Output Format

## Archive Index Layout

```md
---
source: jike
generated_at: 2026-03-29T19:27:22+08:00
month_count: 29
item_count: 578
---

# 即刻归档索引

- 共归档 **578** 条内容，覆盖 **29** 个月。
- 时间范围：**2023-06-18** 到 **2026-03-29**。

## 2026

- [[2026-03]] · 67 条
- [[2026-02]] · 24 条
```

## Monthly File Layout

```md
---
source: jike
month: 2026-03
generated_at: 2026-03-29T10:00:00+08:00
item_count: 42
---

# 2026-03 即刻归档

## 月度总结
- 本月共归档 42 条内容，活跃了 10 天。
- 本月最常出现的话题是：AI探索站 (8), 浴室沉思 (6)。

## 2026-03-28

### [21:14](https://m.okjike.com/originalPosts/unique-post-id)
> 话题：AI探索站

正文内容

![](assets/jike/2026-03/unique-post-id-01.jpg)

![](assets/jike/2026-03/unique-post-id-02.jpg)

---
```

## Normalized Item Fields

- `id`: required string, used for dedupe
- `created_at`: required ISO 8601 timestamp with timezone
- `content`: required string, may be empty
- `source_url`: optional string
- `media_links`: optional array of strings
- `media_assets`: optional array of downloaded local asset records
- `topic`: optional string
- `raw_type`: optional string

## Rendering Rules

- Render a vault-level index file named `即刻归档索引.md`.
- Group index links by year and link each month with Obsidian wikilinks like `[[2026-03]]`.
- Sort by `created_at` ascending inside each month.
- Group by local calendar day.
- Keep blank lines between sections for clean Markdown.
- If `content` is empty, render `(no text content)`.
- If `source_url` exists, attach it to the time heading as a Markdown link.
- If `topic` exists, render it as a lightweight `> 话题：...` line.
- Prefer rendering downloaded local image assets as `![](assets/...)` so Obsidian previews them inline.
- Do not render a separate metadata block for source, id, or image links.
- Keep non-image media as normal Markdown links when needed, preferring local files when available.
- Keep the summary section short and note-like, closer to a monthly review than a raw metrics dump.
- Keep summary text in simplified Chinese.
