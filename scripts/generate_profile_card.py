#!/usr/bin/env python3
"""Generate a starry-sky SVG profile card for Mariajtik.

Usage:
  GITHUB_TOKEN=... python scripts/generate_profile_card.py
  PROFILE_MOCK=1 python scripts/generate_profile_card.py      # offline preview

Avatar: put an image named ``avatar`` (.png/.jpg/.jpeg/.webp) in the repo root, or
set PROFILE_IMAGE_FILE. With Pillow installed it is cropped to a square and
shrunk to 256 px so the SVG stays light. Output: assets/profile-card.svg
Texts below can be overridden with PROFILE_NAME, PROFILE_ROLE, PROFILE_TAGS, PROFILE_LINE.
"""
from __future__ import annotations

import base64
import datetime as dt
import html
import io
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGIN = os.environ.get("GITHUB_USER", "Mariajtik")
OUTPUT = Path(os.environ.get("PROFILE_OUTPUT", str(ROOT / "assets" / "profile-card.svg")))
NAME = os.environ.get("PROFILE_NAME", "Maria Baptista")
ROLE = os.environ.get("PROFILE_ROLE", "Full Stack Engineer · Aspiring Game Developer")
TAGS = os.environ.get("PROFILE_TAGS", "Resilient systems · Open source · AI engineering")
LINE = os.environ.get("PROFILE_LINE", "Exploring gameplay, systems design & interactive experiences")

NAVY, NAVY2 = "#0B1426", "#16263B"
MINT, CORAL, GOLD = "#9FD3B0", "#FF6B5E", "#FFD66B"
TEXT, MUTED = "#F2F0E6", "#AFC2D4"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
FALLBACK_COLORS = [MINT, GOLD, CORAL, "#8FB8E8", "#C9A7E8"]

PROFILE_Q = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
REPOS_Q = """
query($login: String!, $after: String) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
  }
}
"""


def graphql(token: str, query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "User-Agent": "maria-profile-card-generator"}
    last: Exception | None = None
    for attempt in range(3):  # retry on transient network errors
        try:
            req = urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("errors"):
                raise RuntimeError(payload["errors"][0].get("message", "GitHub GraphQL request failed"))
            return payload["data"]
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not reach GitHub API: {last}")


def streaks(days: list[tuple[str, int]]) -> tuple[int, int]:
    days = sorted(days)
    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    i, current = len(days) - 1, 0
    if i >= 0 and days[i][1] == 0:  # today may not have contributions yet
        i -= 1
    while i >= 0 and days[i][1] > 0:
        current += 1
        i -= 1
    return current, longest


def fetch_stats(token: str, login: str) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    data = graphql(token, PROFILE_Q, {"login": login, "from": (now - dt.timedelta(days=365)).isoformat(),
                                      "to": now.isoformat()})
    user = data.get("user")
    if user is None:
        raise RuntimeError(f"GitHub user {login!r} was not found")
    cc = user["contributionsCollection"]
    days = [(d["date"], d["contributionCount"]) for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)

    stars, repos_count, langs, after = 0, 0, {}, None
    while True:
        repos = graphql(token, REPOS_Q, {"login": login, "after": after})["user"]["repositories"]
        repos_count = repos["totalCount"]
        for repo in repos["nodes"]:
            stars += int(repo["stargazerCount"] or 0)
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                size, color = langs.get(name, (0, edge["node"]["color"]))
                langs[name] = (size + edge["size"], color or color)
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]

    return {"created_at": user["createdAt"], "followers": user["followers"]["totalCount"], "repos": repos_count,
            "stars": stars, "commits": cc["totalCommitContributions"], "pull_requests": cc["totalPullRequestContributions"],
            "reviews_issues": cc["totalIssueContributions"] + cc["totalPullRequestReviewContributions"],
            "contributions": cc["contributionCalendar"]["totalContributions"],
            "streak": current, "longest": longest, "languages": langs}


def mock_stats() -> dict:
    return {"created_at": "2024-03-10T00:00:00Z", "followers": 67, "repos": 12, "stars": 3, "commits": 412,
            "pull_requests": 18, "reviews_issues": 25, "contributions": 463, "streak": 6, "longest": 21,
            "languages": {"Python": (52000, "#3572A5"), "TypeScript": (31000, "#3178c6"),
                          "JavaScript": (14000, "#f1e05a"), "C#": (9000, "#178600"), "HTML": (4000, None)}}


