#!/usr/bin/env python3
"""
AlkaidSTART — Unified Profile Telemetry & Content Synchronization Engine.

Zero external dependencies (Python 3 stdlib only).
Synchronizes:
  1. GitHub User & Repository metadata (GraphQL when GITHUB_TOKEN is set; public REST fallback)
  2. Real 371-day Contribution Calendar + Current/Longest Streak calculation
  3. Language byte distribution & UTC+8 Circadian Coding Rhythm
  4. Real-Time GitHub Public Activity Pulse -> <!-- START_SECTION:activity --> in README.md
  5. Latest Technical Articles from alkaid.live/blog/ -> <!-- START_SECTION:blog --> in README.md
  6. Regenerates all Dark & Light monochrome particle SVGs via scripts/generate_assets.py
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "profile.config.json"
CACHE_PATH = ROOT_DIR / "scripts" / ".telemetry-cache.json"
README_PATH = ROOT_DIR / "README.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_assets  # noqa: E402


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> str | None:
    hdrs = {"User-Agent": "AlkaidSTART-Profile-Engine/2.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"[!] GET {url} failed: {exc}", file=sys.stderr)
    return None


def github_headers() -> dict[str, str]:
    hdrs = {
        "User-Agent": "AlkaidSTART-Profile-Engine/2.0",
        "Accept": "application/vnd.github.v3+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    return hdrs


def fetch_github_graphql(username: str) -> dict[str, Any] | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None

    query = """
    query($login: String!) {
      user(login: $login) {
        followers { totalCount }
        following { totalCount }
        pullRequests { totalCount }
        issues { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes {
            name
            stargazerCount
            forkCount
            isFork
            primaryLanguage { name }
            languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name }
              }
            }
          }
        }
        allRepos: repositories(ownerAffiliations: OWNER) { totalCount }
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "AlkaidSTART-Profile-Engine/2.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "data" in data and data["data"].get("user"):
                return data["data"]["user"]
    except Exception as exc:
        print(f"[!] GraphQL query failed: {exc}", file=sys.stderr)
    return None


def fetch_contributions_html(username: str) -> tuple[int | None, list[dict[str, Any]]]:
    raw = http_get(f"https://github.com/users/{username}/contributions", timeout=15)
    if not raw:
        return None, []

    total_m = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", raw, re.I)
    yearly_total = int(total_m.group(1).replace(",", "")) if total_m else None

    day_matches = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="(contribution-day-component-\d+-\d+)"[^>]*data-level="(\d)"',
        raw,
    )
    tooltips = dict(re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]+)<', raw))

    days: list[dict[str, Any]] = []
    for date_s, cid, lv_s in day_matches:
        tip = tooltips.get(cid, "")
        cm = re.search(r"(\d+)\s+contribution", tip)
        count = int(cm.group(1)) if cm else (0 if lv_s == "0" else int(lv_s) * 5)
        days.append({"date": date_s, "level": int(lv_s), "count": count})

    days.sort(key=lambda d: d["date"])
    return yearly_total, days


def compute_streaks(days: list[dict[str, Any]]) -> tuple[int, int]:
    if not days:
        return 0, 0
    longest = 0
    running = 0
    for d in days:
        if d.get("count", 0) > 0 or d.get("level", 0) > 0:
            running += 1
            if running > longest:
                longest = running
        else:
            running = 0

    # Current streak: count backwards from today (allow today to be 0 if day isn't over)
    idx = len(days) - 1
    if idx >= 0 and days[idx].get("count", 0) == 0 and days[idx].get("level", 0) == 0:
        idx -= 1
    current = 0
    while idx >= 0 and (days[idx].get("count", 0) > 0 or days[idx].get("level", 0) > 0):
        current += 1
        idx -= 1
    return current, longest


def compute_rank(yearly_contrib: int, stars: int, prs: int, repos: int) -> str:
    score = yearly_contrib * 0.45 + stars * 3.5 + prs * 4.0 + repos * 2.0
    if score >= 2800:
        return "A+"
    if score >= 1400:
        return "A"
    if score >= 700:
        return "A-"
    return "B+"


