from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    from .charts import CHART_FILENAMES, generate_charts
except ImportError:  # Allows `cd benchmarks && uv run pytest`.
    from charts import CHART_FILENAMES, generate_charts


class _FakeFigure:
    def tight_layout(self):
        return None

    def savefig(self, path: Path, dpi: int):
        path.write_bytes(b"fake-png")


class _FakeAxes:
    def bar(self, *args, **kwargs):
        return None

    def plot(self, *args, **kwargs):
        return None

    def set_title(self, *args, **kwargs):
        return None

    def set_ylabel(self, *args, **kwargs):
        return None

    def set_xlabel(self, *args, **kwargs):
        return None

    def set_xticks(self, *args, **kwargs):
        return None

    def set_xticklabels(self, *args, **kwargs):
        return None

    def grid(self, *args, **kwargs):
        return None

    def legend(self, *args, **kwargs):
        return None

    def twinx(self):
        return _FakeAxes()

    def text(self, *args, **kwargs):
        return None

    def set_axis_off(self):
        return None


class _FakePyplot(types.ModuleType):
    def subplots(self, *args, **kwargs):
        return _FakeFigure(), _FakeAxes()

    def close(self, *args, **kwargs):
        return None


def _install_fake_matplotlib(monkeypatch):
    fake_matplotlib = types.ModuleType("matplotlib")
    fake_matplotlib.use = lambda backend: None
    fake_pyplot = _FakePyplot("matplotlib.pyplot")
    monkeypatch.setitem(sys.modules, "matplotlib", fake_matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_pyplot)


def test_generate_charts_from_synthetic_phase3_json(tmp_path, monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    phase3 = tmp_path / "phase3.json"
    phase3.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "adapter": "markdownify",
                        "fixture": "small",
                        "status": "ok",
                        "throughput_mib_s": 5.0,
                        "input_bytes": 100,
                        "peak_rss_delta_bytes": 300,
                        "output_to_input_ratio": 1.0,
                        "async_gate": {"max_delay_ms": 20, "missed_beat_pct": 50},
                    },
                    {
                        "adapter": "html2md_streaming",
                        "fixture": "small",
                        "status": "ok",
                        "throughput_mib_s": 50.0,
                        "input_bytes": 100,
                        "peak_rss_delta_bytes": 20,
                        "output_to_input_ratio": 1.0,
                        "async_gate": {"max_delay_ms": 2, "missed_beat_pct": 0},
                        "streaming_cadence": {
                            "first_chunk_s": 0.005,
                            "max_inter_chunk_gap_s": None,
                            "chunk_count": 1,
                        },
                    },
                ]
            }
        )
    )
    out = tmp_path / "charts"
    paths = generate_charts(phase3, out)
    assert {path.name for path in paths} == set(CHART_FILENAMES.values())
    for path in paths:
        assert path.read_bytes() == b"fake-png"
