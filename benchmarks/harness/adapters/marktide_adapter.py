"""Local marktide phase-3 adapter."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .base import Adapter, OptionMap


STREAM_INPUT_CHUNK_BYTES = 64 * 1024

OPTION_MAP = OptionMap(
    settings={"options": "marktide.Options() defaults"},
    targets={
        "options": "drop-in markdownify-compatible defaults; no benchmark normalization",
    },
    residual=(
        "Under active phase-2 implementation; final fidelity is owned by the conformance harness.",
    ),
)


@dataclass(frozen=True)
class Html2MdAdapter(Adapter):
    name: str = "marktide"
    package: str = "marktide local checkout"
    engine: str = "lxml target parser + Python streaming emitter"
    option_map: OptionMap = OPTION_MAP

    def convert(self, html_bytes: bytes) -> str:
        import marktide

        return marktide.convert(html_bytes)


@dataclass(frozen=True)
class Html2MdStreamingAdapter(Adapter):
    name: str = "marktide_streaming"
    package: str = "marktide local checkout"
    engine: str = "lxml target parser + Python streaming emitter (convert_stream)"
    option_map: OptionMap = OptionMap(
        settings={
            "api": "marktide.convert_stream(chunked html_bytes)",
            "input_chunk_bytes": STREAM_INPUT_CHUNK_BYTES,
        },
        targets={
            "api": "native streaming API for TTFO and inter-chunk cadence measurement with chunked fixture input",
        },
        residual=OPTION_MAP.residual,
    )

    def convert(self, html_bytes: bytes) -> str:
        return "".join(self.convert_stream_chunks(html_bytes))

    def convert_stream_chunks(self, html_bytes: bytes) -> Iterable[str]:
        import marktide

        yield from marktide.convert_stream(_iter_input_chunks(html_bytes))


def _iter_input_chunks(html_bytes: bytes) -> Iterable[bytes]:
    for offset in range(0, len(html_bytes), STREAM_INPUT_CHUNK_BYTES):
        yield html_bytes[offset : offset + STREAM_INPUT_CHUNK_BYTES]
