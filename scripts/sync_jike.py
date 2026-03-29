#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from render_month import render_markdown
from render_index import render_index_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Jike items into monthly Obsidian archives with incremental state tracking."
    )
    parser.add_argument("--source", choices=["json", "jike-web"], required=True)
    parser.add_argument("--input-json", help="Path to a JSON file for the json source.")
    parser.add_argument("--output-root", required=True, help="Directory for monthly Markdown archives.")
    parser.add_argument("--start-url", help="Optional start URL for the jike-web adapter.")
    parser.add_argument("--max-scrolls", type=int, default=30, help="Scroll limit for the jike-web adapter.")
    parser.add_argument(
        "--scroll-pause-ms",
        type=int,
        default=1500,
        help="Delay between scrolls for the jike-web adapter.",
    )
    parser.add_argument("--headless", action="store_true", help="Run the jike-web adapter headlessly.")
    parser.add_argument(
        "--ignore-existing-cursor",
        action="store_true",
        help="Ignore state.json cursor and continue paging backwards for historical backfill.",
    )
    parser.add_argument(
        "--recent-seen-limit",
        type=int,
        default=50,
        help="How many recent IDs to keep in state.json.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_created_at(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone()


def load_source_items(args: argparse.Namespace) -> list[dict]:
    if args.source == "jike-web":
        return load_jike_web_items(args)
    if not args.input_json:
        raise ValueError("--input-json is required when --source json is used.")

    input_path = Path(args.input_json)
    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of Jike items.")
    return [normalize_item(item) for item in data]


def load_jike_web_items(args: argparse.Namespace) -> list[dict]:
    script_path = Path(__file__).with_name("jike_web_adapter.py")
    state_dir = Path(args.output_root) / ".jike-sync"
    state = load_state(state_dir / "state.json")
    with tempfile.NamedTemporaryFile(prefix="jike-capture-", suffix=".json", delete=False) as handle:
        dump_path = Path(handle.name)
    command = [
        sys.executable,
        str(script_path),
        "--state-dir",
        str(state_dir),
        "--dump-json",
        str(dump_path),
        "--max-scrolls",
        str(args.max_scrolls),
        "--scroll-pause-ms",
        str(args.scroll_pause_ms),
    ]
    if args.start_url:
        command.extend(["--start-url", args.start_url])
    if args.headless:
        command.append("--headless")
    if state.get("latest_seen_post_id") and not args.ignore_existing_cursor:
        command.extend(["--stop-post-id", state["latest_seen_post_id"]])

    try:
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"Jike web adapter failed with exit code {completed.returncode}")
        if not dump_path.exists():
            return []
        with dump_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("The jike-web adapter did not return a JSON array.")
        return [normalize_item(item) for item in data]
    finally:
        dump_path.unlink(missing_ok=True)


def normalize_item(item: dict) -> dict:
    if not item.get("id"):
        raise ValueError(f"Missing required field 'id' in item: {item}")
    if not item.get("created_at"):
        raise ValueError(f"Missing required field 'created_at' in item: {item}")

    normalized = {
        "id": str(item["id"]),
        "created_at": parse_created_at(item["created_at"]).isoformat(timespec="seconds"),
        "content": str(item.get("content") or item.get("text") or "").strip(),
        "source_url": item.get("source_url") or item.get("url") or "",
        "media_links": normalize_media_links(item.get("media_links") or item.get("media") or []),
        "topic": str(item.get("topic") or "").strip(),
        "raw_type": str(item.get("raw_type") or item.get("type") or "note").strip(),
    }
    return normalized


def normalize_media_links(value: list | tuple) -> list[str]:
    links: list[str] = []
    for entry in value:
        if isinstance(entry, str):
            link = entry.strip()
        elif isinstance(entry, dict):
            link = str(entry.get("url") or entry.get("src") or "").strip()
        else:
            link = ""
        if not link:
            continue
        if link.startswith("/topic/"):
            continue
        if "userProfile" in link:
            continue
        links.append(link)
    return links


def canonical_signature(item: dict) -> str:
    content = " ".join((item.get("content") or "").split())
    source_url = (item.get("source_url") or "").strip()
    topic = (item.get("topic") or "").strip()
    if source_url:
        return f"url::{source_url}"
    return f"content::{content}::topic::{topic}"


def fallback_signature(item: dict) -> str:
    content = " ".join((item.get("content") or "").split())
    topic = (item.get("topic") or "").strip()
    return f"content::{content}::topic::{topic}"


def choose_better_item(current: dict, candidate: dict) -> dict:
    if current is None:
        return candidate
    current_score = item_quality_score(current)
    candidate_score = item_quality_score(candidate)
    if candidate_score > current_score:
        return candidate
    if candidate_score < current_score:
        return current

    return candidate


