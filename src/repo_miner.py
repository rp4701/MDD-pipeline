#!/usr/bin/env python3
"""
repo_miner.py

A command-line tool to:
  1) Fetch and normalize commit data from GitHub
  2) Fetch and normalize issue data from GitHub
  3) Merge and summarize data

Sub-commands:
  - fetch-commits
  - fetch-issues
  - summarize
"""

import os
import argparse
import pandas as pd
from github import Github, Auth
from datetime import datetime

# ------------------ FETCH COMMITS ------------------
def fetch_commits(repo_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_commits` commits from a GitHub repository.
    Returns a DataFrame with columns: sha, author, email, date, message.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("❌ GITHUB_TOKEN environment variable not set.")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)

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
        raise EnvironmentError("❌ GITHUB_TOKEN environment variable not set.")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)

    records = []
    count = 0

    for issue in repo.get_issues(state=state):
        # skip pull requests
        if hasattr(issue, "pull_request") and issue.pull_request is not None:
            continue

        if max_issues and count >= max_issues:
            break

        created_at = issue.created_at
        closed_at = issue.closed_at

        # Compute open duration
        open_duration = None
        if created_at and closed_at:
            open_duration = (closed_at - created_at).days

        records.append({
            "id": issue.id,
            "number": issue.number,
            "title": issue.title,
            "user": issue.user.login if issue.user else None,
            "state": issue.state,
            "created_at": created_at.isoformat() if created_at else None,
            "closed_at": closed_at.isoformat() if closed_at else None,
            "comments": issue.comments,
            "open_duration_days": open_duration,
        })

        count += 1

    # Ensure column always exists even if empty
    df = pd.DataFrame(records, columns=[
        "id", "number", "title", "user", "state",
        "created_at", "closed_at", "comments", "open_duration_days"
    ])
    return df


# ------------------ MERGE & SUMMARIZE ------------------
def merge_and_summarize(commits_df: pd.DataFrame, issues_df: pd.DataFrame) -> None:
    """
    Takes two DataFrames (commits and issues) and prints:
      - Top 5 committers by commit count
      - Issue close rate (closed/total)
      - Average open duration for closed issues (in days)
    """
    commits_df = commits_df.copy()
    issues_df = issues_df.copy()

    commits_df["date"] = pd.to_datetime(commits_df["date"], errors="coerce")
    issues_df["created_at"] = pd.to_datetime(issues_df["created_at"], errors="coerce")
    issues_df["closed_at"] = pd.to_datetime(issues_df["closed_at"], errors="coerce")

    print("=== Repository Summary ===")

    # Top 5 committers
    top_committers = commits_df["author"].value_counts().head(5)
    print("\nTop 5 committers:")
    for name, count in top_committers.items():
        print(f"  {name}: {count} commits")

    # Issue close rate
    total_issues = len(issues_df)
    closed_issues = (issues_df["state"] == "closed").sum()
    close_rate = closed_issues / total_issues if total_issues > 0 else 0
    print(f"\nIssue close rate: {close_rate:.2f}")

    # Average open duration
    closed_df = issues_df.dropna(subset=["closed_at", "created_at"]).copy()
    if not closed_df.empty:
        closed_df["duration_days"] = (closed_df["closed_at"] - closed_df["created_at"]).dt.total_seconds() / 86400
        avg_duration = closed_df["duration_days"].mean()
        print(f"Avg. issue open duration: {avg_duration:.2f} days")
    else:
        print("Avg. issue open duration: N/A (no closed issues)")

    print("===========================")


# ------------------ MAIN CLI ------------------
def main():
    parser = argparse.ArgumentParser(
        prog="repo_miner",
        description="Fetch GitHub commits/issues and summarize them"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch-commits
    c1 = subparsers.add_parser("fetch-commits", help="Fetch commits and save to CSV")
    c1.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c1.add_argument("--max", type=int, dest="max_commits", help="Max number of commits to fetch")
    c1.add_argument("--out", required=True, help="Path to output commits CSV")

    # fetch-issues
    c2 = subparsers.add_parser("fetch-issues", help="Fetch issues and save to CSV")
    c2.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c2.add_argument("--state", choices=["all", "open", "closed"], default="all", help="Issue state filter")
    c2.add_argument("--max", type=int, dest="max_issues", help="Max number of issues to fetch")
    c2.add_argument("--out", required=True, help="Path to output issues CSV")

    # summarize
    c3 = subparsers.add_parser("summarize", help="Summarize commits and issues")
    c3.add_argument("--commits", required=True, help="Path to commits CSV file")
    c3.add_argument("--issues", required=True, help="Path to issues CSV file")

    args = parser.parse_args()

    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max_commits)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} commits to {args.out}")

    elif args.command == "fetch-issues":
        df = fetch_issues(args.repo, args.state, args.max_issues)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} issues to {args.out}")

    elif args.command == "summarize":
        commits_df = pd.read_csv(args.commits)
        issues_df = pd.read_csv(args.issues)
        merge_and_summarize(commits_df, issues_df)


if __name__ == "__main__":
    main()
