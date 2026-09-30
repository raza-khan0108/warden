from pathlib import PurePosixPath

MAX_FILE_SIZE = 500_000  # bytes; larger files are skipped (binaries, bundles, etc.)

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "vendor", "__pycache__",
    ".next", ".venv", "venv", "target", "coverage", ".idea", ".vscode",
}

IGNORED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Cargo.lock", "composer.lock", "Gemfile.lock",
}

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf",
    ".zip", ".tar", ".gz", ".jar", ".class", ".pyc", ".so", ".dll", ".exe",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".mov", ".min.js", ".map",
}

LANGUAGES = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".h": "c",
    ".dart": "dart", ".kt": "kotlin", ".swift": "swift",
    ".abap": "abap", ".sql": "sql", ".sh": "shell",
    ".md": "markdown", ".json": "json", ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml", ".html": "html", ".css": "css",
}


def should_index(path: str, size: int) -> bool:
    """Decide whether a file from GitHub's tree is worth indexing at all."""
    p = PurePosixPath(path)

    if size > MAX_FILE_SIZE:
        return False
    # any parent directory in the path being "ignored" excludes the file
    if any(part in IGNORED_DIRS for part in p.parts[:-1]):
        return False
    if p.name in IGNORED_NAMES:
        return False

    name = p.name.lower()
    return not any(name.endswith(ext) for ext in IGNORED_EXTENSIONS)


def detect_language(path: str) -> str | None:
    return LANGUAGES.get(PurePosixPath(path).suffix.lower())
