# tests/test_repo.py

import os
import pytest
import vcr
from src.repo_miner import fetch_commits

# Make sure you set your GITHUB_TOKEN in environment variables before running tests

my_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes",  # folder to store API recordings
    record_mode="once",  # record once, replay later
    match_on=["uri", "method"],
)


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
