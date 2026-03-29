#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate simple factual summary bullets for one month of Jike items."
    )
    parser.add_argument("--input-json", required=True, help="Path to a JSON file containing month items.")
    return parser.parse_args()


def load_items(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of items.")
    return data


def summarize_items(items: list[dict]) -> list[str]:
    if not items:
        return ["本月还没有归档到任何即刻内容。"]

    sorted_items = sorted(items, key=lambda item: item["created_at"])
    parsed_dates = [datetime.fromisoformat(item["created_at"]) for item in sorted_items]
    day_count = len({dt.date().isoformat() for dt in parsed_dates})
    media_count = sum(1 for item in items if item.get("media_links"))
    longest = max(items, key=lambda item: len(item.get("content", "").strip()))
    longest_length = len(longest.get("content", "").strip())
    topic_counter = Counter(item.get("topic", "").strip() or "Uncategorized" for item in items)
    top_topics = topic_counter.most_common(3)
    top_topics_text = ", ".join(f"{topic} ({count})" for topic, count in top_topics)
    longest_date = datetime.fromisoformat(longest["created_at"]).date().isoformat()
    first_date = parsed_dates[0].date().isoformat()
    last_date = parsed_dates[-1].date().isoformat()
    active_dates = [dt.date().isoformat() for dt in parsed_dates]
    busiest_day, busiest_day_count = Counter(active_dates).most_common(1)[0]
    short_entries = [item for item in items if len(item.get("content", "").strip()) <= 80]
    short_entries_count = len(short_entries)

    return [
        f"本月共归档 {len(items)} 条内容，活跃了 {day_count} 天，时间范围从 {first_date} 到 {last_date}。",
        f"发帖最集中的一天是 {busiest_day}，当天共记录 {busiest_day_count} 条。",
        f"本月最常出现的话题是：{top_topics_text}。",
        f"带媒体链接的内容有 {media_count} 条，短笔记风格的内容有 {short_entries_count} 条。",
        f"最长的一条发布于 {longest_date}，正文约 {longest_length} 字。",
    ]


def main() -> int:
    args = parse_args()
    items = load_items(Path(args.input_json))
    for bullet in summarize_items(items):
        print(f"- {bullet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
