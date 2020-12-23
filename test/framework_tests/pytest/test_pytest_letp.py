"""Test pytest letp plugin."""
import os
import pytest
from pytest_letp import get_git_info


@pytest.mark.parametrize(
    "repo_path, repo_name",
    [(os.path.dirname(os.path.abspath(__file__)), "LeTP"), ("INVALID_PATH", "")],
)
def test_get_version(repo_path, repo_name):
    """Test get git repo versions."""
    name, _ = get_git_info(repo_path)
    assert name == repo_name, "Did not find {}".format(repo_name)
