#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Jike archive index for Obsidian.")
    parser.add_argument("--state-dir", required=True, help="Directory containing items.jsonl.")
    parser.add_argument("--output", required=True, help="Markdown output file path.")
    return parser.parse_args()


def parse_created_at(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone()


def load_items(state_dir: Path) -> list[dict]:
    items_path = state_dir / "items.jsonl"
    if not items_path.exists():
        return []

    items: list[dict] = []
    with items_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            items.append(json.loads(line))
    return sorted(items, key=lambda item: (item["created_at"], item["id"]))


def monthly_counts(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[item["created_at"][:7]] += 1
    return dict(counts)


def render_index_markdown(items: list[dict], generated_at: str) -> str:
    counts = monthly_counts(items)
    months = sorted(counts.keys(), reverse=True)
    lines = [
        "---",
        "source: jike",
        f"generated_at: {generated_at}",
        f"month_count: {len(months)}",
        f"item_count: {len(items)}",
        "---",
        "",
        "# 即刻归档索引",
        "",
    ]

    if items:
        first_item = parse_created_at(items[0]["created_at"])
        last_item = parse_created_at(items[-1]["created_at"])
        lines.extend(
            [
                f"- 共归档 **{len(items)}** 条内容，覆盖 **{len(months)}** 个月。",
                f"- 时间范围：**{first_item.strftime('%Y-%m-%d')}** 到 **{last_item.strftime('%Y-%m-%d')}**。",
                f"- 最近一次生成：`{generated_at}`。",
                "",
            ]
        )
    else:
        lines.extend(["- 还没有归档内容。", ""])

    current_year = None
    for month in months:
        year = month[:4]
        if year != current_year:
            current_year = year
            lines.extend([f"## {year}", ""])
        lines.append(f"- [[{month}]] · {counts[month]} 条")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    state_dir = Path(args.state_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items = load_items(state_dir)
    markdown = render_index_markdown(items, datetime.now().astimezone().isoformat(timespec="seconds"))
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