def fetch_events_and_rhythm(username: str) -> tuple[list[str], list[int]]:
    raw = http_get(f"https://api.github.com/users/{username}/events/public?per_page=60", headers=github_headers())
    if not raw:
        return [], []
    try:
        events = json.loads(raw)
    except Exception:
        return [], []
    if not isinstance(events, list):
        return [], []

    # Guarantee strict reverse-chronological ordering across mixed event types
    events.sort(key=lambda ev: ev.get("created_at", ""), reverse=True)

    # Build UTC+8 circadian hourly histogram (blended gently with smooth baseline if sparse)
    hours = [0] * 24
    for ev in events:
        ts = ev.get("created_at", "")
        if len(ts) >= 19:
            try:
                utc_dt = dt.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
                cn_hour = (utc_dt.hour + 8) % 24
                hours[cn_hour] += 1
            except Exception:
                pass

    # Format clean editorial activity log entries
    formatted: list[str] = []
    seen_keys: set[str] = set()
    for ev in events:
        etype = ev.get("type", "")
        repo = ev.get("repo", {}).get("name", "")
        if not repo or repo.endswith("/AlkaidSTART"):
            # Keep activity stream focused on engineering repos (skip self-sync noise)
            continue
        repo_url = f"https://github.com/{repo}"
        repo_link = f"**[{repo}]({repo_url})**"
        created_at = ev.get("created_at", "")
        date_tag = created_at[:10].replace("-", ".") if len(created_at) >= 10 else "RECENT"
        payload = ev.get("payload", {})
        line = None
        dedupe_key = ""

        if etype == "PushEvent":
            commits = payload.get("commits", [])
            ref = payload.get("ref", "").replace("refs/heads/", "")
            msg = commits[0].get("message", "").split("\n")[0].strip() if commits else ""
            if msg:
                if len(msg) > 54:
                    msg = msg[:51] + "..."
                line = f"- `{date_tag}` · `PUSH` — {repo_link} · *{msg}*"
                dedupe_key = f"push:{repo}:{msg}"
            elif ref:
                line = f"- `{date_tag}` · `PUSH` — {repo_link} (`{ref}`)"
                dedupe_key = f"push:{repo}:{ref}:{date_tag}"
        elif etype == "PullRequestEvent":
            action = payload.get("action", "opened").lower()
            pr = payload.get("pull_request", {})
            merged = bool(pr.get("merged"))
            verb = "Merged" if (action == "closed" and merged) else action.capitalize()
            pr_num = pr.get("number") or payload.get("number", "")
            title = (pr.get("title") or "").strip()
            pr_url = pr.get("html_url") or (f"{repo_url}/pull/{pr_num}" if pr_num else repo_url)
            if not title:
                title = f"{verb} Pull Request #{pr_num}" if pr_num else f"{verb} Pull Request"
            elif len(title) > 48:
                title = title[:45] + "..."
            line = f"- `{date_tag}` · `PR #{pr_num}` — [{title}]({pr_url}) in {repo_link}"
            dedupe_key = f"pr:{repo}:{pr_num}"
        elif etype == "IssuesEvent":
            action = payload.get("action", "opened").lower()
            issue = payload.get("issue", {})
            inum = issue.get("number") or payload.get("number", "")
            title = (issue.get("title") or "").strip()
            iurl = issue.get("html_url") or (f"{repo_url}/issues/{inum}" if inum else repo_url)
            if not title:
                title = f"{action.capitalize()} Issue #{inum}" if inum else f"{action.capitalize()} Issue"
            elif len(title) > 48:
                title = title[:45] + "..."
            line = f"- `{date_tag}` · `ISSUE #{inum}` — [{title}]({iurl}) in {repo_link}"
            dedupe_key = f"issue:{repo}:{inum}"
        elif etype == "ReleaseEvent":
            tag = payload.get("release", {}).get("tag_name", "latest")
            line = f"- `{date_tag}` · `RELEASE` — Published `{tag}` in {repo_link}"
            dedupe_key = f"rel:{repo}:{tag}"
        elif etype == "CreateEvent":
            ref_type = payload.get("ref_type", "repository")
            ref = payload.get("ref")
            if ref_type == "repository":
                line = f"- `{date_tag}` · `INIT` — Created repository {repo_link}"
                dedupe_key = f"init:{repo}"
            elif ref:
                line = f"- `{date_tag}` · `BRANCH` — Created `{ref}` in {repo_link}"
                dedupe_key = f"branch:{repo}:{ref}"
        elif etype == "WatchEvent" and payload.get("action") == "started":
            line = f"- `{date_tag}` · `STAR` — Starred {repo_link}"
            dedupe_key = f"star:{repo}"

        if line and dedupe_key not in seen_keys:
            seen_keys.add(dedupe_key)
            formatted.append(line)
        if len(formatted) >= 6:
            break

    return formatted, hours


