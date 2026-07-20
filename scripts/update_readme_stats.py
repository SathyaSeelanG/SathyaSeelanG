#!/usr/bin/env python3
"""
Fetches live GitHub data for the account via the REST API and rewrites the
stats block in README.md between the <!-- STATS:START --> / <!-- STATS:END -->
markers. No third-party badge/image services, no hardcoded numbers — every
number here is fetched fresh each time this script runs.

Run by .github/workflows/update-readme-stats.yml on a schedule, on push,
and on manual dispatch.
"""
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone

USERNAME = "SathyaSeelanG"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

START_MARKER = "<!-- STATS:START -->"
END_MARKER = "<!-- STATS:END -->"


def gh_get(path):
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", USERNAME)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_all_repos():
    repos = []
    page = 1
    while True:
        batch = gh_get(f"/users/{USERNAME}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def main():
    user = gh_get(f"/users/{USERNAME}")
    repos = get_all_repos()

    non_fork = [r for r in repos if not r.get("fork")]
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)

    lang_counter = Counter()
    for r in non_fork:
        lang = r.get("language")
        if lang:
            lang_counter[lang] += 1
    top_langs = lang_counter.most_common(6)

    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    account_age_days = (datetime.now(timezone.utc) - created).days
    account_age_years = round(account_age_days / 365.25, 1)

    lang_lines = "\n".join(
        f"| {lang} | {count} repo{'s' if count != 1 else ''} |" for lang, count in top_langs
    ) or "| — | — |"

    block = f"""{START_MARKER}
### 📊 GitHub Insights

| Metric | Value |
|---|---|
| Public repos | {user.get('public_repos', len(repos))} |
| Followers | {user.get('followers', 0)} |
| Following | {user.get('following', 0)} |
| Total stars across repos | {total_stars} |
| Total forks across repos | {total_forks} |
| Account age | {account_age_years} years |

**Top languages (by repo count):**

| Language | Repos |
|---|---|
{lang_lines}

{END_MARKER}"""

    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER in content and END_MARKER in content:
        pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
        new_content = pattern.sub(block, content)
    else:
        new_content = content + "\n\n" + block + "\n"

    if new_content != content:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md stats block updated.")
    else:
        print("No change in stats — README.md left as is.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Failed to update stats: {e}", file=sys.stderr)
        sys.exit(1)
