# tests/test_repo.py

import sys
import os
import pytest
import pandas as pd
import vcr

# Add src folder to sys.path so imports work on CI and Windows
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from repo_miner import fetch_commits, fetch_issues


my_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes",  # folder to store API recordings
    record_mode="once",  # record once, replay later
    match_on=["uri", "method"],
)


# ---------- Commit Tests ----------
@my_vcr.use_cassette("test_fetch_commits.yaml")
def test_fetch_commits_basic():
    df = fetch_commits("octocat/Hello-World", max_commits=5)
    assert not df.empty
    assert "sha" in df.columns
    assert len(df) <= 5


@my_vcr.use_cassette("test_fetch_commits_limit.yaml")
def test_fetch_commits_limit():
    df = fetch_commits("octocat/Hello-World", max_commits=3)
    assert len(df) == 3


# ---------- Issue Tests ----------
@my_vcr.use_cassette("test_fetch_issues.yaml")
def test_fetch_issues_basic():
    df = fetch_issues("octocat/Hello-World", state="all", max_issues=5)
    assert not df.empty
    # Check required columns exist
    for col in [
        "id", "number", "title", "user",
        "state", "created_at", "closed_at",
        "comments", "open_duration_days"
    ]:
        assert col in df.columns
    assert len(df) <= 5

    # Check ISO-8601 format for created_at
    assert all(df["created_at"].dropna().str.match(r"\d{4}-\d{2}-\d{2}T"))

    # Check open_duration_days is either int or None
    assert all((pd.isna(v) or isinstance(v, (int, float))) for v in df["open_duration_days"])


@my_vcr.use_cassette("test_fetch_issues_open.yaml")
def test_fetch_issues_open_state():
    df = fetch_issues("octocat/Hello-World", state="open", max_issues=3)
    # Ensure all returned issues are open
    assert all(df["state"] == "open")
    assert len(df) <= 3



@my_vcr.use_cassette("test_fetch_issues_excludes_prs.yaml")
def test_fetch_issues_excludes_prs():
    df = fetch_issues("octocat/Hello-World", state="all", max_issues=10)
    assert not df.empty

    # None of the rows should have PR-specific data
    # Since we skip pull requests, this ensures only issues remain
    # (a PR in GitHub API includes 'pull_request' key, but our DataFrame skips those)
    assert "pull_request" not in df.columns


@my_vcr.use_cassette("test_fetch_issues_dates.yaml")
def test_fetch_issues_dates():
    df = fetch_issues("octocat/Hello-World", state="all", max_issues=5)

    # created_at must be ISO-8601
    assert df["created_at"].notnull().all()
    assert df["created_at"].str.match(r"\d{4}-\d{2}-\d{2}T").all()

    # closed_at (when present) must also be ISO-8601
    closed = df["closed_at"].dropna()
    if not closed.empty:
        assert closed.str.match(r"\d{4}-\d{2}-\d{2}T").all()


@my_vcr.use_cassette("test_fetch_issues_duration.yaml")
def test_fetch_issues_duration():
    df = fetch_issues("octocat/Hello-World", state="closed", max_issues=3)

    for _, row in df.iterrows():
        if row["created_at"] and row["closed_at"]:
            created = pd.to_datetime(row["created_at"])
            closed = pd.to_datetime(row["closed_at"])
            expected_days = (closed - created).days
            assert row["open_duration_days"] == expected_days
