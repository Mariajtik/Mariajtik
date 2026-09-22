```python
#!/usr/bin/env python3

import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


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

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fmt_date(value):
    if not value:
        return "—"

    try:
        date = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        return date.strftime("%d %b %Y")

    except Exception:
        return value[:10]


def percentage(value, total):
    if not total:
        return 0

    return value / total * 100


def escape_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def replace_block(text, name, content):

    start = f"<!-- AUTO:{name}:START -->"
    end = f"<!-- AUTO:{name}:END -->"

    pattern = re.compile(
        re.escape(start) +
        r".*?" +
        re.escape(end),
        re.S
    )

    replacement = (
        f"{start}\n"
        f"{content}\n"
        f"{end}"
    )

    if pattern.search(text):
        return pattern.sub(
            replacement,
            text,
            count=1
        )

    return (
        text +
        "\n\n" +
        replacement +
        "\n"
    )


def create_language_svg(items):

    width = 900
    row_height = 34
    height = 80 + max(len(items), 1) * row_height

    maximum = max(
        [value for _, value in items] or [1]
    )

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',

        '<rect width="100%" height="100%" '
        'rx="18" fill="#0d1117"/>',

        '<text x="32" y="38" '
        'fill="#f0f6fc" '
        'font-family="Arial,sans-serif" '
        'font-size="22" '
        'font-weight="700">'
        'Top Languages'
        '</text>'
    ]

    y = 72

    for language, value in items:

        bar_width = int(
            500 * (value / maximum)
        ) if maximum else 0

        svg.append(
            f'<text x="32" y="{y + 18}" '
            f'fill="#c9d1d9" '
            f'font-family="Arial,sans-serif" '
            f'font-size="14">'
            f'{escape_html(language)}'
            f'</text>'
        )

        svg.append(
            f'<rect x="190" y="{y + 5}" '
            f'width="500" height="18" '
            f'rx="9" fill="#21262d"/>'
        )

        svg.append(
            f'<rect x="190" y="{y + 5}" '
            f'width="{bar_width}" height="18" '
            f'rx="9" fill="#2563eb"/>'
        )

        svg.append(
            f'<text x="715" y="{y + 19}" '
            f'fill="#f0f6fc" '
            f'font-family="Arial,sans-serif" '
            f'font-size="14">'
            f'{value:.2f}%'
            f'</text>'
        )

        y += row_height

    svg.append("</svg>")

    return "\n".join(svg)


def main():

    print("Starting GitHub README automation...")

    user = api(
        f"/users/{OWNER}"
    )

    repositories = api(
        f"/users/{OWNER}/repos",
        {
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }
    )

    public_repositories = [
        repo
        for repo in repositories
        if not repo.get("fork")
        and not repo.get("archived")
    ]

    total_stars = sum(
        repo.get("stargazers_count", 0)
        for repo in repositories
    )

    total_forks = sum(
        repo.get("forks_count", 0)
        for repo in repositories
    )

    print(
        f"Found {len(repositories)} repositories."
    )

    print(
        f"Followers: {user.get('followers', 0)}"
    )

    print(
        f"Stars: {total_stars}"
    )

    print(
        f"Forks: {total_forks}"
    )

    languages = Counter()

    for repository in public_repositories:

        try:

            repository_languages = api(
                f"/repos/{OWNER}/{repository['name']}/languages"
            )

            languages.update(
                repository_languages
            )

        except Exception as error:

            print(
                f"Could not read languages for "
                f"{repository['name']}: {error}"
            )

    total_language_bytes = sum(
        languages.values()
    )

    language_items = []

    for language, value in languages.most_common(10):

        language_items.append(
            (
                language,
                percentage(
                    value,
                    total_language_bytes
                )
            )
        )

    recent_repositories = sorted(
        repositories,
        key=lambda repo:
        repo.get("updated_at") or "",
        reverse=True
    )[:6]

    top_repositories = sorted(
        repositories,
        key=lambda repo: (
            repo.get("stargazers_count", 0),
            repo.get("forks_count", 0)
        ),
        reverse=True
    )[:6]

    stats_html = f"""
<p align="center">

<img src="https://img.shields.io/badge/Public_Repos-{user.get('public_repos', 0)}-2563EB?style=for-the-badge"/>

<img src="https://img.shields.io/badge/Followers-{user.get('followers', 0)}-7C3AED?style=for-the-badge"/>

<img src="https://img.shields.io/badge/Stars-{total_stars}-F59E0B?style=for-the-badge"/>

<img src="https://img.shields.io/badge/Forks-{total_forks}-059669?style=for-the-badge"/>

</p>
""".strip()

    languages_html = "<br>".join(
        f"**{escape_html(language)}** — {value:.2f}%"
        for language, value in language_items
    )

    if not languages_html:
        languages_html = "No language data available."

    rows = []

    for repository in recent_repositories:

        rows.append(
            f"""
<tr>

<td>
<a href="{repository['html_url']}">
<strong>{escape_html(repository['name'])}</strong>
</a>
</td>

<td>
{escape_html(repository.get('language') or '—')}
</td>

<td>
⭐ {repository.get('stargazers_count', 0)}
</td>

<td>
{fmt_date(repository.get('updated_at'))}
</td>

</tr>
""".strip()
        )

    recent_html = """
<table width="100%">

<tr>
<th>Repository</th>
<th>Language</th>
<th>Stars</th>
<th>Updated</th>
</tr>

""" + "\n".join(rows) + """

</table>
"""

    top_html = "\n".join(
        f'- [{escape_html(repo["name"])}]({repo["html_url"]}) '
        f'— ⭐ {repo.get("stargazers_count", 0)} '
        f'· 🍴 {repo.get("forks_count", 0)}'
        for repo in top_repositories
    )

    if not top_html:
        top_html = "No repositories found."

    generated_directory = Path("generated")

    generated_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    language_svg = create_language_svg(
        language_items[:8]
    )

    Path(
        "generated/languages.svg"
    ).write_text(
        language_svg,
        encoding="utf-8"
    )

    readme_path = Path(README)

    readme = readme_path.read_text(
        encoding="utf-8"
    )

    readme = replace_block(
        readme,
        "ST
```
