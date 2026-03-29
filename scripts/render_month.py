#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from summarize_month import summarize_items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render one monthly Jike archive Markdown file.")
    parser.add_argument("--state-dir", required=True, help="Directory containing items.jsonl.")
    parser.add_argument("--month", required=True, help="Month in YYYY-MM format.")
    parser.add_argument("--output", required=True, help="Markdown output file path.")
    return parser.parse_args()


def load_items_for_month(state_dir: Path, month: str) -> list[dict]:
    items_path = state_dir / "items.jsonl"
    if not items_path.exists():
        return []

    items: list[dict] = []
    with items_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if item["created_at"][:7] == month:
                items.append(item)
    return sorted(items, key=lambda item: item["created_at"])


def format_time_heading(dt: datetime, source_url: str) -> str:
    label = dt.strftime('%H:%M')
    if source_url:
        return f"### [{label}]({source_url})"
    return f"### {label}"


def detect_media_kind(url: str) -> str:
    lowered = url.lower()
    if any(token in lowered for token in [".mp4", ".mov", ".m4v", "video"]):
        return "视频"
    return "图片"


def render_topic(topic: str) -> str:
    normalized = (topic or "").strip()
    if not normalized:
        return ""
    return f"#{normalized}"


def media_render_targets(item: dict) -> list[dict]:
    assets = item.get("media_assets") or []
    if assets:
        return assets
    return [
        {
            "source_url": media_link,
            "local_path": "",
            "kind": detect_media_kind(media_link),
        }
        for media_link in (item.get("media_links") or [])
    ]


def render_markdown(month: str, items: list[dict], generated_at: str) -> str:
    lines: list[str] = [
        "---",
        "source: jike",
        f"month: {month}",
        f"generated_at: {generated_at}",
        f"item_count: {len(items)}",
        "---",
        "",
        f"# {month} 即刻归档",
        "",
        "## 月度总结",
    ]

    for bullet in summarize_items(items):
        lines.append(f"- {bullet}")

    if not items:
        lines.extend(["", "No archived items for this month.", ""])
        return "\n".join(lines).rstrip() + "\n"

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["created_at"][:10]].append(item)

    for day in sorted(grouped):
        lines.extend(["", f"## {day}", ""])
        for item in grouped[day]:
            dt = datetime.fromisoformat(item["created_at"])
            content = item.get("content", "").strip() or "(no text content)"
            lines.append(format_time_heading(dt, item.get("source_url", "")))
            lines.append(content)
            lines.append("")
            for media in media_render_targets(item):
                target = media.get("local_path") or media.get("source_url") or ""
                if not target:
                    continue
                if media.get("kind") == "图片":
                    lines.append(f"![]({target})")
                    lines.append("")
                else:
                    lines.append(f"> [视频]({target})")
                    lines.append("")
            topic_line = render_topic(item.get("topic", ""))
            if topic_line:
                lines.append(topic_line)
                lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    state_dir = Path(args.state_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items = load_items_for_month(state_dir, args.month)
    markdown = render_markdown(args.month, items, datetime.now().astimezone().isoformat(timespec="seconds"))
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
