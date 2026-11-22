# lawyer-site

Multilingual static website for **Ekaterina Aleksandrovna Nikolaenko** — Moscow attorney (Moscow City Bar, practicing since 2001; civil cases mainly, criminal too). A refresh of her existing site pro-lawyer.ru: civil cases for clients in **Moscow and the Moscow Region** (housing, inheritance, family disputes, court representation). An earlier plan to target Russians living abroad was dropped on 2026-11-20 at her request: payments from abroad are complicated, and foreign money carries legal risk for her. Don't reintroduce remote or cross-border wording. Design is restrained and premium: deep navy / muted gold, Cormorant Garamond + Inter.

Built 2026-07-05. No backend — plain HTML/CSS/JS on GitHub Pages. One build step: `tools/tg_mirror.py` copies the site into `_site/` and fills it with posts from her Telegram channel.

## Structure

```
index.html          # root: always forwards to /ru/ (Russian is the default; EN via the switcher)
en/index.html       # English one-pager
ru/index.html       # Russian one-pager
assets/css/style.css
assets/js/main.js   # header scroll state, mobile menu, reveal-on-scroll, footer year
assets/img/favicon.svg, portrait.jpg
tools/tg_mirror.py            # build: site → _site/ + Telegram posts; adds ?v=<hash> to CSS/JS URLs (Pages caches them 10 min)
tools/blog-template.html      # page shell for _site/ru/blog/ (all posts)
.github/workflows/pages.yml   # daily build + deploy to GitHub Pages (and on every push)
```

Both pages share identical structure and anchors (`#about #services #process #results #channel #contact`) — keep them in sync when editing. `_site/` is build output (git-ignored); never edit it.

## Telegram mirror

Her channel [@pro_lawyer](https://t.me/pro_lawyer) is mirrored onto the site (added 2026-11-20, her request). @advokat_nikolaenko is her personal account, used for the contact button.

- Source: Telegram's public preview `https://t.me/s/pro_lawyer` (no bot, token or login). Pages back through the full history with `?before=<id>`.
- Output: the latest 3 posts as cards in `#channel` on `ru/` and `en/` (between the `tg-feed` markers; without a build the section just links to the channel), and every post in full at `ru/blog/`. Photos are downloaded into `assets/tg/` because Telegram's image URLs expire.
- Skipped: service messages, polls, and posts with no text or photo. Videos and files stay in Telegram with a note on the post.
- `ONLY_TAG` in the script: set it to e.g. `"#сайт"` to mirror only tagged posts, if she'd rather choose what reaches the site.
- Refresh: the workflow rebuilds daily at 06:17 Moscow time (`cron: 17 3 * * *`) and on every push, so a new post appears by the next morning. To pull posts in sooner, run it by hand: Actions → Build and deploy → Run workflow. The workflow keeps the last good fetch in the Actions cache (`.tg-cache/`, `--cache`). If Telegram is unreachable, the build uses those posts and shows a warning on the run page, so site edits still deploy. A fresh repo has no cache, so its first build needs Telegram to answer. Its keep-alive step re-enables the workflow so GitHub's 60-day inactivity pause doesn't stop the schedule.
- If posts stop appearing: run the script locally. "no posts parsed" means Telegram changed its page markup and `parse_page()` needs updating.

## Local preview

```bash
cd ~/Desktop/Projects/Shelf/lawyer-site && python3 tools/tg_mirror.py && python3 -m http.server 8080 -d _site
# → http://localhost:8080   (needs: pip install beautifulsoup4)
```

Opening the source files via file:// also works, without the Telegram posts.

## Deploy (GitHub Pages)

1. Create a repo (public for free Pages), push this folder's contents to `main`.
2. Repo → Settings → Pages → Source: **GitHub Actions** (not "Deploy from a branch": the workflow builds `_site/` and deploys it).
3. Site appears at `https://<user>.github.io/<repo>/`.

Custom domain (no `CNAME` file needed: Actions deploys ignore it):
1. Repo → Settings → Pages → Custom domain: `example.com`.
2. DNS at the registrar: `A @` → `185.199.108.153`, `.109.153`, `.110.153`, `.111.153`; `AAAA @` → `2606:50c0:8000::153`, `8001`, `8002`, `8003`; `CNAME www` → `legard525.github.io`.
3. Account Settings → Pages → verify the domain (TXT record), so nobody else can point it at their Pages site.
4. Once the certificate is issued, tick **Enforce HTTPS**. Then fill the hreflang TODOs on both pages with the real domain.
5. If the registrar is Cloudflare, keep the records DNS-only (grey cloud): Russian ISPs have throttled Cloudflare-proxied sites.

## Content status / TODO (waiting on Ekaterina & Alex)

- [x] **Portrait photo** → `assets/img/portrait.jpg` (1057×1280, added 2026-11-19; CSS crops it to 3:4)
- [x] **Win-rate figure** — dropped: she says publishing it is not allowed (2026-11-20). Placeholder removed from both pages
- [x] **Case results** — she approved the three drafted from pro-lawyer.ru case notes as they are (2026-11-20). **No testimonials**: KPEA art. 17 bars reviews by others about an advokat's work
- [x] **Telegram** — @advokat_nikolaenko, button in both contact sections (2026-11-19)
- [ ] **Confirm contact channels** — currently the public ones from pro-lawyer.ru: `+7 916-819-51-03` (also WhatsApp), `pro-lawyer@mail.ru`. Recommend a domain e-mail once a domain exists (a mail.ru address undercuts the premium positioning)
- [x] **Regions** — Moscow plus some cases in Moscow Oblast; step 03 updated (2026-11-19)
- [x] **Consultation languages** — Russian and English only; stat, About list, process step, contact text and meta updated (2026-11-19)
- [x] **Telegram channel mirror** — see the section above (2026-11-20)
- [ ] **Domain** — advokat-nikolaenko.ru, registered 2026-11-22 at REG.RU in her account (paid to 2027-11-22). Hosting: GitHub Pages. Canonical/hreflang/og tags, `sitemap.xml` and `robots.txt` already use it. Left: A/AAAA/CNAME records at REG.RU, then the repo's Pages custom domain + Enforce HTTPS (set the custom domain only after DNS resolves, or github.io starts redirecting to a dead domain)
- [x] **DE / FR versions** — dropped with the 2026-11-20 repositioning (local clients; she consults in RU + EN). If ever revived: copy `en/` → `de/`, `fr/`, translate, extend the `.lang` switcher in all headers and the root redirect

## Adding a language

Copy `en/index.html` → `<lang>/index.html`, translate, set `<html lang>`, `og:locale`, and the `.lang` switcher (all pages + footer links), and extend the root `index.html` redirect logic.

## Facts source

Credentials/practice details taken from pro-lawyer.ru (fetched 2026-07-05): Moscow City Bar member since 2002, RUDN law degrees (BA with distinction 2001, MA 2003), office Strastnoy Blvd 6/2, practice areas housing/inheritance/family + consumer/labor/debt. The site said "20+" years; the pages use 25, consistent with practicing since 2001.

Refreshed 2026-11-20 from the live pro-lawyer.ru: practice-area lists, the case-handling steps, her 2007 «Домашний адвокат» publication, the quote «Обратитесь вовремя, буду рада быть полезной», and the office address (Страстной бульвар, 6, стр. 2; earlier pages wrongly said 6/2).