def item_quality_score(item: dict) -> tuple[int, int, int]:
    source_url_score = 1 if item.get("source_url") else 0
    content_length = len((item.get("content") or "").strip())
    topic_score = 1 if item.get("topic") else 0
    return (source_url_score, content_length, topic_score)


def should_merge_items(current: dict, candidate: dict) -> bool:
    if fallback_signature(current) != fallback_signature(candidate):
        return False
    current_dt = parse_created_at(current["created_at"])
    candidate_dt = parse_created_at(candidate["created_at"])
    return abs((current_dt - candidate_dt).total_seconds()) <= 12 * 3600


def dedupe_items(items: list[dict]) -> list[dict]:
    by_signature: dict[str, dict] = {}
    for item in items:
        signature = canonical_signature(item)
        existing = by_signature.get(signature)
        if existing is None:
            merged = False
            for existing_signature, existing_item in list(by_signature.items()):
                if should_merge_items(existing_item, item):
                    by_signature[existing_signature] = choose_better_item(existing_item, item)
                    merged = True
                    break
            if not merged:
                by_signature[signature] = item
        else:
            by_signature[signature] = choose_better_item(existing, item)
    return list(by_signature.values())


def load_existing_items(items_path: Path) -> dict[str, dict]:
    if not items_path.exists():
        return {}

    items: dict[str, dict] = {}
    with items_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            items[item["id"]] = item
    deduped = dedupe_items(list(items.values()))
    return {item["id"]: item for item in deduped}


def save_items(items_path: Path, items_by_id: dict[str, dict]) -> None:
    with items_path.open("w", encoding="utf-8") as handle:
        for item_id in sorted(items_by_id, key=lambda value: (parse_created_at(items_by_id[value]["created_at"]), value)):
            handle.write(json.dumps(items_by_id[item_id], ensure_ascii=False) + "\n")


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {
            "last_successful_sync_at": None,
            "latest_seen_post_id": None,
            "latest_seen_created_at": None,
            "seen_ids_recent": [],
        }
    with state_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_state(
    state: dict,
    all_items: list[dict],
    changed_ids: list[str],
    recent_seen_limit: int,
) -> dict:
    if all_items:
        newest = max(all_items, key=lambda item: (parse_created_at(item["created_at"]), item["id"]))
        state["latest_seen_post_id"] = newest["id"]
        state["latest_seen_created_at"] = newest["created_at"]

    valid_ids = {item["id"] for item in all_items}
    previous_recent = [item_id for item_id in state.get("seen_ids_recent", []) if item_id in valid_ids]
    recent = list(dict.fromkeys((changed_ids + previous_recent)))
    state["seen_ids_recent"] = recent[:recent_seen_limit]
    state["last_successful_sync_at"] = now_iso()
    return state


def render_changed_months(state_dir: Path, output_root: Path, months: set[str], items_by_id: dict[str, dict]) -> None:
    generated_at = now_iso()
    for month in sorted(months):
        month_items = sorted(
            (item for item in items_by_id.values() if item["created_at"][:7] == month),
            key=lambda item: parse_created_at(item["created_at"]),
        )
        markdown = render_markdown(month, month_items, generated_at)
        output_path = output_root / f"{month}.md"
        output_path.write_text(markdown, encoding="utf-8")
        print(f"Rendered {output_path}")


def render_archive_index(output_root: Path, items_by_id: dict[str, dict]) -> None:
    output_path = output_root / "即刻归档索引.md"
    markdown = render_index_markdown(list(items_by_id.values()), now_iso())
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Rendered {output_path}")


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    state_dir = output_root / ".jike-sync"
    state_dir.mkdir(parents=True, exist_ok=True)
    items_path = state_dir / "items.jsonl"
    state_path = state_dir / "state.json"

    incoming_items = dedupe_items(load_source_items(args))
    items_by_id = load_existing_items(items_path)
    existing_by_signature = {canonical_signature(item): item_id for item_id, item in items_by_id.items()}
    touched_months: set[str] = set()
    changed_ids: list[str] = []

    for item in incoming_items:
        signature = canonical_signature(item)
        existing_id = existing_by_signature.get(signature, item["id"])
        existing = items_by_id.get(existing_id)
        if existing != item:
            if existing and existing_id != item["id"]:
                items_by_id.pop(existing_id, None)
            items_by_id[item["id"]] = choose_better_item(existing, item) if existing else item
            existing_by_signature[signature] = item["id"]
            touched_months.add(item["created_at"][:7])
            changed_ids.append(item["id"])

    save_items(items_path, items_by_id)
    state = load_state(state_path)
    updated_state = update_state(state, list(items_by_id.values()), changed_ids, args.recent_seen_limit)
    save_state(state_path, updated_state)

    if touched_months:
        render_changed_months(state_dir, output_root, touched_months, items_by_id)
    else:
        print("No content changes detected. State refreshed without rewriting month files.")

    render_archive_index(output_root, items_by_id)
    print(f"State updated at {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
