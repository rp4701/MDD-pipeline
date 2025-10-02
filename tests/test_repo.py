# tests/test_repo.py

import sys
import os
import pytest
import pandas as pd
from datetime import datetime, timedelta

# Add src/ to sys.path so Python can find repo_miner.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import repo_miner
from repo_miner import fetch_commits, fetch_issues

# --- Dummy Classes to Simulate GitHub API ---

class DummyAuthor:
    def __init__(self, name, email, date):
        self.name = name
        self.email = email
        self.date = date

class DummyCommitCommit:
    def __init__(self, author, message):
        self.author = author
        self.message = message

class DummyCommit:
    def __init__(self, sha, author, email, date, message):
        self.sha = sha
        self.commit = DummyCommitCommit(DummyAuthor(author, email, date), message)

class DummyUser:
    def __init__(self, login):
        self.login = login

class DummyIssue:
    def __init__(self, id_, number, title, user, state, created_at, closed_at, comments, is_pr=False):
        self.id = id_
        self.number = number
        self.title = title
        self.user = DummyUser(user)
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.comments = comments
        if is_pr:
            self.pull_request = {"url": "dummy_pr_url"}

class DummyRepo:
    def __init__(self, commits=None, issues=None):
        self._commits = commits or []
        self._issues = issues or []

    def get_commits(self):
        return self._commits

    def get_issues(self, state="all"):
        if state == "all":
            return self._issues
        return [i for i in self._issues if i.state == state]

class DummyGithub:
    def __init__(self, token):
        assert token == "fake-token"
    def get_repo(self, repo_name):
        return self._repo

# Shared dummy GH instance
gh_instance = DummyGithub("fake-token")

# Patch environment variable and Github class in repo_miner
@pytest.fixture(autouse=True)
def patch_env_and_github(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    
    def dummy_github(*args, **kwargs):
        return gh_instance

    monkeypatch.setattr(repo_miner, "Github", dummy_github)


# ---------- Commit Tests ----------

def test_fetch_commits_basic():
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Alice", "a@example.com", now, "Initial commit\nDetails"),
        DummyCommit("sha2", "Bob", "b@example.com", now - timedelta(days=1), "Bug fix")
    ]
    gh_instance._repo = DummyRepo(commits=commits)
    df = fetch_commits("any/repo", max_commits=5)
    assert not df.empty
    assert "sha" in df.columns
    assert len(df) <= 5

def test_fetch_commits_limit():
    now = datetime.now()
    commits = [DummyCommit(f"sha{i}", "Dev", "d@example.com", now, f"Commit {i}") for i in range(10)]
    gh_instance._repo = DummyRepo(commits=commits)
    df = fetch_commits("any/repo", max_commits=3)
    assert len(df) == 3

def test_fetch_commits_empty():
    gh_instance._repo = DummyRepo(commits=[])
    df = fetch_commits("any/repo")
    assert df.empty

# ---------- Issue Tests ----------

def test_fetch_issues_basic():
    now = datetime.now()
    issues = [
        DummyIssue(1, 101, "Issue A", "alice", "open", now, None, 2),
        DummyIssue(2, 102, "Issue B", "bob", "closed", now - timedelta(days=5), now, 1),
    ]
    gh_instance._repo = DummyRepo(issues=issues)
    df = fetch_issues("any/repo", state="all", max_issues=5)
    assert not df.empty
    for col in ["id", "number", "title", "user", "state", "created_at", "closed_at", "comments", "open_duration_days"]:
        assert col in df.columns
    assert all(df["created_at"].dropna().str.match(r"\d{4}-\d{2}-\d{2}T"))
    assert all((pd.isna(v) or isinstance(v, (int, float))) for v in df["open_duration_days"])

def test_fetch_issues_open_state():
    now = datetime.now()
    issues = [
        DummyIssue(3, 201, "Open 1", "alice", "open", now, None, 0),
        DummyIssue(4, 202, "Open 2", "bob", "open", now, None, 0),
    ]
    gh_instance._repo = DummyRepo(issues=issues)
    df = fetch_issues("any/repo", state="open", max_issues=3)
    assert all(df["state"] == "open")
    assert len(df) <= 3

def test_fetch_issues_excludes_prs():
    now = datetime.now()
    issues = [
        DummyIssue(5, 301, "Real Issue", "alice", "open", now, None, 1),
        DummyIssue(6, 302, "PR disguised", "bob", "closed", now, now, 0, is_pr=True),
    ]
    gh_instance._repo = DummyRepo(issues=issues)
    df = fetch_issues("any/repo", state="all", max_issues=10)
    assert not df.empty
    assert "pull_request" not in df.columns

def test_fetch_issues_dates_and_duration():
    now = datetime.now()
    issues = [
        DummyIssue(7, 401, "Closed Issue", "alice", "closed", now - timedelta(days=2), now, 1),
        DummyIssue(8, 501, "Closed Duration", "bob", "closed", now - timedelta(days=10), now, 2),
    ]
    gh_instance._repo = DummyRepo(issues=issues)
    df = fetch_issues("any/repo", state="all", max_issues=5)
    
    # Dates
    assert df["created_at"].notnull().all()
    assert df["created_at"].str.match(r"\d{4}-\d{2}-\d{2}T").all()
    
    closed = df["closed_at"].dropna()
    if not closed.empty:
        assert closed.str.match(r"\d{4}-\d{2}-\d{2}T").all()
    
    # Duration check
    for _, row in df.iterrows():
        if row["created_at"] and row["closed_at"]:
            created = pd.to_datetime(row["created_at"])
            closed = pd.to_datetime(row["closed_at"])
            expected_days = (closed - created).days
            assert row["open_duration_days"] == expected_days
