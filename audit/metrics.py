"""
metrics.py
---------------------------------
Lightweight in-memory counters so the pitch can quote REAL measured
numbers instead of estimates (e.g. "X% of transactions needed step-up,
Y contradictions caught, Z fell back to simulated checkout").

Not a database — resets every process run. Good enough for a demo /
hackathon dashboard. Call record_*() from the relevant modules as
events happen, then export_summary() at the end for the pitch/README.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any

try:
    from audit.recourse import DenialReason
except ImportError:
    from recourse import DenialReason



@dataclass
class MetricsTracker:
    total_attempts: int = 0
    successful: int = 0
    denied_by_reason: Dict[str, int] = field(default_factory=dict)
    fallback_checkouts: int = 0
    live_checkouts: int = 0
    contradictions_caught: int = 0
    step_up_triggered: int = 0
    latencies_sec: List[float] = field(default_factory=list)
    _start_time: float = field(default_factory=time.time, repr=False)

    # -- recording methods ----------------------------------------------

    def record_attempt(self) -> None:
        self.total_attempts += 1

    def record_success(self, latency_sec: float | None = None) -> None:
        self.successful += 1
        if latency_sec is not None:
            self.latencies_sec.append(latency_sec)

    def record_denial(self, reason: DenialReason) -> None:
        key = reason.value
        self.denied_by_reason[key] = self.denied_by_reason.get(key, 0) + 1

    def record_checkout_mode(self, mode: str) -> None:
        if mode == "live":
            self.live_checkouts += 1
        elif mode == "fallback":
            self.fallback_checkouts += 1

    def record_contradiction(self) -> None:
        self.contradictions_caught += 1

    def record_step_up_triggered(self) -> None:
        self.step_up_triggered += 1

    # -- reporting --------------------------------------------------------

    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return round(100 * self.successful / self.total_attempts, 2)

    def avg_latency_sec(self) -> float:
        if not self.latencies_sec:
            return 0.0
        return round(sum(self.latencies_sec) / len(self.latencies_sec), 3)

    def export_summary(self) -> Dict[str, Any]:
        uptime = round(time.time() - self._start_time, 2)
        return {
            "uptime_sec": uptime,
            "total_attempts": self.total_attempts,
            "successful": self.successful,
            "success_rate_pct": self.success_rate(),
            "denied_by_reason": self.denied_by_reason,
            "live_checkouts": self.live_checkouts,
            "fallback_checkouts": self.fallback_checkouts,
            "contradictions_caught": self.contradictions_caught,
            "step_up_triggered": self.step_up_triggered,
            "avg_latency_sec": self.avg_latency_sec(),
        }

    def print_summary(self) -> None:
        summary = self.export_summary()
        print("--- Metrics summary ---")
        for k, v in summary.items():
            print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    m = MetricsTracker()

    m.record_attempt()
    m.record_success(latency_sec=1.2)
    m.record_checkout_mode("live")

    m.record_attempt()
    m.record_denial(DenialReason.STEP_UP_REQUIRED)
    m.record_step_up_triggered()

    m.record_attempt()
    m.record_success(latency_sec=0.9)
    m.record_checkout_mode("fallback")
    m.record_contradiction()

    m.print_summary()

    assert m.total_attempts == 3
    assert m.successful == 2
    assert m.denied_by_reason.get("step_up_required") == 1
    print("\nmetrics.py self-tests passed.")