def find_avatar() -> tuple[str, str] | None:
    configured = os.environ.get("PROFILE_IMAGE_FILE")
    candidates = [Path(configured)] if configured else [ROOT / f"avatar{e}" for e in (".png", ".jpg", ".jpeg", ".webp")] + [ROOT / "avatar"]
    for path in candidates:
        if not path.is_file():
            continue
        data, mime = path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/png"
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGB")
            side = min(im.size)
            left, top = (im.width - side) // 2, (im.height - side) // 2
            im = im.crop((left, top, left + side, top + side)).resize((256, 256), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=86, optimize=True)
            data, mime = buf.getvalue(), "image/jpeg"
        except ImportError:
            if len(data) > 300_000:
                print("Warning: avatar is large; install Pillow (pip install pillow) to shrink it.", file=sys.stderr)
        except Exception as exc:  # corrupted image: keep the original bytes
            print(f"Warning: could not process avatar ({exc}).", file=sys.stderr)
        return mime, base64.b64encode(data).decode("ascii")
    return None


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def duration(created_at: str) -> str:
    try:
        created = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        days = max(0, (dt.datetime.now(dt.timezone.utc) - created).days)
        years, days = divmod(days, 365)
        months, days = divmod(days, 30)
        return " ".join(p for p in (f"{years}y" if years else "", f"{months}mo" if months else "", f"{days}d" if not years else "") if p)
    except (TypeError, ValueError):
        return "—"


def sky(width: int, height: int) -> str:
    rnd = random.Random(LOGIN)  # same stars every run: no flicker in git diffs
    out = []
    for _ in range(85):
        x, y = rnd.uniform(8, width - 8), rnd.uniform(8, height * 0.78)
        if 255 < x < 940 and 60 < y < 385:  # keep the text area clean
            continue
        r = rnd.choice([.6, .8, 1, 1.2, 1.5])
        o = rnd.uniform(.35, .9)
        cls = f' class="tw" style="animation-delay:{rnd.uniform(0, 5):.1f}s;animation-duration:{rnd.uniform(2.5, 5):.1f}s"' if rnd.random() < .4 else ""
        out.append(f'<circle{cls} cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFF4D6" opacity="{o:.2f}"/>')
    return "".join(out)


def lang_bar(langs: dict, x0: int, y: int, total_w: int) -> str:
    if not langs:
        return ""
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]
    total = sum(v[0] for _, v in top) or 1
    segs, labels, x, lx = [], [], float(x0), float(x0)
    for i, (name, (size, color)) in enumerate(top):
        color = color or FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
        w = total_w * size / total
        segs.append(f'<rect x="{x:.1f}" y="{y}" width="{w + 1:.1f}" height="8" fill="{esc(color)}"/>')
        x += w
        label = f"{name} {size * 100 / total:.0f}%"
        labels.append(f'<circle cx="{lx + 5:.0f}" cy="{y + 26}" r="4.5" fill="{esc(color)}"/>'
                      f'<text x="{lx + 15:.0f}" y="{y + 31}" fill="{MUTED}" font-size="12.5" font-family="{SANS}">{esc(label)}</text>')
        lx += 15 + len(label) * 7 + 18
    return (f'<defs><clipPath id="lb"><rect x="{x0}" y="{y}" width="{total_w}" height="8" rx="4"/></clipPath></defs>'
            f'<rect x="{x0}" y="{y}" width="{total_w}" height="8" rx="4" fill="#223349"/>'
            f'<g clip-path="url(#lb)">{"".join(segs)}</g>{"".join(labels)}')


