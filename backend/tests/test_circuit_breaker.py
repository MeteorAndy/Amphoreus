"""Tests for the LLM circuit breaker (T1-④) — pure state machine, zero IO."""

from __future__ import annotations

from app.core.circuit_breaker import CircuitBreaker, BreakerState


def test_starts_closed():
    cb = CircuitBreaker()
    assert cb.state == BreakerState.CLOSED and not cb.is_open


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == BreakerState.OPEN and cb.is_open


def test_stays_closed_below_threshold():
    cb = CircuitBreaker(failure_threshold=5)
    for _ in range(4):
        cb.record_failure()
    assert cb.state == BreakerState.CLOSED


def test_success_resets_to_closed():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == BreakerState.CLOSED
    # Failures reset to zero
    for _ in range(2):
        cb.record_failure()
    assert cb.state == BreakerState.CLOSED


def test_half_open_probe_failure_does_not_change_count():
    """A failure in half-open state should not add to the failure count."""
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.0)
    for _ in range(2):
        cb.record_failure()
    assert cb.state == BreakerState.OPEN
    # After timeout, transitions to HALF_OPEN when accessed
    cb._state = BreakerState.HALF_OPEN  # simulate timeout
    cb.record_failure()
    assert cb.state == BreakerState.HALF_OPEN  # stays half-open, doesn't reopen


# --- Stage grading (T1-⑤) ---

def test_stage_severity_completeness():
    """Every PipelineStage must have a severity entry."""
    from app.services.pipeline_orchestrator import PipelineStage, _STAGE_SEVERITY
    for stage in PipelineStage:
        if stage != PipelineStage.DONE:
            assert stage in _STAGE_SEVERITY, f"{stage} missing from _STAGE_SEVERITY"


def test_canon_is_only_optional():
    """CANON is the sole optional stage — failures there warn, don't terminate."""
    from app.services.pipeline_orchestrator import _STAGE_SEVERITY, PipelineStage
    optional = [s for s, v in _STAGE_SEVERITY.items() if v == "optional"]
    assert optional == [PipelineStage.CANON]


def test_critical_stages_fail_fast():
    """All critical stages — failure must terminate the pipeline."""
    from app.services.pipeline_orchestrator import _STAGE_SEVERITY, PipelineStage
    critical = [s for s, v in _STAGE_SEVERITY.items() if v == "critical"]
    assert PipelineStage.WORLD in critical
    assert PipelineStage.CHARACTERS in critical
    assert PipelineStage.WRITING in critical
