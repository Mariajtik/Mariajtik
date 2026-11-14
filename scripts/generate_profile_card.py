#!/usr/bin/env python3
"""Generate a personalized SVG profile card for Mariajtik.

Usage:
  GITHUB_TOKEN=... python scripts/generate_profile_card.py

The script looks for an image named ``avatar`` in the repository root, accepting
PNG, JPG/JPEG, or WebP extensions. Set PROFILE_IMAGE_FILE to override the path.
The output defaults to ``assets/profile-card.svg``.
"""
from __future__ import annotations

import base64
import datetime as dt
import html
import json
import mimetypes
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOGIN = os.environ.get("GITHUB_USER", "Mariajtik")
OUTPUT = Path(os.environ.get("PROFILE_OUTPUT", str(ROOT / "assets" / "profile-card.svg")))
NAVY = "#0F1B2D"
MINT = "#9FD3B0"
CORAL = "#FF6B5E"
TEXT = "#E6EDF3"
MUTED = "#AFC2D4"


def graphql(token: str, query: str, variables: dict) -> dict:
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "maria-profile-card-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "GitHub GraphQL request failed"))
    return payload["data"]


def fetch_stats(token: str, login: str) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(days=365)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
          contributionCalendar { totalContributions }
        }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $after) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { stargazerCount }
        }
      }
    }
    """
    after = None
    stars = repos_count = 0
    stats = None
    while True:
        data = graphql(token, query, {
            "login": login,
            "from": start.isoformat(),
            "to": now.isoformat(),
            "after": after,
        })
        user = data.get("user")
        if user is None:
            raise RuntimeError(f"GitHub user {login!r} was not found")
        repos = user["repositories"]
        if stats is None:
            contributions = user["contributionsCollection"]
            repos_count = repos["totalCount"]
            stats = {
                "created_at": user["createdAt"],
                "followers": user["followers"]["totalCount"],
                "repos": repos_count,
                "commits": contributions["totalCommitContributions"],
                "pull_requests": contributions["totalPullRequestContributions"],
                "issues": contributions["totalIssueContributions"],
                "reviews": contributions["totalPullRequestReviewContributions"],
                "contributions": contributions["contributionCalendar"]["totalContributions"],
            }
        stars += sum(int(repo["stargazerCount"] or 0) for repo in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    stats["stars"] = stars
    return stats


def find_avatar() -> tuple[str, str] | None:
    configured = os.environ.get("PROFILE_IMAGE_FILE")
    candidates = [Path(configured)] if configured else [ROOT / f"avatar{ext}" for ext in (".png", ".jpg", ".jpeg", ".webp")]
    # Also allow the exact filename ``avatar`` when it has no extension.
    if not configured:
        candidates.append(ROOT / "avatar")
    for path in candidates:
        if path.is_file():
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return mime, encoded
    return None


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def duration(created_at: str) -> str:
    try:
        created = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        days = max(0, (dt.datetime.now(dt.timezone.utc) - created).days)
        years, days = divmod(days, 365)
        months, days = divmod(days, 30)
        return ", ".join(part for part in (
            f"{years}y" if years else "",
            f"{months}mo" if months else "",
            f"{days}d",
        ) if part)
    except (TypeError, ValueError):
        return "—"


def render(stats: dict) -> str:
    width, height = 980, 340
    avatar = find_avatar()
    image = ""
    if avatar:
        mime, encoded = avatar
        image = (
            '<defs><clipPath id="avatarClip"><circle cx="145" cy="150" r="88"/></clipPath></defs>'
            f'<image x="57" y="62" width="176" height="176" href="data:{esc(mime)};base64,{encoded}" '
            'clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice"/>'
            f'<circle cx="145" cy="150" r="90" fill="none" stroke="{MINT}" stroke-width="3"/>'
        )
    else:
        image = (
            f'<circle cx="145" cy="150" r="88" fill="#16263B" stroke="{MINT}" stroke-width="3"/>'
            f'<text x="145" y="164" text-anchor="middle" fill="{MINT}" font-size="42" font-weight="700">M</text>'
        )

    fields = [
        ("Repos", stats["repos"]),
        ("Stars", stats["stars"]),
        ("Followers", stats["followers"]),
        ("Commits (last 12 months)", stats["commits"]),
        ("Pull requests (last 12 months)", stats["pull_requests"]),
        ("Issues and reviews (last 12 months)", stats["issues"] + stats["reviews"]),
        ("Contributions (last 12 months)", stats["contributions"]),
        ("GitHub journey", duration(stats["created_at"])),
    ]
    rows = []
    x_left, x_right = 385, 685
    y0, row_gap = 105, 45
    for index, (label, value) in enumerate(fields):
        column, row = divmod(index, 4)
        x = x_left if column == 0 else x_right
        y = y0 + row * row_gap
        rows.append(
            f'<text x="{x}" y="{y}" fill="{MUTED}" font-size="13">{esc(label)}</text>'
            f'<text x="{x}" y="{y + 22}" fill="{TEXT}" font-size="19" font-weight="700">{esc(value)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">Maria Baptista — GitHub profile card</title>
<desc id="desc">Full Stack Engineer and aspiring game developer, interested in resilient systems, open source, and AI-powered engineering.</desc>
<rect width="{width}" height="{height}" rx="20" fill="{NAVY}"/>
<path d="M0 300 Q250 250 470 320 T980 285 V340 H0Z" fill="#16263B" opacity=".8"/>
{image}
<text x="270" y="91" fill="{MINT}" font-size="14" letter-spacing="2">GITHUB PROFILE</text>
<text x="270" y="132" fill="{TEXT}" font-size="30" font-weight="700">Maria Baptista</text>
<text x="270" y="160" fill="{CORAL}" font-size="17">Full Stack Engineer · Aspiring Game Developer</text>
<text x="270" y="186" fill="{MUTED}" font-size="14">Resilient systems · Open source · AI engineering</text>
<text x="270" y="211" fill="{MUTED}" font-size="14">Exploring gameplay, systems design &amp; interactive experiences</text>
<line x1="270" y1="231" x2="930" y2="231" stroke="#34465B"/>
{''.join(rows)}
</svg>'''


def main() -> int:
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
