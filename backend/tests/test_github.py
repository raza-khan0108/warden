"""Tests the GitHub client against a fake transport — no network, no token,
safe to run in CI. httpx.MockTransport lets us script exact responses."""
import httpx
import pytest

from app.services.github import GitHubClient, GitHubError


def make_client(handler) -> GitHubClient:
    transport = httpx.MockTransport(handler)
    raw = httpx.Client(base_url="https://api.github.com", transport=transport)
    return GitHubClient(client=raw)


def test_get_repo_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World"
        return httpx.Response(200, json={"full_name": "octocat/Hello-World"})

    client = make_client(handler)
    assert client.get_repo("octocat/Hello-World")["full_name"] == "octocat/Hello-World"


def test_get_repo_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = make_client(handler)
    with pytest.raises(GitHubError) as exc:
        client.get_repo("octocat/does-not-exist")
    assert exc.value.status_code == 404


def test_get_repo_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={})

    client = make_client(handler)
    with pytest.raises(GitHubError) as exc:
        client.get_repo("octocat/Hello-World")
    assert exc.value.status_code == 403
    assert "rate limit" in exc.value.message


def test_get_tree_returns_entries_and_truncated_flag():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World/git/trees/main"
        assert request.url.params["recursive"] == "1"
        return httpx.Response(
            200,
            json={
                "tree": [{"path": "README.md", "type": "blob", "sha": "a" * 40, "size": 10}],
                "truncated": False,
            },
        )

    client = make_client(handler)
    entries, truncated = client.get_tree("octocat/Hello-World", "main")
    assert entries[0]["path"] == "README.md"
    assert truncated is False
