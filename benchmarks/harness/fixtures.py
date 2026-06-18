"""Fixture discovery/loading for phase-1 benchmark inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
DEFAULT_LOCK_PATH = Path(__file__).resolve().parents[1] / "fixtures.lock.json"
FIXTURE_ORDER = ("small", "medium", "large", "xlarge")


@dataclass(frozen=True)
class Fixture:
    name: str
    path: Path
    size_bytes: int
    sha256: str | None = None
    target_bytes: int | None = None

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()


@dataclass(frozen=True)
class FixtureSet:
    root: Path
    fixtures: tuple[Fixture, ...]

    def by_name(self, name: str) -> Fixture:
        for fixture in self.fixtures:
            if fixture.name == name:
                return fixture
        raise KeyError(name)


def load_fixture_set(
    root: Path | str = DEFAULT_FIXTURE_DIR,
    names: tuple[str, ...] = FIXTURE_ORDER,
    *,
    lock_path: Path | str | None = DEFAULT_LOCK_PATH,
    verify_hashes: bool = True,
) -> FixtureSet:
    """Load available benchmark fixtures in stable small→xlarge order.

    When ``verify_hashes`` is true, ``benchmarks/fixtures.lock.json`` is used to
    fail fast on stale or locally-mutated large fixtures before expensive runs.
    """

    fixture_root = Path(root)
    lock = _load_lock(Path(lock_path)) if lock_path is not None else {}
    fixtures: list[Fixture] = []
    missing: list[Path] = []
    for name in names:
        path = fixture_root / f"{name}.html"
        if not path.exists():
            missing.append(path)
            continue
        metadata = lock.get(name)
        size_bytes = path.stat().st_size
        if verify_hashes and metadata is not None:
            _verify_fixture(path, size_bytes, metadata)
        fixtures.append(
            Fixture(
                name=name,
                path=path,
                size_bytes=size_bytes,
                sha256=metadata.get("sha256") if metadata else None,
                target_bytes=metadata.get("target_bytes") if metadata else None,
            )
        )
    if missing and not fixtures:
        missing_list = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"no benchmark fixtures found under {fixture_root}; missing {missing_list}")
    return FixtureSet(root=fixture_root, fixtures=tuple(fixtures))


def _load_lock(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    entries: dict[str, dict[str, Any]] = {}
    for item in raw.get("fixtures", []):
        stem = Path(item["path"]).stem
        entries[stem] = item
    return entries


def _verify_fixture(path: Path, size_bytes: int, metadata: dict[str, Any]) -> None:
    expected_size = int(metadata["actual_bytes"])
    if size_bytes != expected_size:
        raise ValueError(f"fixture {path} size {size_bytes} != lock actual_bytes {expected_size}")
    expected_hash = str(metadata["sha256"])
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"fixture {path} sha256 {actual_hash} != lock sha256 {expected_hash}")
