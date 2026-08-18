"""
tests/test_circuit_breaker.py
------------------------------
Unit test suite verifying CircuitBreaker state transitions:
- CLOSED -> OPEN after hitting consecutive failure threshold (5)
- Fast-fail CircuitBreakerOpenException when OPEN
- Automatic transition to HALF_OPEN after cooldown elapses
- Recovery probe success: HALF_OPEN -> CLOSED
- Recovery probe failure: HALF_OPEN -> OPEN
"""

import pytest
import asyncio
from app.engine import CircuitBreaker, CircuitBreakerOpenException, CircuitBreakerStateEnum


@pytest.mark.asyncio
async def test_circuit_breaker_initial_state():
    cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=1.0)
    metrics = await cb.get_metrics()
    assert metrics.state == CircuitBreakerStateEnum.CLOSED
    assert metrics.consecutive_failures == 0
    assert metrics.success_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open():
    cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=1.0)

    # 4 failures -> state remains CLOSED
    for i in range(4):
        await cb.record_failure(f"Error {i + 1}")
        assert cb.state == CircuitBreakerStateEnum.CLOSED

    # 5th failure -> trips to OPEN
    await cb.record_failure("Error 5")
    assert cb.state == CircuitBreakerStateEnum.OPEN

    # Outbound requests must now fast-fail with exception
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        await cb.before_request()
    assert "Circuit Breaker is OPEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_breaker_cooldown_and_half_open_recovery_success():
    # Cooldown of 0.2 seconds for quick testing
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.2)

    await cb.record_failure("Failure 1")
    await cb.record_failure("Failure 2")
    assert cb.state == CircuitBreakerStateEnum.OPEN

    # Wait for cooldown to expire
    await asyncio.sleep(0.25)

    # Calling before_request should evaluate cooldown and transition to HALF_OPEN
    await cb.before_request()
    assert cb.state == CircuitBreakerStateEnum.HALF_OPEN

    # Successful request should recover breaker back to CLOSED
    await cb.record_success()
    assert cb.state == CircuitBreakerStateEnum.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery_failure():
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.2)

    await cb.record_failure("Failure 1")
    await cb.record_failure("Failure 2")
    assert cb.state == CircuitBreakerStateEnum.OPEN

    await asyncio.sleep(0.25)
    await cb.before_request()
    assert cb.state == CircuitBreakerStateEnum.HALF_OPEN

    # Failed probe trial should trip back to OPEN
    await cb.record_failure("Trial failure")
    assert cb.state == CircuitBreakerStateEnum.OPEN
