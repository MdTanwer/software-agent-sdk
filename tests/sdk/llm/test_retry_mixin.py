import asyncio
from unittest.mock import MagicMock

import pytest
from litellm.exceptions import RateLimitError
from tenacity import (
    Future,
    RetryCallState,
    stop_after_attempt,
    stop_after_delay,
    stop_all,
    stop_any,
    stop_never,
)

from openhands.sdk.llm.exceptions import (
    LLMNoResponseError,
    LLMRateLimitError,
    map_provider_exception,
)
from openhands.sdk.llm.utils.retry_mixin import (
    RetryMixin,
    SupportsStopCondition,
    extract_max_retries,
)


def test_extract_max_retries_single_stop():
    """extract_max_retries extracts limit from stop_after_attempt."""
    stop = stop_after_attempt(5)
    assert extract_max_retries(stop) == 5


def test_extract_max_retries_compound_stops():
    """extract_max_retries extracts limit from stop_any and stop_all."""
    stop_any_condition = stop_any(stop_after_delay(10), stop_after_attempt(4))
    assert extract_max_retries(stop_any_condition) == 4

    stop_all_condition = stop_all(stop_after_attempt(7), stop_after_delay(30))
    assert extract_max_retries(stop_all_condition) == 7


def test_extract_max_retries_unbounded():
    """extract_max_retries returns None for unbounded stop conditions."""
    assert extract_max_retries(stop_never) is None
    assert extract_max_retries(stop_after_delay(60)) is None
    assert extract_max_retries(None) is None


def test_extract_max_retries_custom_predicate():
    """extract_max_retries supports custom stop predicate with max_attempts."""

    class CustomStop:
        max_attempts: int = 8

    assert extract_max_retries(CustomStop()) == 8


def test_log_retry_attempt_bounded():
    """log_retry_attempt attaches attempt and max_retries on bounded stop."""
    mixin = RetryMixin()
    exc = LLMNoResponseError("timeout")

    fake_future = Future(attempt_number=2)
    fake_future.set_exception(exc)

    mock_retry_obj = MagicMock()
    mock_retry_obj.stop = stop_after_attempt(3)
    assert isinstance(mock_retry_obj, SupportsStopCondition)

    state = RetryCallState(mock_retry_obj, fn=lambda: None, args=(), kwargs={})
    state.attempt_number = 2
    state.outcome = fake_future

    mixin.log_retry_attempt(state)
    assert exc.retry_attempt == 2
    assert exc.max_retries == 3


def test_log_retry_attempt_unbounded():
    """log_retry_attempt attaches attempt number while max_retries remains None."""
    mixin = RetryMixin()
    exc = LLMNoResponseError("unbounded error")

    fake_future = Future(attempt_number=5)
    fake_future.set_exception(exc)

    mock_retry_obj = MagicMock()
    mock_retry_obj.stop = stop_never

    state = RetryCallState(mock_retry_obj, fn=lambda: None, args=(), kwargs={})
    state.attempt_number = 5
    state.outcome = fake_future

    mixin.log_retry_attempt(state)
    assert exc.retry_attempt == 5
    assert exc.max_retries is None


def test_log_retry_attempt_litellm_exception():
    """log_retry_attempt attaches attempt and max_retries to litellm exceptions."""
    from litellm.exceptions import APIConnectionError

    mixin = RetryMixin()
    exc = APIConnectionError("connection failed", "test_provider", "test_model")
    assert not hasattr(exc, "retry_attempt")

    fake_future = Future(attempt_number=2)
    fake_future.set_exception(exc)

    mock_retry_obj = MagicMock()
    mock_retry_obj.stop = stop_after_attempt(3)

    state = RetryCallState(mock_retry_obj, fn=lambda: None, args=(), kwargs={})
    state.attempt_number = 2
    state.outcome = fake_future

    mixin.log_retry_attempt(state)
    assert getattr(exc, "retry_attempt", None) == 2
    assert exc.max_retries == 3


def test_log_retry_attempt_arbitrary_exception_safely_ignored():
    """log_retry_attempt safely ignores exceptions not satisfying retry protocols."""
    mixin = RetryMixin()
    exc = RuntimeError("generic error")

    fake_future = Future(attempt_number=1)
    fake_future.set_exception(exc)

    mock_retry_obj = MagicMock()
    mock_retry_obj.stop = stop_after_attempt(4)

    state = RetryCallState(mock_retry_obj, fn=lambda: None, args=(), kwargs={})
    state.attempt_number = 1
    state.outcome = fake_future

    mixin.log_retry_attempt(state)
    assert not hasattr(exc, "retry_attempt")


def _exhausting(mixin: RetryMixin, exceptions: tuple[type[BaseException], ...]):
    return mixin.retry_decorator(
        num_retries=3,
        retry_exceptions=exceptions,
        retry_min_wait=0,
        retry_max_wait=0,
    )


def test_exhausted_retries_stamp_the_final_new_exception():
    """Each attempt raises a new error, so only the exhaustion path can stamp it."""
    mixin = RetryMixin()
    raised: list[LLMNoResponseError] = []

    @_exhausting(mixin, (LLMNoResponseError,))
    def flaky() -> None:
        exc = LLMNoResponseError("no response")
        raised.append(exc)
        raise exc

    with pytest.raises(LLMNoResponseError) as err:
        flaky()

    assert len(raised) == 3
    assert err.value is raised[-1]
    assert err.value.retry_attempt == 3
    assert err.value.max_retries == 3
    assert raised[0].retry_attempt == 1
    assert raised[1].retry_attempt == 2


def test_exhausted_retries_stamp_a_reused_exception_with_the_final_attempt():
    """Reusing one exception must not keep the previous attempt's stamp."""
    mixin = RetryMixin()
    exc = LLMNoResponseError("no response")

    @_exhausting(mixin, (LLMNoResponseError,))
    def flaky() -> None:
        raise exc

    with pytest.raises(LLMNoResponseError):
        flaky()

    assert exc.retry_attempt == 3
    assert exc.max_retries == 3


def test_exhausted_provider_exception_keeps_metadata_after_mapping():
    """A fresh LiteLLM error per attempt still reaches the mapped SDK error."""
    mixin = RetryMixin()

    @_exhausting(mixin, (RateLimitError,))
    def flaky() -> None:
        raise RateLimitError("rate limit", "gpt-4o", "openai")

    with pytest.raises(RateLimitError) as err:
        flaky()

    assert "LiteLLM Max Retries" not in str(err.value)
    mapped = map_provider_exception(err.value)
    assert isinstance(mapped, LLMRateLimitError)
    assert mapped.retry_attempt == 3
    assert mapped.max_retries == 3
    assert "LiteLLM Max Retries" not in str(mapped)


def test_exhausted_async_retries_stamp_the_final_exception():
    mixin = RetryMixin()

    @_exhausting(mixin, (LLMNoResponseError,))
    async def flaky() -> None:
        raise LLMNoResponseError("no response")

    with pytest.raises(LLMNoResponseError) as err:
        asyncio.run(flaky())

    assert err.value.retry_attempt == 3
    assert err.value.max_retries == 3
