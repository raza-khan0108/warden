import httpx

from app.config import settings


class GitHubError(Exception):
    """Raised for any GitHub API failure. Carries an HTTP-style status_code
    so the API layer (Day 5) can translate it into the right response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = "", client: httpx.Client | None = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "warden",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # A client can be injected for testing (see tests/test_github.py);
        # otherwise we build a real one against the live API.
        self._client = client or httpx.Client(base_url=self.BASE_URL, headers=headers, timeout=30)

    def _get(self, path: str, **params) -> dict:
        try:
            res = self._client.get(path, params=params or None)
        except httpx.HTTPError as exc:
            raise GitHubError(502, f"GitHub unreachable: {exc}") from exc

        if res.status_code == 404:
            raise GitHubError(404, "Repository not found or token has no access")
        if res.status_code in (401, 403):
            remaining = res.headers.get("x-ratelimit-remaining")
            reason = "rate limit exceeded" if remaining == "0" else "bad or missing token"
            raise GitHubError(res.status_code, f"GitHub refused the request: {reason}")
        if res.status_code >= 400:
            raise GitHubError(502, f"GitHub error {res.status_code}")
        return res.json()

    def get_repo(self, full_name: str) -> dict:
        """GET /repos/{owner}/{repo} — metadata: default branch, description, etc."""
        return self._get(f"/repos/{full_name}")

    def get_tree(self, full_name: str, ref: str) -> tuple[list[dict], bool]:
        """GET /repos/{owner}/{repo}/git/trees/{ref}?recursive=1

        One call gets the whole file tree (GitHub allows up to ~100k entries
        / 7MB for recursive trees). Returns (entries, truncated) — if
        truncated is True, the repo is larger than that limit and a real
        implementation would need to walk subtrees individually.
        """
        data = self._get(f"/repos/{full_name}/git/trees/{ref}", recursive="1")
        return data.get("tree", []), bool(data.get("truncated", False))


def build_github_client() -> GitHubClient:
    """Factory used as a FastAPI dependency (see app/api/deps.py)."""
    return GitHubClient(token=settings.github_token)
