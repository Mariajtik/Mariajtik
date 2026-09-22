#!/usr/bin/env python3
"""
GitHub README data automation for Mariajtik.

Uses only the Python standard library + GitHub REST API.
The script updates ONLY generated blocks in README.md.

Environment:
  GITHUB_TOKEN - GitHub Actions token
  GITHUB_REPOSITORY - owner/repo, automatically supplied by Actions
"""

import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

OWNER = "Mariajtik"
README = "README.md"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Mariajtik-readme-automation",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def api(path, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fmt_date(value):
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return value[:10]


def pct(value, total):
    return (value / total * 100) if total else 0


def svg_escape(text):
    return (
        str(text).replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def bar_svg(title, items, width=900, height=None):
    rows = max(len(items), 1)
    row_h = 34
    height = height or 70 + rows * row_h
    max_value = max([v for _, v in items] or [1])

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="18" fill="#0d1117"/>',
        f'<text x="32" y="38" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="22" font-weight="700">{svg_escape(title)}</text>',
    ]

    y = 72
    for label, value in items:
        label_text = svg_escape(label)
        shown = f"{value:.2f}%" if isinstance(value, float) else str(value)
        bar_w = int(500 * (value / max_value)) if max_value else 0
        out.append(f'<text x="32" y="{y+18}" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="14">{label_text}</text>')
        out.append(f'<rect x="190" y="{y+5}" width="500" height="18" rx="9" fill="#21262d"/>')
        out.append(f'<rect x="190" y="{y+5}" width="{bar_w}" height="18" rx="9" fill="#2563eb"/>')
        out.append(f'<text x="715" y="{y+19}" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="14">{svg_escape(shown)}</text>')
        y += row_h

    out.append("</svg>")
    return "\n".join(out)


def replace_block(text, name, content):
    start = f"<!-- AUTO:{name}:START -->"
    end = f"<!-- AUTO:{name}:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    replacement = f"{start}\n{content}\n{end}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text + "\n\n" + replacement + "\n"


def main():
    user = api(f"/users/{OWNER}")
    repos = api(f"/users/{OWNER}/repos", {"per_page": 100, "sort": "updated", "direction": "desc"})

    public_repos = [r for r in repos if not r.get("fork") and not r.get("archived")]
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)

    languages = Counter()
    for repo in public_repos:
        try:
            data = api(f"/repos/{OWNER}/{repo['name']}/languages")
            languages.update(data)
        except Exception:
            pass

    total_bytes = sum(languages.values())
    lang_items = []
    for lang, count in languages.most_common(10):
        lang_items.append((lang, pct(count, total_bytes)))

    top_repos = sorted(repos, key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0)), reverse=True)[:6]
    recent_repos = sorted(repos, key=lambda r: r.get("updated_at") or "", reverse=True)[:6]

    stats = f"""<p align="center">
<img src="https://img.shields.io/badge/Public_Repos-{user.get('public_repos', 0)}-2563EB?style=for-the-badge" />
<img src="https://img.shields.io/badge/Followers-{user.get('followers', 0)}-7C3AED?style=for-the-badge" />
<img src="https://img.shields.io/badge/Stars-{stars}-F59E0B?style=for-the-badge" />
<img src="https://img.shields.io/badge/Forks-{forks}-059669?style=for-the-badge" />
</p>"""

    language_text = "<br>".join(
        f"**{svg_escape(lang)}** — {value:.2f}%" for lang, value in lang_items
    ) or "No language data available."

    recent_rows = []
    for r in recent_repos:
        recent_rows.append(
            f'<tr><td><a href="{r["html_url"]}"><strong>{svg_escape(r["name"])}</strong></a></td>'
            f'<td>{svg_escape(r.get("language") or "—")}</td>'
            f'<td>⭐ {r.get("stargazers_count", 0)}</td>'
            f'<td>{fmt_date(r.get("updated_at"))}</td></tr>'
        )
    recent_table = """<table width="100%">
<tr><th>Repository</th><th>Language</th><th>Stars</th><th>Updated</th></tr>
""" + "\n".join(recent_rows) + "\n</table>"

    top_rows = []
    for r in top_repos:
        top_rows.append(
            f'- [{svg_escape(r["name"])}]({r["html_url"]}) — ⭐ {r.get("stargazers_count", 0)} · 🍴 {r.get("forks_count", 0)}'
        )
    top_text = "\n".join(top_rows) or "No repositories found."

    language_svg = bar_svg("Top Languages", lang_items[:8])
    (Path("generated")).mkdir(exist_ok=True)
    Path("generated/languages.svg").write_text(language_svg, encoding="utf-8")

    with open(README, "r", encoding="utf-8") as f:
        readme = f.read()

    readme = replace_block(readme, "STATS", stats)
    readme = replace_block(readme, "LANGUAGES", language_text)
    readme = replace_block(readme, "RECENT_REPOSITORIES", recent_table)
    readme = replace_block(readme, "TOP_REPOSITORIES", top_text)
    readme = replace_block(
        readme,
        "LAST_UPDATED",
        f'<p align="center"><small>Automatically updated by Python + GitHub Actions · {datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")}</small></p>',
    )

    with open(README, "w", encoding="utf-8") as f:
        f.write(readme)

    print("README automation completed.")
    print(f"Repositories: {user.get('public_repos', 0)}")
    print(f"Followers: {user.get('followers', 0)}")
    print(f"Stars: {stars}")
    print(f"Forks: {forks}")


if __name__ == "__main__":
    main()
