import asyncio

from .adapters.base import get_adapters, supports_streaming
from .adapters.html2md_adapter import STREAM_INPUT_CHUNK_BYTES
from .probe import probe_streaming_adapter

HTML = b"<h1>hi</h1><p>Hello <strong>bold</strong></p>"


def test_all_phase1_adapters_convert_to_text():
    adapters = get_adapters(include_lxml_naive=True)
    assert {a.name for a in adapters} >= {
        "markdownify",
        "markdownify_default_oracle",
        "html_to_markdown",
        "htmd_py",
        "html2text_rs",
        "html2md",
        "html2md_streaming",
        "lxml_naive",
    }
    for adapter in adapters:
        out = adapter.convert(HTML)
        assert isinstance(out, str), adapter.name
        assert "hi" in out.lower(), adapter.name
        assert adapter.option_map.targets, adapter.name


def test_html2md_streaming_adapter_exposes_native_chunks():
    adapter = next(
        a
        for a in get_adapters(include_lxml_naive=False)
        if a.name == "html2md_streaming"
    )
    assert supports_streaming(adapter)
    out = adapter.convert(HTML)
    streamed = "".join(adapter.convert_stream_chunks(HTML))
    assert out == streamed
    assert "hi" in out.lower()


def test_html2md_streaming_adapter_chunks_fixture_input_for_cadence():
    adapter = next(
        a
        for a in get_adapters(include_lxml_naive=False)
        if a.name == "html2md_streaming"
    )
    paragraph = b"<p>streaming cadence block</p>"
    payload = paragraph * ((STREAM_INPUT_CHUNK_BYTES // len(paragraph)) + 1000)

    pieces = list(adapter.convert_stream_chunks(payload))

    assert len(pieces) > 1
    assert "".join(pieces) == adapter.convert(payload)


def test_streaming_cadence_probe_measures_first_chunk_and_gaps():
    adapter = next(
        a
        for a in get_adapters(include_lxml_naive=False)
        if a.name == "html2md_streaming"
    )

    async def run():
        result = await probe_streaming_adapter(
            "html2md_streaming:test", adapter.convert_stream_chunks, HTML
        )
        assert result.chunk_count >= 1
        assert result.first_chunk_s is not None
        assert result.first_chunk_s >= 0
        assert result.output_bytes == len(adapter.convert(HTML).encode())
        assert result.output_hash is not None

    asyncio.run(run())


def test_html2text_rs_residual_documents_known_fidelity_gaps():
    adapter = next(
        a for a in get_adapters(include_lxml_naive=False) if a.name == "html2text_rs"
    )
    residual = " ".join(adapter.option_map.residual)
    assert "tables" in residual
    assert "escaping" in residual