def fetch_alkaid_blog_posts(blog_index_url: str, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    raw = http_get(blog_index_url, timeout=12)
    if not raw:
        return fallback

    # Strip React SSR hydration comment nodes so dates & reading times parse cleanly
    clean_html = re.sub(r"<!--.*?-->", "", raw, flags=re.S)

    posts: list[dict[str, str]] = []
    # Parse <a ... href="/blog/...">Title</a> and nearby dates from SSR HTML
    for m in re.finditer(r'href="(/blog/[^"]+)"[^>]*>([^<]{4,140})</a>', clean_html):
        href, raw_title = m.group(1), html.unescape(m.group(2)).strip()
        if "sample-article" in href or "示例文章" in raw_title:
            continue
        full_url = f"https://alkaid.live{href}"
        if any(p["url"] == full_url for p in posts):
            continue
        ctx = clean_html[max(0, m.start() - 600) : m.start()]
        dm = re.findall(r"(\d{4})年(\d{1,2})月(\d{1,2})日", ctx)
        if dm:
            y, mo, d = dm[-1]
            date_s = f"{y}.{int(mo):02d}.{int(d):02d}"
        else:
            dm2 = re.findall(r"(\d{4}-\d{2}-\d{2})", ctx)
            date_s = dm2[-1].replace("-", ".") if dm2 else "2026"
        rm = re.findall(r"(\d+)\s*min read", ctx)
        read_min = rm[-1] if rm else ""
        # Match fallback summary if present
        summary = ""
        for fb in fallback:
            if fb["url"] == full_url or fb["title"][:12] == raw_title[:12]:
                summary = fb.get("summary", "")
                break
        posts.append(
            {
                "date": date_s,
                "readTime": f"{read_min} min" if read_min else "",
                "title": re.sub(r"\s+", " ", raw_title),
                "url": full_url,
                "summary": summary,
            }
        )
        if len(posts) >= 4:
            break

    return posts if posts else fallback


def replace_section(content: str, tag: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- START_SECTION:{tag} -->)(.*?)(<!-- END_SECTION:{tag} -->)", re.DOTALL)
    if not pattern.search(content):
        return content
    return pattern.sub(rf"\1\n{body}\n\3", content)


def sync_all() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    username = cfg["identity"]["username"]

    # Load previous cache or fallback baseline
    if CACHE_PATH.exists():
        telemetry = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    else:
        telemetry = dict(cfg["fallbackTelemetry"])
    telemetry.setdefault("repoMeta", {})

    # 1. Try GraphQL first (authoritative in GitHub Actions)
    gql = fetch_github_graphql(username)
    level_map = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }
    if gql:
        print("[+] Synced live metrics via GitHub GraphQL API")
        telemetry["followers"] = gql["followers"]["totalCount"]
        telemetry["following"] = gql["following"]["totalCount"]
        telemetry["totalPRs"] = gql["pullRequests"]["totalCount"]
        telemetry["totalIssues"] = gql["issues"]["totalCount"]
        telemetry["publicRepos"] = gql["allRepos"]["totalCount"]
        telemetry["originalRepos"] = gql["repositories"]["totalCount"]

        lang_bytes: dict[str, int] = {}
        total_stars = 0
        for node in gql["repositories"]["nodes"]:
            total_stars += node["stargazerCount"]
            telemetry["repoMeta"][node["name"]] = {
                "stars": node["stargazerCount"],
                "forks": node["forkCount"],
                "language": (node.get("primaryLanguage") or {}).get("name") or "TypeScript",
            }
            for edge in node["languages"]["edges"]:
                lname = edge["node"]["name"]
                lang_bytes[lname] = lang_bytes.get(lname, 0) + edge["size"]
        if total_stars > 0:
            telemetry["totalStars"] = max(total_stars, telemetry.get("totalStars", 0))
        if lang_bytes:
            tot_b = sum(lang_bytes.values()) or 1
            top_langs = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:8]
            telemetry["languages"] = [
                {"name": name, "percent": round(size * 100.0 / tot_b, 2)} for name, size in top_langs
            ]

        cal = gql["contributionsCollection"]["contributionCalendar"]
        telemetry["yearlyContributions"] = cal["totalContributions"]
        telemetry["totalContributions"] = max(cal["totalContributions"], telemetry.get("totalContributions", 0))
        days = []
        for week in cal["weeks"]:
            for d in week["contributionDays"]:
                days.append(
                    {
                        "date": d["date"],
                        "count": d["contributionCount"],
                        "level": level_map.get(d["contributionLevel"], 0),
                    }
                )
        telemetry["contributionDays"] = days
        cur_s, max_s = compute_streaks(days)
        if max_s > 0:
            telemetry["currentStreak"] = cur_s
            telemetry["longestStreak"] = max(max_s, telemetry.get("longestStreak", 0))
    else:
        # 2. Public REST + Contributions HTML fallback (zero token required!)
        user_raw = http_get(f"https://api.github.com/users/{username}", headers=github_headers())
        if user_raw:
            u = json.loads(user_raw)
            telemetry["publicRepos"] = u.get("public_repos", telemetry.get("publicRepos", 74))
            telemetry["followers"] = u.get("followers", telemetry.get("followers", 10))
            telemetry["following"] = u.get("following", telemetry.get("following", 28))

        repos_raw = http_get(
            f"https://api.github.com/users/{username}/repos?per_page=100&sort=pushed", headers=github_headers()
        )
        if repos_raw:
            repos = json.loads(repos_raw)
            if isinstance(repos, list) and repos:
                telemetry["originalRepos"] = sum(1 for r in repos if not r.get("fork"))
                telemetry["totalStars"] = sum(int(r.get("stargazers_count", 0)) for r in repos)
                for r in repos:
                    telemetry["repoMeta"][r["name"]] = {
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "language": r.get("language") or "TypeScript",
                    }

        yr_total, days = fetch_contributions_html(username)
        if days:
            telemetry["contributionDays"] = days
            if yr_total is not None:
                telemetry["yearlyContributions"] = yr_total
                telemetry["totalContributions"] = max(yr_total, telemetry.get("totalContributions", 0))
            cur_s, max_s = compute_streaks(days)
            if max_s > 0:
                telemetry["currentStreak"] = cur_s
                telemetry["longestStreak"] = max(max_s, telemetry.get("longestStreak", 0))
            print(f"[+] Parsed {len(days)} live contribution days (yearly={yr_total}, streak={cur_s}d/{max_s}d)")

    # 3. Real-Time Events & Circadian Rhythm
    activity_lines, hours = fetch_events_and_rhythm(username)
    if sum(hours) >= 12:
        # Blend real recent hourly pulses with smooth circadian curve so 24h waveform stays balanced
        base = [14, 10, 5, 2, 1, 1, 3, 7, 14, 24, 34, 38, 28, 32, 42, 46, 48, 40, 36, 44, 52, 56, 46, 28]
        telemetry["hourlyRhythm"] = [base[i] + hours[i] * 8 for i in range(24)]

    telemetry["rank"] = compute_rank(
        telemetry.get("yearlyContributions", 2816),
        telemetry.get("totalStars", 155),
        telemetry.get("totalPRs", 157),
        telemetry.get("publicRepos", 74),
    )
    telemetry["updatedAt"] = dt.datetime.now(dt.timezone.utc).strftime("%Y.%m.%d")

    # Persist cache for deterministic local runs
    CACHE_PATH.write_text(json.dumps(telemetry, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4. Sync alkaid.live Technical Writing
    blog_posts = fetch_alkaid_blog_posts(cfg["identity"]["blogIndexUrl"], cfg["fallbackBlogPosts"])

    # 5. Update README.md dynamic blocks
    if README_PATH.exists():
        readme = README_PATH.read_text(encoding="utf-8")
        if activity_lines:
            readme = replace_section(readme, "activity", "\n".join(activity_lines))
        if blog_posts:
            blog_md = "\n".join(
                f"- `{p['date']}` — **[{p['title']}]({p['url']})**"
                + (f" <sub>`{p['readTime']}`</sub>" if p.get("readTime") else "")
                + (f"<br/><sub>{p['summary']}</sub>" if p.get("summary") else "")
                for p in blog_posts
            )
            readme = replace_section(readme, "blog", blog_md)
        README_PATH.write_text(readme, encoding="utf-8")
        print(f"[+] Updated README.md ({len(activity_lines)} activity lines, {len(blog_posts)} blog posts)")

    # 6. Regenerate all Dark & Light animated particle SVGs
    written = generate_assets.generate_all(telemetry)
    total_kb = sum(p.stat().st_size for p in written) / 1024.0
    print(f"[+] Regenerated {len(written)} monochrome SVGs ({total_kb:.1f} KB total)")


if __name__ == "__main__":
    sync_all()
