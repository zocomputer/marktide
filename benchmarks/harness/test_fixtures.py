from pathlib import Path

from benchmarks.harness.fixtures import load_fixture_set


def test_load_fixture_set_orders_available_sizes(tmp_path: Path):
    for name in ("medium", "small"):
        (tmp_path / f"{name}.html").write_text(f"<p>{name}</p>")
    fixtures = load_fixture_set(tmp_path, names=("small", "medium", "large"), lock_path=None)
    assert [f.name for f in fixtures.fixtures] == ["small", "medium"]
    assert fixtures.by_name("small").read_bytes() == b"<p>small</p>"


def test_load_fixture_set_verifies_lock_hash(tmp_path: Path):
    path = tmp_path / "small.html"
    path.write_text("<p>small</p>")
    import hashlib
    import json

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lock = tmp_path / "fixtures.lock.json"
    lock.write_text(json.dumps({"fixtures": [{"path": "benchmarks/fixtures/small.html", "actual_bytes": path.stat().st_size, "sha256": digest, "target_bytes": 1}]}))
    fixture = load_fixture_set(tmp_path, names=("small",), lock_path=lock).by_name("small")
    assert fixture.sha256 == digest

    path.write_text("<p>mutated</p>")
    import pytest
    with pytest.raises(ValueError, match="sha256|size"):
        load_fixture_set(tmp_path, names=("small",), lock_path=lock)


def test_load_fixture_set_requires_lockfile_when_verifying(tmp_path: Path):
    (tmp_path / "small.html").write_text("<p>small</p>")
    import pytest
    with pytest.raises(FileNotFoundError, match="fixture lockfile not found"):
        load_fixture_set(tmp_path, names=("small",), lock_path=tmp_path / "missing.lock.json")


def test_load_fixture_set_requires_lock_entry_when_verifying(tmp_path: Path):
    (tmp_path / "small.html").write_text("<p>small</p>")
    (tmp_path / "fixtures.lock.json").write_text('{"fixtures": []}')
    import pytest
    with pytest.raises(ValueError, match="no entry in lockfile"):
        load_fixture_set(tmp_path, names=("small",), lock_path=tmp_path / "fixtures.lock.json")
