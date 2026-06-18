"""Config for the black-box E2E suite.

Registers the ``nightly`` marker and a ``--run-nightly`` flag. The large/xlarge
(50–110 MiB) fixture cases are marked ``nightly`` and **skipped unless ``--run-nightly``
is passed**, so PR CI never hangs on 100 MiB conversions; nightly / on-demand jobs opt in.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "nightly: heavy E2E over large/xlarge fixtures; only runs with --run-nightly",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-nightly",
        action="store_true",
        default=False,
        help="run nightly-marked heavy E2E tests (large/xlarge fixtures)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-nightly"):
        return
    skip_nightly = pytest.mark.skip(reason="heavy E2E; pass --run-nightly to run")
    for item in items:
        if "nightly" in item.keywords:
            item.add_marker(skip_nightly)
