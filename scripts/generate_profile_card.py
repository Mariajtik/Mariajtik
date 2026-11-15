#!/usr/bin/env python3
"""Generate two starry-sky SVGs for a GitHub profile:
  assets/profile-card.svg      -> stats, issues/PRs, repos (public+private), ALL languages
  assets/contributions-3d.svg  -> isometric 3D contributions-per-day chart

Usage:
  PROFILE_TOKEN=... python scripts/generate_profile_card.py   # real data
  PROFILE_MOCK=1 python scripts/generate_profile_card.py      # offline preview

Private repos/languages need a personal access token (PROFILE_TOKEN). The default Actions
token (GITHUB_TOKEN) only sees public data. Only AGGREGATES are drawn (counts, percentages):
no private repo names ever appear in the images.
"""
from __future__ import annotations

import base64, datetime as dt, html, io, json, mimetypes, os, random, sys, time
import urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGIN = os.environ.get("GITHUB_USER", "Mariajtik")
OUT_CARD = Path(os.environ.get("PROFILE_OUTPUT", str(ROOT / "assets" / "profile-card.svg")))
OUT_3D = Path(os.environ.get("PROFILE_3D_OUTPUT", str(ROOT / "assets" / "contributions-3d.svg")))
INCLUDE_FORKS = os.environ.get("PROFILE_INCLUDE_FORKS") == "1"
NAME = os.environ.get("PROFILE_NAME", "Maria Baptista")
ROLE = os.environ.get("PROFILE_ROLE", "Full Stack Engineer · Aspiring Game Developer")
TAGS = os.environ.get("PROFILE_TAGS", "Resilient systems · Open source · AI engineering")
LINE = os.environ.get("PROFILE_LINE", "Exploring gameplay, systems design & interactive experiences")

NAVY, NAVY2 = "#0B1426", "#16263B"
MINT, CORAL, GOLD = "#9FD3B0", "#FF6B5E", "#FFD66B"
TEXT, MUTED = "#F2F0E6", "#AFC2D4"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
PALETTE = [MINT, GOLD, CORAL, "#8FB8E8", "#C9A7E8", "#7BD3D1", "#E8A7C9", "#B5D67A", "#E8C58F", "#9AA9F0"]
LEVELS = ["#2E5A4E", "#5FA58A", MINT, GOLD, CORAL]

PROFILE_Q = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    following { totalCount }
    issuesOpen: issues(states: OPEN) { totalCount }
    issuesClosed: issues(states: CLOSED) { totalCount }
    prsOpen: pullRequests(states: OPEN) { totalCount }
    prsClosed: pullRequests(states: CLOSED) { totalCount }
    prsMerged: pullRequests(states: MERGED) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""
REPOS_Q = """
query($login: String!, $after: String, $isFork: Boolean) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: $isFork, first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        isPrivate
        stargazerCount
        languages(first: 30, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
  }
}
"""


def graphql(token: str, query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "maria-profile-card"}
    last: Exception | None = None
    for attempt in range(3):
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
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i, cur = len(days) - 1, 0
    if i >= 0 and days[i][1] == 0:
        i -= 1
    while i >= 0 and days[i][1] > 0:
        cur += 1
        i -= 1
    return cur, longest


def calendar_stats(days: list[tuple[str, int]]) -> dict:
    counts = [c for _, c in days]
    total, n = sum(counts), max(len(counts), 1)
    active = sum(1 for c in counts if c > 0)
    peak_date, peak = max(days, key=lambda d: d[1]) if days else ("", 0)
    return {"total": total, "days": n, "active": active, "peak": peak, "peak_date": peak_date,
            "avg": total / n, "avg_active": total / active if active else 0.0}


