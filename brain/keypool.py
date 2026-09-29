"""Key pool: xoay vòng nhiều key + fallback + cooldown chống khóa lưu lượng.

Vấn đề cần giải quyết:
    Gemini free key bị Google "xích cổ" khi gọi liên tục (429/RESOURCE_EXHAUSTED),
    và gọi fallback dồn dập có thể khiến Google khóa luôn lưu lượng tài khoản.

Giải pháp:
    1. Xoay vòng (round-robin) giữa nhiều key thay vì dồn 1 key.
    2. Khi 1 key báo lỗi rate-limit/quota -> đánh dấu cooldown, chuyển key kế.
    3. Delay ngẫu nhiên giữa các lần gọi (jitter) để không bị coi là spam.
    4. Không bao giờ gọi lại key đang trong thời gian cooldown.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class _KeyState:
    key: str
    cooldown_until: float = 0.0
    consecutive_failures: int = 0


class KeyPool:
    """Quản lý một dàn key cho 1 provider, xoay vòng + cooldown."""

    def __init__(self, keys: list[str], cooldown_seconds: float = 60.0,
                 max_consecutive_failures: int = 2,
                 base_delay: float = 1.0):
        self._states = [_KeyState(k) for k in keys]
        self._cooldown = cooldown_seconds
        self._max_fail = max_consecutive_failures
        self._base_delay = base_delay
        self._idx = 0
        self._lock = threading.Lock()

    def __len__(self):
        return len(self._states)

    @property
    def available_count(self) -> int:
        now = time.time()
        return sum(1 for s in self._states if s.cooldown_until <= now)

    def _next_available(self) -> Optional[str]:
        now = time.time()
        n = len(self._states)
        if n == 0:
            return None
        # thử từ vị trí hiện tại quay 1 vòng
        for offset in range(n):
            s = self._states[(self._idx + offset) % n]
            if s.cooldown_until <= now:
                self._idx = (self._idx + offset + 1) % n
                return s.key
        # không key nào sẵn sàng: trả key cooldown ngắn nhất (hy vọng qua 429)
        soonest = min(self._states, key=lambda s: s.cooldown_until)
        if soonest.cooldown_until <= now + 5:
            return soonest.key
        return None

    def get(self) -> Optional[str]:
        """Lấy key kế tiếp khả dụng (kèm delay jitter nhẹ)."""
        with self._lock:
            k = self._next_available()
        if k is None:
            return None
        time.sleep(self._base_delay + random.uniform(0, 1.0))
        return k

    def report_success(self, key: str):
        with self._lock:
            for s in self._states:
                if s.key == key:
                    s.consecutive_failures = 0
                    s.cooldown_until = 0.0
                    break

    def report_failure(self, key: str, retryable: bool = True):
        """Ghi nhận lỗi. retryable=True (429/quota) -> cooldown; False -> cooldown dài."""
        with self._lock:
            for s in self._states:
                if s.key == key:
                    s.consecutive_failures += 1
                    if retryable:
                        s.cooldown_until = time.time() + self._cooldown
                    else:
                        s.cooldown_until = time.time() + self._cooldown * 5
                    break


def is_rate_limit(exc: Exception) -> bool:
    """Nhận diện lỗi rate-limit / quota (429, RESOURCE_EXHAUSTED, 403 quota)."""
    msg = str(exc).lower()
    markers = ("429", "resource_exhausted", "quota", "rate limit",
               "ratelimit", "too many requests", "exceeded")
    return any(m in msg for m in markers)


def retry_with_pool(pool: KeyPool, fn, *args, max_rounds: int | None = None,
                    **kwargs):
    """Gọi fn(key, *args, **kwargs) qua key pool, tự fallback sang key khác.

    fn phải nhận `key` làm tham số đầu tiên.
    Trả về (result, key_used) hoặc ném exception cuối cùng nếu hết key.
    """
    rounds = max_rounds if max_rounds is not None else max(1, len(pool))
    last_exc: Optional[Exception] = None
    used_keys: set[str] = set()
    for _ in range(rounds):
        key = pool.get()
        if key is None:
            time.sleep(2)
            continue
        if key in used_keys and len(used_keys) >= len(pool):
            time.sleep(3)  # đã thử hết 1 vòng, nghỉ rồi thử lại
        used_keys.add(key)
        try:
            result = fn(key, *args, **kwargs)
            pool.report_success(key)
            return result, key
        except Exception as e:
            last_exc = e
            pool.report_failure(key, retryable=is_rate_limit(e))
    if last_exc:
        raise last_exc
    raise RuntimeError("hết key khả dụng trong key pool")
