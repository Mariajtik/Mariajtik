import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone


OWNER = "Mariajtik"
README_FILE = "README.md"

TOKEN = os.environ.get("GITHUB_TOKEN")

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
        return response.read().decode("utf-8")


def get_json(endpoint, params=None):
    import json

    return json.loads(
        github_api(endpoint, params)
    )


def replace_block(text, name, content):
    start = f"<!-- AUTO:{name}:START -->"
    end = f"<!-- AUTO:{name}:END -->"

    pattern = re.compile(
        re.escape(start) +
        r".*?" +
        re.escape(end),
        re.DOTALL
    )

    replacement = (
        start +
        "\n" +
        content +
        "\n" +
        end
    )

    if pattern.search(text):
        return pattern.sub(
            replacement,
            text,
            count=1
        )

    return text + "\n\n" + replacement + "\n"


def main():

    print("Starting GitHub README automation...")

    user = get_json(
        f"/users/{OWNER}"
    )

    repositories = get_json(
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
        f"Repositories: {len(repositories)}"
    )

    followers = user.get(
        "followers",
        0
    )

    following = user.get(
        "following",
        0
    )

    public_repos = user.get(
        "public_repos",
        0
    )

    stars = sum(
        repo.get(
            "stargazers_count",
            0
        )
        for repo in repositories
    )

    forks = sum(
        repo.get(
            "forks_count",
            0
        )
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

    recent = sorted(
        repositories,
        key=lambda repo:
        repo.get("updated_at") or "",
        reverse=True
    )[:6]

    rows = []

    for repo in recent:

        name = repo.get(
            "name",
            "Unknown"
        )

        url = repo.get(
            "html_url",
            "#"
        )

        language = repo.get(
            "language"
        ) or "—"

        repo_stars = repo.get(
            "stargazers_count",
            0
        )

        updated = repo.get(
            "updated_at",
            ""
        )

        if updated:
            updated = updated[:10]

        rows.append(
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

    recent_repositories = """
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

    top = sorted(
        repositories,
        key=lambda repo: (
            repo.get(
                "stargazers_count",
                0
            ),
            repo.get(
                "forks_count",
                0
            )
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

    language_data = {}

    for repo in repositories:

        try:

            languages = get_json(
                f"/repos/{OWNER}/{repo['name']}/languages"
            )

            for language, amount in languages.items():

                language_data[language] = (
                    language_data.get(
                        language,
                        0
                    ) + amount
                )

        except Exception as error:

            print(
                f"Could not read languages for "
                f"{repo['name']}: {error}"
            )

    total_bytes = sum(
        language_data.values()
    )

    language_lines = []

    for language, amount in sorted(
        language_data.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]:

        percentage = (
            amount / total_bytes * 100
            if total_bytes
            else 0
        )

        language_lines.append(
            f"**{language}** — {percentage:.2f}%"
        )

    languages = "<br>".join(
        language_lines
    )

    if not languages:
        languages = "No language data available."

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

    with open(
        README_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        readme = file.read()

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
        recent_repositories
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

    with open(
        README_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(readme)

    print("README updated successfully.")

    print(
        f"Followers: {followers}"
    )

    print(
        f"Following: {following}"
    )

    print(
        f"Stars: {stars}"
    )

    print(
        f"Forks: {forks}"
    )


if __name__ == "__main__":
    main()
