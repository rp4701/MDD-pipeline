#!/usr/bin/env python3
"""
repo_miner.py

A command-line tool to:
  1) Fetch and normalize commit data from GitHub
  2) Fetch and normalize issue data from GitHub

Sub-commands:
  - fetch-commits
  - fetch-issues
"""

import os
import argparse
import pandas as pd
from github import Github, Auth
from datetime import datetime

# ------------------ FETCH COMMITS ------------------
def fetch_commits(repo_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_commits` from the specified GitHub repository.
    Returns a DataFrame with columns: sha, author, email, date, message.
    """
    # 1) Read GitHub token from environment
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set.")

    # 2) Initialize GitHub client and get the repo
    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)

    # 3) Fetch commit objects
    records = []
    for i, commit in enumerate(repo.get_commits()):
        if max_commits and i >= max_commits:
            break
        c = commit.commit
        records.append({
            "sha": commit.sha,
            "author": c.author.name if c.author else None,
            "email": c.author.email if c.author else None,
            "date": c.author.date.isoformat() if c.author else None,
            "message": c.message.splitlines()[0] if c.message else None,
        })

    # 4) Build DataFrame
    return pd.DataFrame(records)


# ------------------ FETCH ISSUES ------------------
def fetch_issues(repo_name: str, state: str = "all", max_issues: int = None) -> pd.DataFrame:
    """
    Fetch GitHub issues (excluding PRs) with optional state and limit.
    Returns a DataFrame with columns:
      id, number, title, user, state, created_at, closed_at, comments, open_duration_days
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set.")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)

    records = []
    count = 0
    for issue in repo.get_issues(state=state):
        # Skip pull requests
        if hasattr(issue, "pull_request") and issue.pull_request is not None:
            continue

        if max_issues and count >= max_issues:
            break

        created_at = issue.created_at
        closed_at = issue.closed_at

        records.append({
            "id": issue.id,
            "number": issue.number,
            "title": issue.title,
            "user": issue.user.login if issue.user else None,
            "state": issue.state,
            "created_at": created_at.isoformat() if created_at else None,
            "closed_at": closed_at.isoformat() if closed_at else None,
            "comments": issue.comments,
            "open_duration_days": (closed_at - created_at).days if closed_at and created_at else None,
        })
        count += 1

    return pd.DataFrame(records)


# ------------------ MAIN CLI ------------------
def main():
    """
    Parse command-line arguments and dispatch to sub-commands.
    """
    parser = argparse.ArgumentParser(
        prog="repo_miner",
        description="Fetch GitHub commits/issues and summarize them"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sub-command: fetch-commits
    c1 = subparsers.add_parser("fetch-commits", help="Fetch commits and save to CSV")
    c1.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c1.add_argument("--max", type=int, dest="max_commits",
                    help="Max number of commits to fetch")
    c1.add_argument("--out", required=True, help="Path to output commits CSV")

    # Sub-command: fetch-issues
    c2 = subparsers.add_parser("fetch-issues", help="Fetch issues and save to CSV")
    c2.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c2.add_argument("--state", choices=["all", "open", "closed"], default="all",
                    help="Issue state filter")
    c2.add_argument("--max", type=int, dest="max_issues", help="Max number of issues to fetch")
    c2.add_argument("--out", required=True, help="Path to output issues CSV")

    args = parser.parse_args()

    # Dispatch commands
    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max_commits)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} commits to {args.out}")

    elif args.command == "fetch-issues":
        df = fetch_issues(args.repo, args.state, args.max_issues)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} issues to {args.out}")


if __name__ == "__main__":
    main()
