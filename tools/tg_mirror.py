#!/usr/bin/env python3
"""Build the site into OUT with posts mirrored from the Telegram channel.

Reads Telegram's public web preview, https://t.me/s/<channel>, so no bot,
token or login is needed. The source tree is never modified: the site is
copied into OUT and only the copy is filled in.

  - the <!-- tg-feed:start --> ... <!-- tg-feed:end --> block on ru/ and en/
    gets the latest posts as cards;
  - ru/blog/index.html is written from tools/blog-template.html with every post;
  - post photos are downloaded into assets/tg/ (Telegram's image URLs expire).

Usage:  python3 tools/tg_mirror.py [--out _site]
Needs:  beautifulsoup4
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

CHANNEL = "pro_lawyer"
# Set to a hashtag such as "#сайт" to mirror only the posts that carry it
# (the tag itself is removed from the mirrored text). None mirrors every post.
ONLY_TAG = None
HOME_CARDS = 3

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ["index.html", "en", "ru", "assets"]
UA = "Mozilla/5.0 (compatible; site-builder)"
MSK = timezone(timedelta(hours=3))
RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
             "августа", "сентября", "октября", "ноября", "декабря"]
EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"]
KEEP_TAGS = {"b", "strong", "i", "em", "u", "s", "del", "code", "pre", "blockquote", "br", "a"}


def fetch(url, binary=False):
    delays = [5, 15, 30]
    for attempt in range(len(delays) + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            return data if binary else data.decode("utf-8")
        except Exception:
            if attempt == len(delays):
                raise
            time.sleep(delays[attempt])


def clean_html(node):
    """Reduce Telegram's message markup to a small safe subset."""
    for e in node.select("i.emoji"):
        e.replace_with(e.get_text())
    for e in node.find_all("tg-spoiler"):
        e.name, e.attrs = "span", {"class": "spoiler", "tabindex": "0"}
    for e in node.find_all(True):
        if e.name == "span" and "spoiler" in (e.get("class") or []):
            continue
        if e.name not in KEEP_TAGS:
            e.unwrap()
        elif e.name == "a":
            href = e.get("href", "")
            if href.startswith(("http://", "https://")):
                e.attrs = {"href": href, "rel": "noopener", "target": "_blank"}
            else:  # hashtag search links and the like
                e.unwrap()
        else:
            e.attrs = {}
    return node.decode_contents().strip()


