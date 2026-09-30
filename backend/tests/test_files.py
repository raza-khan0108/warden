from app.services.files import detect_language, should_index


def test_should_index_accepts_normal_source_file():
    assert should_index("src/app.py", 1000)


def test_should_index_rejects_ignored_directory():
    assert not should_index("node_modules/x.js", 10)
    assert not should_index("frontend/.next/cache/x.js", 10)


def test_should_index_rejects_binary_extension():
    assert not should_index("assets/logo.png", 10)


def test_should_index_rejects_lockfile():
    assert not should_index("package-lock.json", 10)


def test_should_index_rejects_oversized_file():
    assert not should_index("big.py", 10_000_000)


def test_detect_language():
    assert detect_language("a/b.py") == "python"
    assert detect_language("x.tsx") == "typescript"
    assert detect_language("Makefile") is None
