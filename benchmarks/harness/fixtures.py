"""Fixture discovery/loading for phase-1 benchmark inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_ORDER = ("small", "medium", "large", "xlarge")


@dataclass(frozen=True)
class Fixture:
    name: str
    path: Path
    size_bytes: int

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


def load_fixture_set(root: Path | str = DEFAULT_FIXTURE_DIR, names: tuple[str, ...] = FIXTURE_ORDER) -> FixtureSet:
    """Load available benchmark fixtures in stable small→xlarge order."""

    fixture_root = Path(root)
    fixtures: list[Fixture] = []
    missing: list[Path] = []
    for name in names:
        path = fixture_root / f"{name}.html"
        if not path.exists():
            missing.append(path)
            continue
        fixtures.append(Fixture(name=name, path=path, size_bytes=path.stat().st_size))
    if missing and not fixtures:
        missing_list = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"no benchmark fixtures found under {fixture_root}; missing {missing_list}")
    return FixtureSet(root=fixture_root, fixtures=tuple(fixtures))
