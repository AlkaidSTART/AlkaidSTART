#!/usr/bin/env python3
"""
Fetch recent public events for AlkaidSTART from the GitHub REST API
and update the <!-- START_SECTION:activity --> block in README.md
using an editorial, minimalist log format.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error

USERNAME = "AlkaidSTART"
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
README_PATH = os.path.join(REPO_DIR, "README.md")
MAX_EVENTS = 5


def fetch_events():
    url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=30"
    headers = {
        "User-Agent": "AlkaidSTART-Telemetry-Agent",
        "Accept": "application/vnd.github.v3+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                data = resp.read().decode("utf-8")
                return json.loads(data)
    except Exception as e:
        print(f"[!] Warning: Failed to fetch events from GitHub API: {e}", file=sys.stderr)
    return None


def format_event(event):
    etype = event.get("type")
    repo = event.get("repo", {}).get("name", "")
    if not repo:
        return None
    repo_url = f"https://github.com/{repo}"
    repo_link = f"**[{repo}]({repo_url})**"
    created_at = event.get("created_at", "")
    date_tag = created_at[:10].replace("-", ".") if len(created_at) >= 10 else "RECENT"
    payload = event.get("payload", {})

    if etype == "PushEvent":
        commits = payload.get("commits", [])
        ref = payload.get("ref", "").replace("refs/heads/", "")
        msg = commits[0].get("message", "").split("\n")[0].strip() if commits else ""
        if msg:
            if len(msg) > 48:
                msg = msg[:45] + "..."
            return f"- `{date_tag}` · `PUSH` — {repo_link} · *\"{msg}\"*"
        if ref:
            return f"- `{date_tag}` · `PUSH` — {repo_link} (`{ref}`)"
        return f"- `{date_tag}` · `PUSH` — {repo_link}"

    elif etype == "WatchEvent":
        action = payload.get("action", "started")
        if action == "started":
            return f"- `{date_tag}` · `STAR` — {repo_link}"

    elif etype == "CreateEvent":
        ref_type = payload.get("ref_type", "repository")
        ref = payload.get("ref")
        if ref:
            return f"- `{date_tag}` · `CREATE` — {repo_link} (`{ref}`)"
        return f"- `{date_tag}` · `INIT` — Created {ref_type} {repo_link}"

    elif etype == "PullRequestEvent":
        action = payload.get("action", "opened").upper()
        pr = payload.get("pull_request", {})
        title = pr.get("title", "")
        pr_num = pr.get("number", "")
        pr_url = pr.get("html_url", repo_url)
        if len(title) > 42:
            title = title[:39] + "..."
        return f"- `{date_tag}` · `PR #{pr_num}` — [{title}]({pr_url}) in {repo_link}"

    elif etype == "IssuesEvent":
        issue = payload.get("issue", {})
        title = issue.get("title", "")
        issue_num = issue.get("number", "")
        issue_url = issue.get("html_url", repo_url)
        if len(title) > 42:
            title = title[:39] + "..."
        return f"- `{date_tag}` · `ISSUE #{issue_num}` — [{title}]({issue_url}) in {repo_link}"

    elif etype == "ReleaseEvent":
        tag = payload.get("release", {}).get("tag_name", "latest")
        return f"- `{date_tag}` · `RELEASE` — Published `{tag}` in {repo_link}"

    elif etype == "ForkEvent":
        forkee = payload.get("forkee", {}).get("full_name", "")
        if forkee:
            return f"- `{date_tag}` · `FORK` — {repo_link} → **[{forkee}](https://github.com/{forkee})**"

    return None


def update_readme(items):
    if not os.path.exists(README_PATH):
        print(f"[!] Error: README.md not found at {README_PATH}", file=sys.stderr)
        return False

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    section_pattern = re.compile(
        r"(<!-- START_SECTION:activity -->)(.*?)(<!-- END_SECTION:activity -->)",
        re.DOTALL,
    )

    if not section_pattern.search(content):
        print("[!] Warning: START_SECTION:activity tags not found in README.md", file=sys.stderr)
        return False

    rendered_list = "\n".join(items)
    new_section = f"\\1\n{rendered_list}\n\\3"
    updated_content = section_pattern.sub(new_section, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"[+] Successfully refreshed {len(items)} real-time GitHub activity entries in README.md")
    return True


def main():
    events = fetch_events()
    formatted = []
    if events:
        for ev in events:
            line = format_event(ev)
            if line and line not in formatted:
                formatted.append(line)
            if len(formatted) >= MAX_EVENTS:
                break

    if not formatted:
        print("[-] No events fetched or API unreachable; keeping existing telemetry block.")
        return

    update_readme(formatted)


if __name__ == "__main__":
    main()
