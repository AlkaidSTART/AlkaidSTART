#!/usr/bin/env python3
"""
Fetch recent public events for AlkaidSTART from the GitHub REST API
and update the <!-- START_SECTION:activity --> block in README.md.
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
MAX_EVENTS = 6

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
    
    if etype == "PushEvent":
        commits = event.get("payload", {}).get("commits", [])
        count = len(commits)
        msg = commits[0].get("message", "").split("\n")[0] if commits else ""
        if msg:
            if len(msg) > 50:
                msg = msg[:47] + "..."
            return f"- 🔨 推送了 {count} 次提交至 {repo_link} ── *\"{msg}\"*"
        return f"- 🔨 推送了 {count} 次提交至 {repo_link}"
    elif etype == "WatchEvent":
        action = event.get("payload", {}).get("action", "started")
        if action == "started":
            return f"- ⭐ Star 收藏了开源项目 {repo_link}"
    elif etype == "CreateEvent":
        ref_type = event.get("payload", {}).get("ref_type", "repo")
        ref = event.get("payload", {}).get("ref")
        if ref:
            return f"- ✨ 创建了分支/标签 `{ref}` 于 {repo_link}"
        return f"- 📦 创建了新仓库 {repo_link}"
    elif etype == "PullRequestEvent":
        action = event.get("payload", {}).get("action", "opened")
        pr = event.get("payload", {}).get("pull_request", {})
        title = pr.get("title", "")
        pr_num = pr.get("number", "")
        pr_url = pr.get("html_url", repo_url)
        if len(title) > 40:
            title = title[:37] + "..."
        return f"- 🔀 {action.capitalize()} PR [#{pr_num} {title}]({pr_url}) 于 {repo_link}"
    elif etype == "IssuesEvent":
        action = event.get("payload", {}).get("action", "opened")
        issue = event.get("payload", {}).get("issue", {})
        title = issue.get("title", "")
        issue_num = issue.get("number", "")
        issue_url = issue.get("html_url", repo_url)
        if len(title) > 40:
            title = title[:37] + "..."
        return f"- 💬 {action.capitalize()} Issue [#{issue_num} {title}]({issue_url}) 于 {repo_link}"
    elif etype == "ReleaseEvent":
        tag = event.get("payload", {}).get("release", {}).get("tag_name", "")
        return f"- 🏷️ 带来了新版本发布 `{tag}` 于 {repo_link}"
    elif etype == "ForkEvent":
        forkee = event.get("payload", {}).get("forkee", {}).get("full_name", "")
        return f"- 🍴 Fork 了仓库 {repo_link} 到 **[{forkee}](https://github.com/{forkee})**"
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
        print("[-] No events fetched or API unreachable; using resilient fallback telemetry markers.")
        return

    update_readme(formatted)

if __name__ == "__main__":
    main()
