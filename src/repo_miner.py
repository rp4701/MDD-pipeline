import os
import argparse
from github import Github
import pandas as pd


def fetch_commits(repo_full_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch commits from a GitHub repository.

    Args:
        repo_full_name (str): Full repo name in "owner/repo" format.
        max_commits (int, optional): Maximum number of commits to fetch. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame with columns [sha, author, email, date, message].
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set.")

    gh = Github(token)
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


def main():
    parser = argparse.ArgumentParser(description="GitHub Repo Miner")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: fetch-commits
    fetch_parser = subparsers.add_parser("fetch-commits", help="Fetch commits from a repo")
    fetch_parser.add_argument("--repo", required=True, help="Repository in 'owner/repo' format")
    fetch_parser.add_argument("--max", type=int, help="Maximum number of commits to fetch")
    fetch_parser.add_argument("--out", required=True, help="Output CSV file path")

    args = parser.parse_args()

    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max)
        df.to_csv(args.out, index=False)
        print(f"✅ Saved {len(df)} commits to {args.out}")


if __name__ == "__main__":
    main()
