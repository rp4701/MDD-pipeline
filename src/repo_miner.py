import os
import argparse
import pandas as pd
from github import Github, Auth

def fetch_commits(repo_full_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch commits from a GitHub repository.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set.")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_full_name)

    commits = []
    for i, commit in enumerate(repo.get_commits()):
        if max_commits and i >= max_commits:
            break
        commit_data = commit.commit
        commits.append({
            "sha": commit.sha,
            "author": commit_data.author.name if commit_data.author else None,
            "email": commit_data.author.email if commit_data.author else None,
            "date": commit_data.author.date.isoformat() if commit_data.author else None,
            "message": commit_data.message.splitlines()[0] if commit_data.message else None,
        })
    return pd.DataFrame(commits)


def fetch_issues(repo_full_name: str, state: str = "all", max_issues: int = None) -> pd.DataFrame:
    """
    Fetch issues from a GitHub repository.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set.")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_full_name)

    issues = []
    count = 0
    for issue in repo.get_issues(state=state):
        # Skip pull requests
        if issue.pull_request is not None:
            continue

        if max_issues and count >= max_issues:
            break

        created_at = issue.created_at
        closed_at = issue.closed_at

        issues.append({
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

    return pd.DataFrame(issues)


def main():
    parser = argparse.ArgumentParser(description="GitHub Repo Miner")
    subparsers = parser.add_subparsers(dest="command")

    # Fetch commits
    fetch_parser = subparsers.add_parser("fetch-commits")
    fetch_parser.add_argument("--repo", required=True)
    fetch_parser.add_argument("--max", type=int)
    fetch_parser.add_argument("--out", required=True)

    # Fetch issues
    issue_parser = subparsers.add_parser("fetch-issues")
    issue_parser.add_argument("--repo", required=True)
    issue_parser.add_argument("--state", choices=["all", "open", "closed"], default="all")
    issue_parser.add_argument("--max", type=int, dest="max_issues")
    issue_parser.add_argument("--out", required=True)

    args = parser.parse_args()

    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} commits to {args.out}")

    elif args.command == "fetch-issues":
        df = fetch_issues(args.repo, args.state, args.max_issues)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} issues to {args.out}")


if __name__ == "__main__":
    main()
