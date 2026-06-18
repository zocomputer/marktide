"""Public conversions — sync/async/stream equivalence, bytes/str, chunk-invariance."""

from __future__ import annotations

import asyncio

import pytest

from html2md import (
    Options,
    convert,
    convert_async,
    convert_stream,
    convert_stream_async,
)

SAMPLE = "<div><p>Hello <strong>world</strong></p><span>tail</span><hr></div>"


def test_convert_basic() -> None:
    assert convert(SAMPLE) == convert(SAMPLE.encode())  # str and bytes agree


def test_str_and_bytes_equivalent() -> None:
    assert convert("<strong>é</strong>") == convert("<strong>é</strong>".encode())


def test_convert_async_matches_sync() -> None:
    assert asyncio.run(convert_async(SAMPLE)) == convert(SAMPLE)


def test_convert_stream_concatenation_matches_convert() -> None:
    chunks = [SAMPLE[i:i + 7].encode() for i in range(0, len(SAMPLE), 7)]
    streamed = "".join(convert_stream(chunks))
    assert streamed == convert(SAMPLE)


def test_convert_stream_async_matches_convert() -> None:
    async def run() -> str:
        async def agen():
            for i in range(0, len(SAMPLE), 5):
                yield SAMPLE[i:i + 5].encode()
        return "".join([c async for c in convert_stream_async(agen())])

    assert asyncio.run(run()) == convert(SAMPLE)


@pytest.mark.parametrize("chunk_size", [1, 3, 16, 1024, 64 * 1024])
def test_chunk_invariance(chunk_size: int) -> None:
    # The deterministic-transducer property: output is independent of how the input
    # bytes are split into feed chunks.
    data = SAMPLE.encode()
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    assert "".join(convert_stream(chunks)) == convert(SAMPLE)


def test_options_chunk_size_does_not_change_output() -> None:
    assert convert(SAMPLE, options=Options(chunk_size=4)) == convert(SAMPLE)


def test_empty_input() -> None:
    assert convert("") == ""
    assert convert(b"") == ""
    assert "".join(convert_stream([])) == ""
