import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


OWNER = "Mariajtik"
README_FILE = Path("README.md")

TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Mariajtik-README-Automation",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def github_api(endpoint, params=None):

    url = "https://api.github.com" + endpoint

    if params:
        url += "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def replace_block(readme, name, content):

    start = f"<!-- AUTO:{name}:START -->"
    end = f"<!-- AUTO:{name}:END -->"

    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL
    )

    replacement = (
        start
        + "\n"
        + content
        + "\n"
        + end
    )

    if pattern.search(readme):
        return pattern.sub(
            replacement,
            readme,
            count=1
        )

    return readme + "\n\n" + replacement + "\n"


def main():

    print("Starting README automation...")

    # --------------------------------------------------
    # USER
    # --------------------------------------------------

    user = github_api(
        f"/users/{OWNER}"
    )

    # --------------------------------------------------
    # REPOSITORIES
    # --------------------------------------------------

    repositories = github_api(
        f"/users/{OWNER}/repos",
        {
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }
    )

    repositories = [
        repo
        for repo in repositories
        if not repo.get("fork")
        and not repo.get("archived")
    ]

    print(
        f"Repositories found: {len(repositories)}"
    )

    # --------------------------------------------------
    # BASIC STATS
    # --------------------------------------------------

    followers = user.get("followers", 0)
    following = user.get("following", 0)
    public_repos = user.get("public_repos", 0)

    stars = sum(
        repo.get("stargazers_count", 0)
        for repo in repositories
    )

    forks = sum(
        repo.get("forks_count", 0)
        for repo in repositories
    )

    stats = f"""
<p align="center">

<img src="https://img.shields.io/badge/Public_Repositories-{public_repos}-2563EB?style=for-the-badge">

<img src="https://img.shields.io/badge/Followers-{followers}-7C3AED?style=for-the-badge">

<img src="https://img.shields.io/badge/Following-{following}-059669?style=for-the-badge">

<img src="https://img.shields.io/badge/Stars-{stars}-F59E0B?style=for-the-badge">

<img src="https://img.shields.io/badge/Forks-{forks}-EA4B71?style=for-the-badge">

</p>
""".strip()

    # --------------------------------------------------
    # LANGUAGES
    # --------------------------------------------------

    language_counter = Counter()

    for repo in repositories:

        try:

            languages = github_api(
                f"/repos/{OWNER}/{repo['name']}/languages"
            )

            language_counter.update(
                languages
            )

        except Exception as error:

            print(
                f"Language error for {repo['name']}: {error}"
            )

    total_bytes = sum(
        language_counter.values()
    )

    language_lines = []

    for language, amount in language_counter.most_common(10):

        if total_bytes:
            percentage = (
                amount / total_bytes
            ) * 100
        else:
            percentage = 0

        language_lines.append(
            f"**{language}** — {percentage:.2f}%"
        )

    languages = "<br>".join(
        language_lines
    )

    if not languages:
        languages = "No language data available."

    # --------------------------------------------------
    # RECENT REPOSITORIES
    # --------------------------------------------------

    recent = sorted(
        repositories,
        key=lambda repo:
        repo.get("updated_at") or "",
        reverse=True
    )[:6]

    recent_rows = []

    for repo in recent:

        name = repo["name"]
        url = repo["html_url"]
        language = repo.get("language") or "—"
        repo_stars = repo.get(
            "stargazers_count",
            0
        )

        updated = repo.get(
            "updated_at",
            ""
        )[:10]

        recent_rows.append(
            f"""
<tr>

<td>
<a href="{url}">
<strong>{name}</strong>
</a>
</td>

<td>{language}</td>

<td>⭐ {repo_stars}</td>

<td>{updated}</td>

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

""" + "\n".join(recent_rows) + """

</table>
"""

    # --------------------------------------------------
    # TOP REPOSITORIES
    # --------------------------------------------------

    top = sorted(
        repositories,
        key=lambda repo: (
            repo.get("stargazers_count", 0),
            repo.get("forks_count", 0)
        ),
        reverse=True
    )[:6]

    top_lines = []

    for repo in top:

        top_lines.append(
            f'- [{repo["name"]}]({repo["html_url"]}) '
            f'— ⭐ {repo.get("stargazers_count", 0)} '
            f'· 🍴 {repo.get("forks_count", 0)}'
        )

    top_repositories = "\n".join(
        top_lines
    )

    if not top_repositories:
        top_repositories = "No repositories found."

    # --------------------------------------------------
    # LAST UPDATED
    # --------------------------------------------------

    now = datetime.now(
        timezone.utc
    ).strftime(
        "%d %b %Y, %H:%M UTC"
    )

    last_updated = f"""
<p align="center">
<small>
Automatically updated by Python + GitHub Actions · {now}
</small>
</p>
""".strip()

    # --------------------------------------------------
    # README
    # --------------------------------------------------

    readme = README_FILE.read_text(
        encoding="utf-8"
    )

    readme = replace_block(
        readme,
        "STATS",
        stats
    )

    readme = replace_block(
        readme,
        "LANGUAGES",
        languages
    )

    readme = replace_block(
        readme,
        "RECENT_REPOSITORIES",
        recent_html
    )

    readme = replace_block(
        readme,
        "TOP_REPOSITORIES",
        top_repositories
    )

    readme = replace_block(
        readme,
        "LAST_UPDATED",
        last_updated
    )

    README_FILE.write_text(
        readme,
        encoding="utf-8"
    )

    print(
        "README updated successfully."
    )

    print(
        f"Followers: {followers}"
    )

    print(
        f"Stars: {stars}"
    )

    print(
        f"Forks: {forks}"
    )


if __name__ == "__main__":
    main()