def render(stats: dict) -> str:
    width, height = 980, 450
    avatar = find_avatar()
    if avatar:
        mime, enc = avatar
        photo = (f'<defs><clipPath id="ac"><circle cx="145" cy="190" r="88"/></clipPath></defs>'
                 f'<image x="57" y="102" width="176" height="176" href="data:{esc(mime)};base64,{enc}" '
                 f'xlink:href="data:{esc(mime)};base64,{enc}" clip-path="url(#ac)" preserveAspectRatio="xMidYMid slice"/>')
    else:
        photo = (f'<circle cx="145" cy="190" r="88" fill="{NAVY2}"/>'
                 f'<text x="145" y="204" text-anchor="middle" fill="{MINT}" font-size="46" font-weight="700" font-family="{SERIF}">{esc(NAME[:1])}</text>')

    fields = [("Repos", stats["repos"]), ("Stars", stats["stars"]), ("Followers", stats["followers"]),
              ("Commits · 12 mo", stats["commits"]), ("Pull requests · 12 mo", stats["pull_requests"]),
              ("Issues & reviews · 12 mo", stats["reviews_issues"]),
              ("Contributions · 12 mo", stats["contributions"]), ("Current streak", f'{stats["streak"]} days'),
              ("Longest streak", f'{stats["longest"]} days')]
    cells = []
    for i, (label, value) in enumerate(fields):
        row, col = divmod(i, 3)
        x, y = 270 + col * 225, 242 + row * 52
        shown = f"{value:,}" if isinstance(value, int) else value
        cells.append(f'<g class="s" style="animation-delay:{.15 * i + .3:.2f}s">'
                     f'<text x="{x}" y="{y}" fill="{MUTED}" font-size="12.5" font-family="{SANS}">{esc(label)}</text>'
                     f'<text x="{x}" y="{y + 24}" fill="{TEXT}" font-size="21" font-weight="700" font-family="{SANS}">{esc(shown)}</text></g>')

    desc = f"{NAME}: {ROLE}. {stats['repos']} repositories, {stats['stars']} stars, {stats['followers']} followers."
    css = (".tw{animation:tw 4s ease-in-out infinite}.s{opacity:0;animation:up .8s ease-out forwards}"
           ".ring{transform-box:fill-box;transform-origin:center;animation:ring 4s ease-in-out infinite}"
           ".moon{transform-box:fill-box;transform-origin:center;animation:ring 7s ease-in-out infinite}"
           "@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}"
           "@keyframes up{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}"
           "@keyframes ring{0%,100%{transform:scale(1);opacity:.55}50%{transform:scale(1.05);opacity:1}}")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(NAME)} — GitHub profile card</title>
<desc id="desc">{esc(desc)}</desc>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{NAVY}"/><stop offset="1" stop-color="{NAVY2}"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#FFF4D6" stop-opacity=".5"/><stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></radialGradient>
<clipPath id="card"><rect width="{width}" height="{height}" rx="22"/></clipPath>
</defs>
<style>{css}</style>
<g clip-path="url(#card)">
<rect width="{width}" height="{height}" fill="url(#bg)"/>
{sky(width, height)}
<circle class="moon" cx="905" cy="62" r="60" fill="url(#glow)"/><circle cx="905" cy="62" r="20" fill="#FFF4D6"/>
<circle cx="898" cy="56" r="3.5" fill="#E6DAB4"/><circle cx="912" cy="70" r="4.5" fill="#E6DAB4"/>
<path d="M0 400 L90 372 L170 392 L270 356 L360 388 L470 362 L570 394 L680 358 L790 390 L890 366 L980 388 V450 H0Z" fill="#0A1626" opacity=".85"/>
<path d="M0 425 L120 408 L260 424 L420 404 L580 424 L740 406 L900 422 L980 410 V450 H0Z" fill="#0E1B22"/>
{photo}
<circle class="ring" cx="145" cy="190" r="94" fill="none" stroke="{MINT}" stroke-width="2.5"/>
<text x="145" y="312" text-anchor="middle" fill="{MINT}" font-size="16" font-family="{SERIF}">@{esc(LOGIN)}</text>
<text x="145" y="334" text-anchor="middle" fill="{MUTED}" font-size="13" font-family="{SANS}">On GitHub for {esc(duration(stats["created_at"]))}</text>
<text x="270" y="78" fill="{MINT}" font-size="13" letter-spacing="3" font-family="{SANS}">GITHUB PROFILE</text>
<text x="270" y="118" fill="{TEXT}" font-size="33" font-family="{SERIF}">{esc(NAME)}</text>
<text x="270" y="146" fill="{CORAL}" font-size="17" font-family="{SANS}">{esc(ROLE)}</text>
<text x="270" y="172" fill="{MUTED}" font-size="14" font-family="{SANS}">{esc(TAGS)}</text>
<text x="270" y="194" fill="{MUTED}" font-size="14" font-family="{SANS}">{esc(LINE)}</text>
<line x1="270" y1="212" x2="930" y2="212" stroke="#34465B"/>
{"".join(cells)}
{lang_bar(stats["languages"], 57, 392, 866)}
</g>
</svg>'''


def main() -> int:
    if os.environ.get("PROFILE_MOCK"):
        stats = mock_stats()
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("Set GITHUB_TOKEN (or GH_TOKEN) with permission to read your GitHub profile.")
        stats = fetch_stats(token, LOGIN)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(stats), encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT) if OUTPUT.is_relative_to(ROOT) else OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
