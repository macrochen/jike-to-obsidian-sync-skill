#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - handled at runtime
    async_playwright = None
    PlaywrightTimeoutError = Exception


DEFAULT_START_URL = "https://web.okjike.com"
DEFAULT_PROFILE_DIRNAME = "browser-profile"


@dataclass
class CaptureConfig:
    start_url: str
    profile_dir: Path
    max_scrolls: int
    scroll_pause_ms: int
    stop_post_id: str | None
    headless: bool


def build_post_url(post_id: str) -> str:
    return f"https://m.okjike.com/originalPosts/{post_id}"


EXTRACTION_SCRIPT = r"""
() => {
  const uniq = (values) => Array.from(new Set(values.filter(Boolean)));
  const TIME_PATTERN = /刚刚|今天|昨天|\d+\s*分钟前|\d+\s*小时前|\d+\s*天前|\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{2})?|\d{4}-\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{2})?/;
  const textOf = (element, selectors) => {
    for (const selector of selectors) {
      const node = element.querySelector(selector);
      const text = node?.innerText?.trim();
      if (text) return text;
    }
    return "";
  };

  const attrOf = (element, selectors, attributeName) => {
    for (const selector of selectors) {
      const node = element.querySelector(selector);
      const value = node?.getAttribute?.(attributeName)?.trim();
      if (value) return value;
    }
    return "";
  };

  const allAttr = (element, selectors, attributeName) => {
    const values = [];
    for (const selector of selectors) {
      for (const node of element.querySelectorAll(selector)) {
        const value = node?.getAttribute?.(attributeName)?.trim();
        if (value) values.push(value);
      }
    }
    return Array.from(new Set(values));
  };

  const isoFromTime = (value) => {
    if (!value) return "";
    const ts = Date.parse(value);
    if (Number.isNaN(ts)) return value;
    return new Date(ts).toISOString();
  };

  const findContainer = (node) => {
    let current = node;
    for (let i = 0; current && i < 8; i += 1) {
      const text = current.innerText?.trim() || "";
      const linkCount = current.querySelectorAll?.("a[href]").length || 0;
      if (text.length >= 10 && linkCount >= 1) return current;
      current = current.parentElement;
    }
    return node;
  };

  const isLikelyPost = (element) => {
    if (!element) return false;
    const text = element.innerText?.trim() || "";
    if (text.length < 20) return false;
    const hasContentWrapper = !!element.querySelector("[class*='contentWrapper']");
    const hasActions = !!element.querySelector("[class*='actions']");
    const timeText =
      textOf(element, ["time", "[class*='descContainer']", "[class*='desc']"]) || "";
    const hasTime = TIME_PATTERN.test(timeText);
    return hasContentWrapper && hasActions && hasTime;
  };

  const candidates = [];

  const directSelectors = [
    "article",
    "[data-testid='feed-item']",
    "[class*='feed-item']",
    "[class*='post-item']",
    "[class*='note-item']",
    "[class*='itemWrap']",
    "[class*='contentItem']"
  ];

  for (const selector of directSelectors) {
    for (const element of document.querySelectorAll(selector)) {
      if (isLikelyPost(element)) candidates.push(element);
    }
  }

  for (const header of document.querySelectorAll("header")) {
    const parent = header.parentElement;
    if (!parent) continue;
    if (isLikelyPost(parent)) candidates.push(parent);
  }

  for (const wrapper of document.querySelectorAll("[class*='contentWrapper']")) {
    const parent = wrapper.parentElement;
    if (!parent) continue;
    if (isLikelyPost(parent)) candidates.push(parent);
  }

  for (const link of document.querySelectorAll("a[href*='originalPosts'], a[href*='/posts/']")) {
    const container = findContainer(link);
    if (isLikelyPost(container)) candidates.push(container);
  }

  for (const timeNode of document.querySelectorAll("time, [datetime]")) {
    const container = findContainer(timeNode);
    if (isLikelyPost(container)) candidates.push(container);
  }

  const articles = uniq(candidates);

  return articles.map((element, index) => {
    const sourceUrl = attrOf(
      element,
      ["a[href*='originalPosts']", "a[href*='/posts/']", "a[href*='okjike.com' ]"],
      "href"
    );
    const candidateId =
      element.getAttribute("data-id") ||
      element.getAttribute("data-note-id") ||
      element.getAttribute("data-post-id") ||
      (sourceUrl ? sourceUrl.split("/").filter(Boolean).slice(-1)[0] : "") ||
      "";

    const createdAt =
      attrOf(element, ["time"], "datetime") ||
      attrOf(element, ["[datetime]"], "datetime") ||
      textOf(element, ["time", "[class*='descContainer']", "[class*='desc']"]);

    const content = textOf(element, [
      "[data-testid='post-content']",
      "[class*='contentWrapper'] [class*='content']",
      "[class*='contentCollapsed']",
      "[class*='contentEllipsis']",
      "[class*='content']",
      "[class*='text']",
      "main",
      "article"
    ]);

    const topic = textOf(element, ["[class*='topic']", "a[href*='/topic/']"]);
    const rawType = textOf(element, ["[class*='type']", "[class*='tag']"]) || "note";

    const mediaRoot = element.querySelector("[class*='contentWrapper']") || element;
    return {
      id: candidateId,
      created_at: isoFromTime(createdAt),
      content,
      source_url: sourceUrl,
      media_links: uniq(allAttr(
        mediaRoot,
        [
          "img[data-mode='grid-item'][src]",
          "img[alt='图片'][src]",
          "[class*='picture'][src]",
          "video[src]",
          "source[src]",
          "a[href$='.jpg']",
          "a[href$='.png']",
          "a[href$='.mp4']"
        ],
        "src"
      ).concat(
        allAttr(
          mediaRoot,
          ["a[href*='image']", "a[href*='video']", "a[href$='.jpg']", "a[href$='.png']", "a[href$='.mp4']"],
          "href"
        )
      )),
      topic,
      raw_type: rawType
    };
  }).filter((item) => item.created_at || item.source_url || item.content);
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Jike posts from the web UI.")
    parser.add_argument("--state-dir", required=True, help="Sync state directory used by the main skill.")
    parser.add_argument("--start-url", default=DEFAULT_START_URL, help="Jike page to open before capture.")
    parser.add_argument("--max-scrolls", type=int, default=30)
    parser.add_argument("--scroll-pause-ms", type=int, default=1500)
    parser.add_argument("--stop-post-id", help="Stop once this post id is encountered.")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--dump-json", help="Optional path to write captured items as JSON.")
    return parser.parse_args()


def ensure_playwright_installed() -> None:
    if async_playwright is None:
        raise RuntimeError(
            "Playwright is not installed in this skill's .venv. Install it with "
            "'./.venv/bin/pip install playwright' and then run "
            "'./.venv/bin/playwright install chromium'."
        )


def normalize_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    return url


def normalize_captured_item(raw_item: dict) -> dict | None:
    raw_created_at = str(raw_item.get("created_at") or "").strip()
    created_at = normalize_created_at(raw_created_at)
    content = str(raw_item.get("content") or "").strip()
    source_url = normalize_url(str(raw_item.get("source_url") or "").strip())
    item_id = str(raw_item.get("id") or "").strip()
    if not item_id:
        item_id = build_fallback_id(created_at, content, source_url)

    if not item_id or not created_at:
        return None

    media_links = []
    for entry in raw_item.get("media_links") or []:
        value = normalize_url(str(entry).strip())
        if not value:
            continue
        if value.startswith("/topic/"):
            continue
        if "userProfile" in value:
            continue
        if value not in media_links:
            media_links.append(value)

    return {
        "id": item_id,
        "created_at": created_at,
        "content": content,
        "source_url": source_url,
        "media_links": media_links,
        "topic": str(raw_item.get("topic") or "").strip(),
        "raw_type": str(raw_item.get("raw_type") or "note").strip(),
    }


def build_fallback_id(created_at: str, content: str, source_url: str) -> str:
    base = "\n".join([created_at, content.strip(), source_url.strip()])
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"synthetic-{digest}"


def normalize_created_at(value: str) -> str:
    value = value.strip()
    if not value:
        return ""

    try:
        return datetime.fromisoformat(value).astimezone().isoformat(timespec="seconds")
    except ValueError:
        pass

    now = datetime.now().astimezone()
    relative_patterns = [
        (r"^(\d+)\s*分钟前$", lambda m: now - timedelta(minutes=int(m.group(1)))),
        (r"^(\d+)\s*小时前$", lambda m: now - timedelta(hours=int(m.group(1)))),
        (r"^(\d+)\s*天前$", lambda m: now - timedelta(days=int(m.group(1)))),
    ]
    for pattern, resolver in relative_patterns:
        match = re.match(pattern, value)
        if match:
            return resolver(match).isoformat(timespec="seconds")

    if value == "刚刚":
        return now.isoformat(timespec="seconds")
    if value == "昨天":
        return (now - timedelta(days=1)).isoformat(timespec="seconds")
    if value == "今天":
        return now.isoformat(timespec="seconds")

    absolute_patterns = [
        ("%Y-%m-%d %H:%M", value),
        ("%Y-%m-%d", value),
        ("%m-%d %H:%M", f"{now.year}-{value}"),
        ("%m-%d", f"{now.year}-{value}"),
    ]
    for pattern, candidate in absolute_patterns:
        try:
            parsed = datetime.strptime(candidate, pattern)
            return parsed.replace(tzinfo=now.tzinfo).isoformat(timespec="seconds")
        except ValueError:
            continue

    return ""


async def wait_for_login(page) -> None:
    selectors = [
        "article",
        "[data-testid='feed-item']",
        "[class*='feed-item']",
        "[class*='post-item']",
        "[class*='note-item']",
        "a[href*='originalPosts']",
        "time",
    ]
    try:
        await page.wait_for_selector(",".join(selectors), timeout=20_000)
    except PlaywrightTimeoutError:
        title = await page.title()
        body_text = await page.evaluate("document.body.innerText.slice(0, 1000)")
        print("Jike feed was not detected yet. Please log in and navigate to your own profile or notes page.")
        print(f"Page title: {title}")
        print(body_text)
        await page.wait_for_timeout(5000)


def normalize_api_item(item: dict) -> dict | None:
    post_id = str(item.get("id") or "").strip()
    created_at = str(item.get("actionTime") or item.get("createdAt") or "").strip()
    content = str(item.get("content") or "").strip()
    if not post_id or not created_at:
        return None

    media_links: list[str] = []
    for picture in item.get("pictures") or []:
        if not isinstance(picture, dict):
            continue
        for key in ("picUrl", "middlePicUrl", "smallPicUrl", "thumbnailUrl"):
            value = normalize_url(str(picture.get(key) or "").strip())
            if value:
                media_links.append(value)
                break

    topic = ""
    if isinstance(item.get("topic"), dict):
        topic = str(item["topic"].get("content") or "").strip()

    return {
        "id": post_id,
        "created_at": created_at,
        "content": content,
        "source_url": build_post_url(post_id),
        "media_links": media_links,
        "topic": topic,
        "raw_type": str(item.get("type") or "ORIGINAL_POST").strip().lower(),
    }


async def capture_items_via_dom(browser, config: CaptureConfig) -> list[dict]:
    page = browser.pages[0] if browser.pages else await browser.new_page()
    print(f"Opening {config.start_url}")
    await page.goto(config.start_url, wait_until="domcontentloaded")
    await wait_for_login(page)

    seen_ids: set[str] = set()
    captured: list[dict] = []
    stop_found = False

    for scroll_index in range(config.max_scrolls):
        raw_items = await page.evaluate(EXTRACTION_SCRIPT)
        page_added = 0
        for raw_item in raw_items:
            item = normalize_captured_item(raw_item)
            if not item or item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])
            captured.append(item)
            page_added += 1
            if config.stop_post_id and item["id"] == config.stop_post_id:
                stop_found = True
        print(
            f"Scroll {scroll_index + 1}/{config.max_scrolls}: "
            f"captured {len(captured)} unique items (+{page_added})"
        )
        if stop_found:
            print(f"Reached existing sync cursor: {config.stop_post_id}")
            break

        previous_height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(config.scroll_pause_ms)
        current_height = await page.evaluate("document.body.scrollHeight")
        if current_height == previous_height and page_added == 0:
            print("No additional content detected. Stopping scroll.")
            break

    return captured


async def capture_items_via_api(browser, config: CaptureConfig) -> list[dict]:
    page = browser.pages[0] if browser.pages else await browser.new_page()
    first_page_response: dict | None = None
    access_token: str | None = None

    async def handle_response(response) -> None:
        nonlocal first_page_response, access_token
        if first_page_response is not None:
            return
        if "api.ruguoapp.com/1.0/personalUpdate/single" not in response.url:
            return
        access_token = (await response.request.all_headers()).get("x-jike-access-token")
        first_page_response = await response.json()

    page.on("response", handle_response)
    print(f"Opening {config.start_url}")
    await page.goto(config.start_url, wait_until="domcontentloaded")
    await wait_for_login(page)
    await page.wait_for_timeout(2000)

    if not first_page_response or not access_token:
        raise RuntimeError("Could not capture authenticated Jike API bootstrap response.")

    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/plain, */*",
        "origin": "https://web.okjike.com",
        "referer": "https://web.okjike.com/",
        "x-jike-access-token": access_token,
    }

    captured: list[dict] = []
    seen_ids: set[str] = set()
    current_page = first_page_response

    for page_index in range(config.max_scrolls):
        page_items = current_page.get("data") or []
        added = 0
        stop_found = False
        for raw_item in page_items:
            item = normalize_api_item(raw_item)
            if not item or item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])
            captured.append(item)
            added += 1
            if config.stop_post_id and item["id"] == config.stop_post_id:
                stop_found = True
        print(
            f"Page {page_index + 1}/{config.max_scrolls}: "
            f"captured {len(captured)} unique items (+{added})"
        )
        if stop_found:
            print(f"Reached existing sync cursor: {config.stop_post_id}")
            break

        load_more_key = current_page.get("loadMoreKey")
        if not load_more_key:
            print("No loadMoreKey returned. Stopping pagination.")
            break

        response = await browser.request.post(
            "https://api.ruguoapp.com/1.0/personalUpdate/single",
            data={
                "limit": 20,
                "username": config.start_url.rstrip("/").split("/")[-1],
                "loadMoreKey": load_more_key,
            },
            headers=headers,
        )
        if response.status != 200:
            raise RuntimeError(f"Jike API pagination failed with status {response.status}")
        current_page = await response.json()

    return captured


async def capture_items(config: CaptureConfig) -> list[dict]:
    ensure_playwright_installed()
    assert async_playwright is not None

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.profile_dir),
            headless=config.headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 1200},
        )
        try:
            try:
                return await capture_items_via_api(browser, config)
            except Exception as exc:
                print(f"API capture failed, falling back to DOM parsing: {exc}")
                return await capture_items_via_dom(browser, config)
        finally:
            await browser.close()


async def async_main(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir)
    profile_dir = state_dir / DEFAULT_PROFILE_DIRNAME
    profile_dir.mkdir(parents=True, exist_ok=True)

    config = CaptureConfig(
        start_url=args.start_url,
        profile_dir=profile_dir,
        max_scrolls=args.max_scrolls,
        scroll_pause_ms=args.scroll_pause_ms,
        stop_post_id=args.stop_post_id,
        headless=args.headless,
    )
    items = await capture_items(config)
    if args.dump_json:
        Path(args.dump_json).write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(items, ensure_ascii=False))
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