def fetch_stats(token: str, login: str) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    d = graphql(token, PROFILE_Q, {"login": login, "from": (now - dt.timedelta(days=365)).isoformat(), "to": now.isoformat()})
    user = d.get("user")
    if user is None:
        raise RuntimeError(f"GitHub user {login!r} was not found")
    cc = user["contributionsCollection"]
    weeks = [[(x["date"], x["contributionCount"], x["weekday"]) for x in w["contributionDays"]]
             for w in cc["contributionCalendar"]["weeks"]]
    flat = [(a, b) for w in weeks for a, b, _ in w]
    cur, longest = streaks(flat)

    stars = pub = priv = 0
    langs: dict[str, tuple[int, str | None]] = {}
    after = None
    while True:
        repos = graphql(token, REPOS_Q, {"login": login, "after": after, "isFork": None if INCLUDE_FORKS else False})["user"]["repositories"]
        for r in repos["nodes"]:
            stars += int(r["stargazerCount"] or 0)
            priv += 1 if r["isPrivate"] else 0
            pub += 0 if r["isPrivate"] else 1
            for e in r["languages"]["edges"]:
                size, color = langs.get(e["node"]["name"], (0, None))
                langs[e["node"]["name"]] = (size + e["size"], color or e["node"]["color"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]

    return {"created_at": user["createdAt"], "followers": user["followers"]["totalCount"],
            "following": user["following"]["totalCount"], "repos_public": pub, "repos_private": priv, "stars": stars,
            "issues_open": user["issuesOpen"]["totalCount"], "issues_closed": user["issuesClosed"]["totalCount"],
            "prs_open": user["prsOpen"]["totalCount"], "prs_closed": user["prsClosed"]["totalCount"],
            "prs_merged": user["prsMerged"]["totalCount"], "commits": cc["totalCommitContributions"],
            "reviews": cc["totalPullRequestReviewContributions"], "private_contribs": cc["restrictedContributionsCount"],
            "streak": cur, "longest": longest, "weeks": weeks, "cal": calendar_stats(flat), "languages": langs}


def mock_stats() -> dict:
    rnd = random.Random(42)
    today = dt.date.today()
    day = today - dt.timedelta(days=(today.weekday() + 1) % 7) - dt.timedelta(weeks=52)
    weeks, week = [], []
    while day <= today:
        wd = (day.weekday() + 1) % 7
        base = rnd.choice([0, 0, 1, 2, 3, 5]) if 0 < wd < 6 else rnd.choice([0, 0, 0, 1, 2])
        if rnd.random() < .04:
            base += rnd.randint(12, 30)
        week.append((day.isoformat(), base, wd))
        if wd == 6:
            weeks.append(week)
            week = []
        day += dt.timedelta(days=1)
    if week:
        weeks.append(week)
    flat = [(a, b) for w in weeks for a, b, _ in w]
    cur, longest = streaks(flat)
    langs = {"Python": (520000, "#3572A5"), "TypeScript": (310000, "#3178c6"), "JavaScript": (140000, "#f1e05a"),
             "C#": (90000, "#178600"), "HTML": (40000, "#e34c26"), "CSS": (22000, "#563d7c"), "Go": (18000, "#00ADD8"),
             "Shell": (9000, "#89e051"), "Dockerfile": (3000, "#384d54"), "Lua": (2500, None), "GDScript": (1200, "#355570"),
             "Makefile": (400, "#427819")}
    return {"created_at": "2024-03-10T00:00:00Z", "followers": 67, "following": 65, "repos_public": 18, "repos_private": 9,
            "stars": 3, "issues_open": 2, "issues_closed": 14, "prs_open": 1, "prs_closed": 4, "prs_merged": 31,
            "commits": 412, "reviews": 9, "private_contribs": 120, "streak": cur, "longest": longest, "weeks": weeks,
            "cal": calendar_stats(flat), "languages": langs}


def find_avatar() -> tuple[str, str] | None:
    configured = os.environ.get("PROFILE_IMAGE_FILE")
    cands = [Path(configured)] if configured else [ROOT / f"avatar{e}" for e in (".png", ".jpg", ".jpeg", ".webp")] + [ROOT / "avatar"]
    for path in cands:
        if not path.is_file():
            continue
        data, mime = path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/png"
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGB")
            s = min(im.size)
            l, t = (im.width - s) // 2, (im.height - s) // 2
            im = im.crop((l, t, l + s, t + s)).resize((256, 256), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=86, optimize=True)
            data, mime = buf.getvalue(), "image/jpeg"
        except ImportError:
            if len(data) > 300_000:
                print("Warning: avatar is large; pip install pillow to shrink it.", file=sys.stderr)
        except Exception as exc:
            print(f"Warning: could not process avatar ({exc}).", file=sys.stderr)
        return mime, base64.b64encode(data).decode("ascii")
    return None


def esc(v: object) -> str:
    return html.escape(str(v), quote=True)


def duration(created_at: str) -> str:
    try:
        c = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        days = max(0, (dt.datetime.now(dt.timezone.utc) - c).days)
        y, days = divmod(days, 365)
        m, days = divmod(days, 30)
        return " ".join(p for p in (f"{y}y" if y else "", f"{m}mo" if m else "", f"{days}d" if not y else "") if p)
    except (TypeError, ValueError):
        return "—"


def days_txt(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


def short_date(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
        return f"{d:%b} {d.day}, {d.year}"
    except ValueError:
        return "—"


def shade(hexcol: str, f: float) -> str:
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))


def sky(width: int, height: int, clear: list[tuple[int, int, int, int]], count: int = 85) -> str:
    rnd = random.Random(LOGIN)
    out = []
    for _ in range(count):
        x, y = rnd.uniform(8, width - 8), rnd.uniform(8, height * 0.85)
        r, o = rnd.choice([.6, .8, 1, 1.2, 1.5]), rnd.uniform(.35, .9)
        tw = rnd.random() < .4
        delay, dur = rnd.uniform(0, 5), rnd.uniform(2.5, 5)
        if any(a < x < c and b < y < d for a, b, c, d in clear):
            continue
        cls = f' class="tw" style="animation-delay:{delay:.1f}s;animation-duration:{dur:.1f}s"' if tw else ""
        out.append(f'<circle{cls} cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFF4D6" opacity="{o:.2f}"/>')
    return "".join(out)


BASE_CSS = (".tw{animation:tw 4s ease-in-out infinite}.s{opacity:0;animation:up .8s ease-out forwards}"
            ".ring{transform-box:fill-box;transform-origin:center;animation:ring 4s ease-in-out infinite}"
            ".moon{transform-box:fill-box;transform-origin:center;animation:ring 7s ease-in-out infinite}"
            ".wk{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s ease-out both}"
            "@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}"
            "@keyframes up{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}"
            "@keyframes ring{0%,100%{transform:scale(1);opacity:.55}50%{transform:scale(1.05);opacity:1}}"
            "@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}")


def defs(width: int, height: int) -> str:
    return (f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{NAVY}"/>'
            f'<stop offset="1" stop-color="{NAVY2}"/></linearGradient>'
            '<radialGradient id="glow"><stop offset="0" stop-color="#FFF4D6" stop-opacity=".5"/>'
            '<stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="card"><rect width="{width}" height="{height}" rx="22"/></clipPath></defs>')


def moon(x: int, y: int) -> str:
    return (f'<circle class="moon" cx="{x}" cy="{y}" r="60" fill="url(#glow)"/><circle cx="{x}" cy="{y}" r="20" fill="#FFF4D6"/>'
            f'<circle cx="{x - 7}" cy="{y - 6}" r="3.5" fill="#E6DAB4"/><circle cx="{x + 7}" cy="{y + 8}" r="4.5" fill="#E6DAB4"/>')


def mountains(width: int, height: int) -> str:
    h = height
    return (f'<path d="M0 {h-52} L90 {h-80} L170 {h-60} L270 {h-96} L360 {h-64} L470 {h-90} L570 {h-58} L680 {h-94} '
            f'L790 {h-62} L890 {h-86} L{width} {h-64} V{h} H0Z" fill="#0A1626" opacity=".85"/>'
            f'<path d="M0 {h-24} L120 {h-42} L260 {h-26} L420 {h-46} L580 {h-26} L740 {h-44} L900 {h-28} L{width} {h-40} V{h} H0Z" fill="#0E1B22"/>')


def lang_section(langs: dict, x0: int, y: int, total_w: int) -> tuple[str, int]:
    items = sorted(langs.items(), key=lambda kv: -kv[1][0])
    total = sum(v[0] for _, v in items) or 1
    colored = [(n, s, c or PALETTE[i % len(PALETTE)]) for i, (n, (s, c)) in enumerate(items)]
    segs, x = [], float(x0)
    for n, s, c in colored:
        w = total_w * s / total
        segs.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w, 1.2):.1f}" height="8" fill="{esc(c)}"/>')
        x += w
    legend, lx, ly = [], x0, y + 34
    for n, s, c in colored:
        pct = s * 100 / total
        label = f"{n} {pct:.1f}%" if pct >= 0.1 else f"{n} <0.1%"
        w = 15 + len(label) * 7 + 18
        if lx + w > x0 + total_w:
            lx, ly = x0, ly + 22
        legend.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="4.5" fill="{esc(c)}"/>'
                      f'<text x="{lx + 15}" y="{ly}" fill="{MUTED}" font-size="12.5" font-family="{SANS}">{esc(label)}</text>')
        lx += w
    svg = (f'<defs><clipPath id="lb"><rect x="{x0}" y="{y}" width="{total_w}" height="8" rx="4"/></clipPath></defs>'
           f'<rect x="{x0}" y="{y}" width="{total_w}" height="8" rx="4" fill="#223349"/>'
           f'<g clip-path="url(#lb)">{"".join(segs)}</g>{"".join(legend)}')
    return svg, ly + 14


