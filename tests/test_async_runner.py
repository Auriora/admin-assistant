import asyncio
import pytest

from core.utilities import async_runner as ar


@pytest.fixture(autouse=True)
def cleanup_after():
    """Ensure global AsyncRunner is shutdown after each test to avoid thread leakage."""
    yield
    try:
        ar.shutdown_global_runner()
    except Exception:
        pass


def test_run_simple_coroutine():
    async def hello():
        await asyncio.sleep(0)
        return "ok"

    result = ar.run_async(hello(), timeout=2.0)
    assert result == "ok"


def test_run_async_safe_on_exception_returns_default():
    async def bad():
        raise RuntimeError("boom")

    res = ar.run_async_safe(bad(), timeout=1.0, default="fallback")
    assert res == "fallback"


def test_run_async_raises_timeout_immediate_path():
    # The implementation raises asyncio.TimeoutError immediately for extremely small timeouts
    async def sleepy():
        await asyncio.sleep(0.1)
        return "done"

    with pytest.raises(asyncio.TimeoutError):
        # Use a tiny timeout to trigger the immediate timeout guard
        ar.run_async(sleepy(), timeout=0.0005)


def test_runner_health_and_recreation():
    runner1 = ar.get_async_runner()
    assert runner1 is not None
    assert runner1.is_healthy() is True

    # Shutdown the runner and ensure a new one is created on next get_async_runner()
    ar.shutdown_global_runner()

    runner2 = ar.get_async_runner()
    assert runner2 is not None
    assert runner2 is not runner1
    assert runner2.is_healthy() is True

