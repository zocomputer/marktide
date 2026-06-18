from benchmarks.harness.adapters.base import get_adapters

HTML = b'<h1>hi</h1><p>Hello <strong>bold</strong></p>'


def test_all_phase1_adapters_convert_to_text():
    adapters = get_adapters(include_lxml_naive=True)
    assert {a.name for a in adapters} >= {"markdownify", "html_to_markdown", "htmd_py", "html2text_rs", "lxml_naive"}
    for adapter in adapters:
        out = adapter.convert(HTML)
        assert isinstance(out, str), adapter.name
        assert "hi" in out.lower(), adapter.name
        assert adapter.option_map.targets, adapter.name


def test_html2text_rs_residual_documents_known_fidelity_gaps():
    adapter = next(a for a in get_adapters(include_lxml_naive=False) if a.name == "html2text_rs")
    residual = " ".join(adapter.option_map.residual)
    assert "tables" in residual
    assert "escaping" in residual
