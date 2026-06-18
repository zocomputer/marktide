import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "regenerate_conformance_corpus.py"
spec = importlib.util.spec_from_file_location("regenerate_conformance_corpus", SCRIPT_PATH)
assert spec is not None
regenerate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = regenerate
spec.loader.exec_module(regenerate)


def test_load_manifest_uses_sources_toml_as_single_source_of_truth(tmp_path: Path):
    manifest = tmp_path / "sources.toml"
    manifest.write_text(
        """
        [corpus]
        fixture_root = "tests/conformance/fixtures"
        lockfile = "tests/conformance/fixtures.lock.json"

        [sources.example_source]
        name = "Display Name Is Not The Fixture Directory"
        url = "https://example.com/repo.git"
        commit = "0123456789abcdef0123456789abcdef01234567"
        fixture_path = "tests/conformance/fixtures/example-fixture"
        selected_paths = ["tests/case.html", "LICENSE"]
        """,
        encoding="utf-8",
    )

    fixture_root, lock_path, sources = regenerate.load_manifest(manifest)

    assert fixture_root == regenerate.REPO_ROOT / "tests" / "conformance" / "fixtures"
    assert lock_path == regenerate.REPO_ROOT / "tests" / "conformance" / "fixtures.lock.json"
    assert sources == (
        regenerate.Source(
            name="example-fixture",
            url="https://example.com/repo.git",
            commit="0123456789abcdef0123456789abcdef01234567",
            paths=("tests/case.html", "LICENSE"),
        ),
    )


def test_load_manifest_rejects_missing_selected_paths(tmp_path: Path):
    manifest = tmp_path / "sources.toml"
    manifest.write_text(
        """
        [corpus]
        fixture_root = "tests/conformance/fixtures"
        lockfile = "tests/conformance/fixtures.lock.json"

        [sources.bad]
        url = "https://example.com/repo.git"
        commit = "0123456789abcdef0123456789abcdef01234567"
        fixture_path = "tests/conformance/fixtures/bad"
        """,
        encoding="utf-8",
    )

    try:
        regenerate.load_manifest(manifest)
    except ValueError as exc:
        assert "sources.bad.selected_paths" in str(exc)
    else:
        raise AssertionError("expected ValueError")