def render_card(s: dict) -> str:
    width = 980
    av = find_avatar()
    if av:
        mime, enc = av
        photo = (f'<defs><clipPath id="ac"><circle cx="145" cy="190" r="88"/></clipPath></defs>'
                 f'<image x="57" y="102" width="176" height="176" href="data:{esc(mime)};base64,{enc}" '
                 f'xlink:href="data:{esc(mime)};base64,{enc}" clip-path="url(#ac)" preserveAspectRatio="xMidYMid slice"/>')
    else:
        photo = (f'<circle cx="145" cy="190" r="88" fill="{NAVY2}"/><text x="145" y="204" text-anchor="middle" fill="{MINT}" '
                 f'font-size="46" font-weight="700" font-family="{SERIF}">{esc(NAME[:1])}</text>')

    repos = s["repos_public"] + s["repos_private"]
    prs = s["prs_open"] + s["prs_closed"] + s["prs_merged"]
    iss = s["issues_open"] + s["issues_closed"]
    c = s["cal"]
    cells = [
        ("Repositories", repos, f'{s["repos_public"]} public · {s["repos_private"]} private'),
        ("Stars", s["stars"], "public + private repos"),
        ("Followers", s["followers"], f'following {s["following"]}'),
        ("Pull requests", prs, f'{s["prs_open"]} open · {s["prs_closed"]} closed · {s["prs_merged"]} merged'),
        ("Issues", iss, f'{s["issues_open"]} open · {s["issues_closed"]} closed'),
        ("PR reviews · 12 mo", s["reviews"], "reviews given"),
        ("Commits · 12 mo", s["commits"], "default branches"),
        ("Contributions · 12 mo", c["total"], f'{s["private_contribs"]:,} private'),
        ("Active days · 12 mo", c["active"], f'of {c["days"]} days'),
        ("Highest in a day", c["peak"], short_date(c["peak_date"])),
        ("Average per day", f'{c["avg"]:.2f}', f'{c["avg_active"]:.2f} per active day'),
        ("Current streak", days_txt(s["streak"]), f'longest {days_txt(s["longest"])}'),
    ]
    g = []
    for i, (label, value, sub) in enumerate(cells):
        row, col = divmod(i, 3)
        x, y = 270 + col * 225, 242 + row * 62
        shown = f"{value:,}" if isinstance(value, int) else value
        g.append(f'<g class="s" style="animation-delay:{.12 * i + .3:.2f}s">'
                 f'<text x="{x}" y="{y}" fill="{MUTED}" font-size="12.5" font-family="{SANS}">{esc(label)}</text>'
                 f'<text x="{x}" y="{y + 23}" fill="{TEXT}" font-size="21" font-weight="700" font-family="{SANS}">{esc(shown)}</text>'
                 f'<text x="{x}" y="{y + 40}" fill="{MUTED}" font-size="11.5" font-family="{SANS}" opacity=".8">{esc(sub)}</text></g>')

    lang_y = 506
    lang_svg, bottom = lang_section(s["languages"], 57, lang_y + 16, 866)
    height = bottom + 26
    desc = (f"{NAME}: {ROLE}. {repos} repositories ({s['repos_private']} private), {s['stars']} stars, "
            f"{s['followers']} followers, {len(s['languages'])} languages.")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(NAME)} — GitHub profile card</title><desc id="desc">{esc(desc)}</desc>
{defs(width, height)}<style>{BASE_CSS}</style>
<g clip-path="url(#card)"><rect width="{width}" height="{height}" fill="url(#bg)"/>
{sky(width, height, [(255, 60, 940, lang_y - 8), (30, 90, 260, 350), (40, lang_y - 20, 940, height)])}{moon(905, 62)}{mountains(width, height)}
{photo}<circle class="ring" cx="145" cy="190" r="94" fill="none" stroke="{MINT}" stroke-width="2.5"/>
<text x="145" y="312" text-anchor="middle" fill="{MINT}" font-size="16" font-family="{SERIF}">@{esc(LOGIN)}</text>
<text x="145" y="334" text-anchor="middle" fill="{MUTED}" font-size="13" font-family="{SANS}">On GitHub for {esc(duration(s["created_at"]))}</text>
<text x="270" y="78" fill="{MINT}" font-size="13" letter-spacing="3" font-family="{SANS}">GITHUB PROFILE</text>
<text x="270" y="118" fill="{TEXT}" font-size="33" font-family="{SERIF}">{esc(NAME)}</text>
<text x="270" y="146" fill="{CORAL}" font-size="17" font-family="{SANS}">{esc(ROLE)}</text>
<text x="270" y="172" fill="{MUTED}" font-size="14" font-family="{SANS}">{esc(TAGS)}</text>
<text x="270" y="194" fill="{MUTED}" font-size="14" font-family="{SANS}">{esc(LINE)}</text>
<line x1="270" y1="212" x2="930" y2="212" stroke="#34465B"/>
{"".join(g)}
<line x1="57" y1="{lang_y - 14}" x2="923" y2="{lang_y - 14}" stroke="#34465B"/>
<text x="57" y="{lang_y + 4}" fill="{MINT}" font-size="12" letter-spacing="2.5" font-family="{SANS}">LANGUAGES · ALL REPOSITORIES (PUBLIC + PRIVATE) · {len(s["languages"])} USED</text>
{lang_svg}</g></svg>'''


def render_3d(s: dict) -> str:
    width, weeks, c = 980, s["weeks"], s["cal"]
    nw = len(weeks)
    cx0, cx1 = 270, 940
    a = (cx1 - cx0) / (nw + 7)
    b, hmax = a * .30, 92
    ox, oy = cx0 + 7 * a, 70 + hmax
    height = int(oy + (nw + 7) * b + 2 * b + 46)
    peak = max(c["peak"], 1)
    top = None
    groups = []
    for w, week in enumerate(weeks):
        cells = []
        for date, count, wd in sorted(week, key=lambda t: t[2]):
            px, py = ox + (w - wd) * a, oy + (w + wd) * b
            k = .86
            gx, gy = a * k, b * k
            ground = [(px, py + b - gy), (px + gx, py + b), (px, py + b + gy), (px - gx, py + b)]
            if count <= 0:
                cells.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in ground)}" fill="#1B2A3F"/>')
                continue
            h = 4 + (hmax - 4) * (count / peak) ** .55
            idx = min(4, int(count / peak * 5 - 1e-9)) if count < peak else 4
            col = LEVELS[idx]
            up = [(x, y - h) for x, y in ground]
            cells.append(f'<polygon points="{up[3][0]:.1f},{up[3][1]:.1f} {up[2][0]:.1f},{up[2][1]:.1f} {ground[2][0]:.1f},{ground[2][1]:.1f} {ground[3][0]:.1f},{ground[3][1]:.1f}" fill="{shade(col, .62)}"/>')
            cells.append(f'<polygon points="{up[1][0]:.1f},{up[1][1]:.1f} {up[2][0]:.1f},{up[2][1]:.1f} {ground[2][0]:.1f},{ground[2][1]:.1f} {ground[1][0]:.1f},{ground[1][1]:.1f}" fill="{shade(col, .42)}"/>')
            cells.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in up)}" fill="{col}"/>')
            if count == c["peak"] and top is None:
                top = (px, py + b - gy - h, count, date)
        groups.append(f'<g class="wk" style="animation-delay:{w * .025:.2f}s">{"".join(cells)}</g>')

    callout = ""
    if top:
        tx, ty, cnt, date = top
        label = f"Peak · {cnt} · {short_date(date)}"
        lx = min(max(tx, cx0 + 70), cx1 - 70)
        callout = (f'<line x1="{tx:.1f}" y1="{ty - 2:.1f}" x2="{tx:.1f}" y2="{ty - 14:.1f}" stroke="{CORAL}" stroke-width="1.5"/>'
                   f'<text x="{lx:.1f}" y="{ty - 20:.1f}" text-anchor="middle" fill="{CORAL}" font-size="13" font-weight="700" font-family="{SANS}">{esc(label)}</text>')

    blocks = [("HIGHEST IN A DAY", str(c["peak"]), CORAL, short_date(c["peak_date"])),
              ("AVERAGE PER DAY", f'{c["avg"]:.2f}', MINT, f'{c["avg_active"]:.2f} per active day'),
              ("ACTIVE DAYS", f'{c["active"]}', GOLD, f'of {c["days"]} · {c["active"] * 100 // c["days"]}%')]
    left = []
    for i, (lab, val, col, sub) in enumerate(blocks):
        y = 150 + i * 82
        left.append(f'<g class="s" style="animation-delay:{.3 + i * .2:.1f}s">'
                    f'<text x="40" y="{y}" fill="{MUTED}" font-size="12" letter-spacing="2" font-family="{SANS}">{lab}</text>'
                    f'<text x="40" y="{y + 36}" fill="{col}" font-size="38" font-family="{SERIF}">{esc(val)}</text>'
                    f'<text x="40" y="{y + 56}" fill="{MUTED}" font-size="12.5" font-family="{SANS}">{esc(sub)}</text></g>')
    ly = height - 22
    legend = f'<text x="{cx1 - 190}" y="{ly + 4}" fill="{MUTED}" font-size="11.5" font-family="{SANS}">Less</text>'
    for i, col in enumerate(["#1B2A3F"] + LEVELS):
        legend += f'<rect x="{cx1 - 160 + i * 18}" y="{ly - 7}" width="12" height="12" rx="2" fill="{col}"/>'
    legend += f'<text x="{cx1 - 160 + 6 * 18 + 4}" y="{ly + 4}" fill="{MUTED}" font-size="11.5" font-family="{SANS}">More</text>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t3 d3">
<title id="t3">Contributions per day, last 12 months</title>
<desc id="d3">Isometric 3D chart. Highest in a day: {c["peak"]}. Average per day: {c["avg"]:.2f}. Active days: {c["active"]} of {c["days"]}.</desc>
{defs(width, height)}<style>{BASE_CSS}</style>
<g clip-path="url(#card)"><rect width="{width}" height="{height}" fill="url(#bg)"/>
{sky(width, height, [(20, 40, 950, height - 30)], 60)}{moon(915, 52)}
<text x="40" y="62" fill="{MINT}" font-size="13" letter-spacing="3" font-family="{SANS}">CONTRIBUTIONS PER DAY</text>
<text x="40" y="84" fill="{MUTED}" font-size="13" font-family="{SANS}">Last 12 months · commits, PRs, issues &amp; reviews</text>
{"".join(left)}{"".join(groups)}{callout}{legend}</g></svg>'''


def main() -> int:
    if os.environ.get("PROFILE_MOCK"):
        stats = mock_stats()
    else:
        token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("Set PROFILE_TOKEN (personal access token) or GITHUB_TOKEN.")
        if not os.environ.get("PROFILE_TOKEN"):
            print("Warning: no PROFILE_TOKEN; private repos and languages will NOT be counted.", file=sys.stderr)
        stats = fetch_stats(token, LOGIN)
    for path, svg in ((OUT_CARD, render_card(stats)), (OUT_3D, render_3d(stats))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")
        print(f"Generated {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} ({len(svg) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
