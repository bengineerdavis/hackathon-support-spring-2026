"""Generate fake Sentry events with raw log file attachments for testing."""

import time
import random
import sentry_sdk
from sentry_sdk import new_scope, capture_exception
from src.config import SENTRY_DSN

FAKE_LOG_TEMPLATE = """\
2026-04-21T{hh}:{mm}:{ss}Z [INFO]  Starting service worker pid={pid}
2026-04-21T{hh}:{mm}:{ss2}Z [DEBUG] Loading config from /etc/app/config.yaml
2026-04-21T{hh}:{mm}:{ss3}Z [INFO]  Database connection pool initialized (size=10)
2026-04-21T{hh}:{mm}:{ss4}Z [WARN]  Slow query detected: SELECT * FROM orders WHERE user_id={uid} took {ms}ms
2026-04-21T{hh}:{mm}:{ss5}Z [ERROR] Unhandled exception in request handler
Traceback (most recent call last):
  File "/app/handlers/order.py", line {line}, in process_order
    result = calculate_discount(order)
  File "/app/utils/discount.py", line 42, in calculate_discount
    return order["total"] / order["discount_rate"]
{exc_type}: {exc_msg}
2026-04-21T{hh}:{mm}:{ss6}Z [INFO]  Worker restarting after crash
"""

SCENARIOS = [
    ("ZeroDivisionError", "division by zero"),
    ("KeyError", "'discount_rate'"),
    ("TypeError", "unsupported operand type(s) for /: 'str' and 'int'"),
]


def _make_log(scenario_idx: int) -> bytes:
    exc_type, exc_msg = SCENARIOS[scenario_idx]
    hh = random.randint(8, 18)
    mm = random.randint(0, 59)
    uid = random.randint(1000, 9999)
    ms = random.randint(200, 5000)
    line = random.randint(20, 80)
    pid = random.randint(10000, 99999)

    def ts(offset: int) -> str:
        s = mm * 60 + offset
        return f"{hh:02d}:{s // 60:02d}:{s % 60:02d}"

    return FAKE_LOG_TEMPLATE.format(
        hh=f"{hh:02d}", mm=f"{mm:02d}", ss="00",
        ss2=ts(1), ss3=ts(3), ss4=ts(5), ss5=ts(8), ss6=ts(10),
        pid=pid, uid=uid, ms=ms, line=line,
        exc_type=exc_type, exc_msg=exc_msg,
    ).encode()


def generate_events(count: int = 3) -> None:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.0)

    for i in range(count):
        exc_type, exc_msg = SCENARIOS[i % len(SCENARIOS)]
        log_bytes = _make_log(i % len(SCENARIOS))

        try:
            if exc_type == "ZeroDivisionError":
                _ = 1 / 0
            elif exc_type == "KeyError":
                d: dict = {}
                _ = d["discount_rate"]
            else:
                _ = "total" / 2  # type: ignore[operator]
        except Exception as exc:
            with new_scope() as scope:
                scope.add_attachment(
                    bytes=log_bytes,
                    filename=f"app_{i}.log",
                    content_type="text/plain",
                )
                event_id = capture_exception(exc)
                print(f"Captured event {event_id}: {exc_type}")

        time.sleep(0.5)

    sentry_sdk.flush(timeout=10)
    print(f"Done. {count} events sent.")


if __name__ == "__main__":
    generate_events()