def to_plain(fragment):
    soup = BeautifulSoup(fragment, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    return soup.get_text().strip()


def parse_page(page):
    """Return (posts worth mirroring, every post id seen on the page)."""
    soup = BeautifulSoup(page, "html.parser")
    posts, ids = [], []
    for m in soup.select("div.tgme_widget_message[data-post]"):
        pid = int(m["data-post"].rsplit("/", 1)[-1])
        ids.append(pid)
        if "service_message" in m.get("class", []):
            continue

        text_el = next((el for el in m.select(".tgme_widget_message_text")
                        if not el.find_parent(class_="tgme_widget_message_reply")), None)
        body = clean_html(text_el) if text_el else ""
        if ONLY_TAG:
            if ONLY_TAG.lower() not in to_plain(body).lower():
                continue
            body = re.sub(re.escape(ONLY_TAG), "", body, flags=re.I).strip()
        plain = to_plain(body)
        # card excerpts must not give away spoilers
        teaser = to_plain(re.sub(r'<span class="spoiler".*?</span>', "…", body, flags=re.S))

        photos = []
        for a in m.select("a.tgme_widget_message_photo_wrap"):
            found = re.search(r"url\('([^']+)'\)", a.get("style", ""))
            if found:
                photos.append(found.group(1))
        if not plain and not photos:
            continue  # stickers, bare videos and other things a web page can't show

        link = None
        lp = m.select_one("a.tgme_widget_message_link_preview")
        if lp and lp.get("href", "").startswith(("http://", "https://")):
            title = lp.select_one(".link_preview_title") or lp.select_one(".link_preview_site_name")
            link = {"href": lp["href"],
                    "title": title.get_text(strip=True) if title else urlparse(lp["href"]).netloc}

        t = m.select_one(".tgme_widget_message_date time")
        fwd = m.select_one(".tgme_widget_message_forwarded_from_name")
        posts.append({
            "id": pid,
            "date": datetime.fromisoformat(t["datetime"]).astimezone(MSK) if t else None,
            "html": body,
            "plain": plain,
            "teaser": teaser,
            "photos": photos,
            "link": link,
            "forwarded": fwd.get_text(strip=True) if fwd else None,
            "media_in_tg": bool(m.select_one(
                ".tgme_widget_message_video_player, .tgme_widget_message_roundvideo_player, "
                ".tgme_widget_message_document_wrap, .tgme_widget_message_poll, "
                ".tgme_widget_message_voice_player, .message_media_not_supported")),
        })
    return posts, ids


def fetch_all():
    posts, before = {}, None
    for _ in range(200):
        url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
        page_posts, ids = parse_page(fetch(url))
        for p in page_posts:
            posts[p["id"]] = p
        if not ids or (before and min(ids) >= before) or min(ids) <= 1:
            break
        before = min(ids)
        time.sleep(1)
    return sorted(posts.values(), key=lambda p: p["id"], reverse=True)


def fmt_date(d, lang):
    if d is None:
        return ""
    months = RU_MONTHS if lang == "ru" else EN_MONTHS
    return f"{d.day} {months[d.month - 1]} {d.year}"


def split_title(p):
    """Use the first line as a heading when it is short and more text follows."""
    first, _, rest = p["plain"].partition("\n")
    if rest.strip() and len(first.strip()) <= 100:
        head_html, _, body_html = p["html"].partition("<br/>")
        body_html = re.sub(r"^(\s*<br/>)+", "", body_html).strip()
        return first.strip(), rest.strip(), body_html
    return None, p["plain"], p["html"]


def excerpt(text, limit=200):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—–- ") + "…"


def download_photos(posts, out):
    folder = out / "assets" / "tg"
    folder.mkdir(parents=True, exist_ok=True)
    for p in posts:
        p["images"] = []
        for n, url in enumerate(p["photos"], 1):
            name = f"{p['id']}-{n}.jpg"
            try:
                (folder / name).write_bytes(fetch(url, binary=True))
                p["images"].append(name)
            except Exception as exc:
                print(f"warning: photo {name} skipped: {exc}", file=sys.stderr)


def feed_block(posts, lang):
    ru = lang == "ru"
    post_href = "blog/" if ru else "../ru/blog/"
    cards = []
    for p in posts[:HOME_CARDS]:
        title, rest, _ = split_title({**p, "plain": p["teaser"]})
        img =(f'<img src="../assets/tg/{p["images"][0]}" alt="" loading="lazy">'
               if p["images"] else "")
        cards.append(
            f'        <a class="feed-card reveal" href="{post_href}#post-{p["id"]}">\n'
            f'          {img}\n'
            f'          <div class="feed-card-body">\n'
            f'            <span class="feed-date">{fmt_date(p["date"], lang)}</span>\n'
            + (f'            <h3>{html.escape(title)}</h3>\n' if title else "")
            + f'            <p>{html.escape(excerpt(rest, 160 if title else 220))}</p>\n'
            f'            <span class="feed-more">{"Читать" if ru else "Read (in Russian)"} →</span>\n'
            f'          </div>\n'
            f'        </a>')
    all_label = "Все публикации" if ru else "All posts (in Russian)"
    sub_label = "Подписаться на канал" if ru else "Follow on Telegram"
    return ('      <div class="feed-cards">\n' + "\n".join(cards) + "\n      </div>\n"
            '      <div class="feed-actions reveal">\n'
            f'        <a class="btn btn-solid" href="{post_href}">{all_label}</a>\n'
            f'        <a class="btn btn-outline" href="https://t.me/{CHANNEL}" target="_blank" rel="noopener">{sub_label}</a>\n'
            '      </div>')


def post_article(p):
    title, _, body = split_title(p)
    parts = [f'      <article class="post" id="post-{p["id"]}">',
             f'        <a class="post-date" href="#post-{p["id"]}">{fmt_date(p["date"], "ru")}</a>']
    if title:
        parts.append(f"        <h2>{html.escape(title)}</h2>")
    if p["forwarded"]:
        parts.append(f'        <p class="post-note">Переслано из «{html.escape(p["forwarded"])}»</p>')
    if p["images"]:
        imgs = "".join(f'<img src="../../assets/tg/{n}" alt="" loading="lazy">' for n in p["images"])
        parts.append(f'        <div class="post-media">{imgs}</div>')
    if body:
        parts.append(f'        <div class="post-text">{body}</div>')
    if p["link"]:
        parts.append(f'        <a class="post-link" href="{html.escape(p["link"]["href"])}" rel="noopener" '
                     f'target="_blank"><span>Ссылка</span>{html.escape(p["link"]["title"])}</a>')
    if p["media_in_tg"]:
        parts.append('        <p class="post-note">В публикации есть видео или файл — они доступны в Telegram.</p>')
    parts.append(f'        <p class="post-foot"><a href="https://t.me/{CHANNEL}/{p["id"]}" target="_blank" rel="noopener">Открыть в Telegram</a></p>')
    parts.append("      </article>")
    return "\n".join(parts)


def fill_feed(path, block):
    text = path.read_text(encoding="utf-8")
    text, n = re.subn(r"(<!-- tg-feed:start.*?-->).*?(<!-- tg-feed:end -->)",
                      lambda m: m.group(1) + "\n" + block + "\n      " + m.group(2),
                      text, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"tg-feed markers not found in {path}")
    path.write_text(text, encoding="utf-8")


def save_cache(posts, out, cache):
    """Keep the last good fetch so a Telegram outage doesn't block deploys."""
    if cache.exists():
        shutil.rmtree(cache)
    shutil.copytree(out / "assets" / "tg", cache / "tg")
    keep = ("id", "html", "plain", "teaser", "images", "link", "forwarded", "media_in_tg")
    rows = [{**{k: p[k] for k in keep}, "date": p["date"].isoformat() if p["date"] else None}
            for p in posts]
    (cache / "posts.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def load_cache(out, cache):
    shutil.copytree(cache / "tg", out / "assets" / "tg", dirs_exist_ok=True)
    rows = json.loads((cache / "posts.json").read_text(encoding="utf-8"))
    for p in rows:
        p["date"] = datetime.fromisoformat(p["date"]) if p["date"] else None
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="_site", help="output folder, relative to the site root")
    ap.add_argument("--cache", help="folder for the last good fetch, used if Telegram is unreachable")
    args = ap.parse_args()
    out = (ROOT / args.out).resolve()
    cache = (ROOT / args.cache).resolve() if args.cache else None
    if out == ROOT or ROOT.is_relative_to(out):
        sys.exit("--out must be a subfolder of the site, not the site itself")

    try:
        posts = fetch_all()
        if not posts:
            raise RuntimeError("no posts parsed: the channel is empty or Telegram changed its page layout")
    except Exception as exc:
        if not (cache and (cache / "posts.json").exists()):
            raise
        posts = None
        # "::warning::" shows up as an annotation on the GitHub Actions run page
        print(f"::warning::Telegram fetch failed ({exc}); built with the cached posts")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for item in PUBLISHED:
        src = ROOT / item
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, out / item)

    if posts is None:
        posts = load_cache(out, cache)
    else:
        download_photos(posts, out)
        if cache:
            save_cache(posts, out, cache)
    for lang in ("ru", "en"):
        fill_feed(out / lang / "index.html", feed_block(posts, lang))
    blog = (ROOT / "tools" / "blog-template.html").read_text(encoding="utf-8")
    blog = blog.replace("<!-- posts -->", "\n".join(post_article(p) for p in posts))
    (out / "ru" / "blog").mkdir(parents=True, exist_ok=True)
    (out / "ru" / "blog" / "index.html").write_text(blog, encoding="utf-8")

    stamp_assets(out)
    print(f"{len(posts)} posts from @{CHANNEL} -> {out}")


def stamp_assets(out):
    """Append a content hash to the CSS/JS URLs in every page.

    GitHub Pages lets browsers cache files for 10 minutes, so a new page could
    otherwise load next to the old stylesheet."""
    stamps = {}
    for rel in ("assets/css/style.css", "assets/js/main.js"):
        digest = hashlib.sha1((out / rel).read_bytes()).hexdigest()[:10]
        stamps[rel] = f"{rel}?v={digest}"
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for rel, stamped in stamps.items():
            text = text.replace(f'{rel}"', f'{stamped}"')
        page.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
