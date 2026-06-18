import asyncio

from benchmarks.harness.memory import sample_peak_rss_while


def test_sample_peak_rss_while_records_peak_and_curve():
    readings = iter([100, 120, 180, 140, 160])

    def read_rss():
        return next(readings, 160)

    async def work():
        await asyncio.sleep(0.003)
        return "done"

    async def run():
        value, peak = await sample_peak_rss_while(
            work(), read_rss_bytes=read_rss, interval_s=0.001
        )
        assert value == "done"
        assert peak.baseline_bytes == 100
        assert peak.peak_bytes == 180
        assert peak.peak_delta_bytes == 80
        assert peak.final_bytes == peak.sample_bytes[-1]
        assert peak.samples == len(peak.sample_bytes) == len(peak.sample_offsets_s)
        assert peak.as_dict()["peak_delta_bytes"] == 80

    asyncio.run(run())


def test_sample_peak_rss_while_propagates_workload_exception_after_sampling():
    calls = 0

    def read_rss():
        nonlocal calls
        calls += 1
        return 100 + calls

    async def boom():
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    async def run():
        try:
            await sample_peak_rss_while(
                boom(), read_rss_bytes=read_rss, interval_s=0.001
            )
        except RuntimeError as exc:
            assert str(exc) == "boom"
        else:
            raise AssertionError("expected workload exception")
        assert calls >= 2

    asyncio.run(run())
