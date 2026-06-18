from pathlib import Path

from benchmarks.harness.fixtures import load_fixture_set


def test_load_fixture_set_orders_available_sizes(tmp_path: Path):
    for name in ("medium", "small"):
        (tmp_path / f"{name}.html").write_text(f"<p>{name}</p>")
    fixtures = load_fixture_set(tmp_path, names=("small", "medium", "large"))
    assert [f.name for f in fixtures.fixtures] == ["small", "medium"]
    assert fixtures.by_name("small").read_bytes() == b"<p>small</p>"
