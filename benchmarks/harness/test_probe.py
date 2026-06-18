import asyncio

from benchmarks.harness.probe import Placement, gil_releasing_sleep, probe_adapter, pure_python_burn


def test_probe_distinguishes_sleep_from_gil_holding_cpu():
    async def run():
        sleep = await probe_adapter(
            "sleep",
            gil_releasing_sleep,
            b"",
            placement=Placement.TO_THREAD,
            interval_s=0.001,
            duration_s=0.12,
        )
        cpu = await probe_adapter(
            "cpu",
            pure_python_burn,
            b"",
            placement=Placement.TO_THREAD,
            interval_s=0.001,
            duration_s=0.12,
            repeat_until_duration=True,
        )
        assert sleep.samples > cpu.samples
        assert cpu.p50_ms > sleep.p50_ms * 5

    asyncio.run(run())


def test_inline_placement_records_output_hash():
    async def run():
        result = await probe_adapter(
            "inline",
            lambda payload: payload.decode().upper(),
            b"abc",
            placement=Placement.INLINE,
            interval_s=0.001,
            duration_s=0.01,
        )
        assert result.conversion_wall_s is not None
        assert result.iterations == 1
        assert result.output_bytes == 3
        assert result.output_hash is not None
        assert result.iterations and result.iterations >= 1

    asyncio.run(run())
