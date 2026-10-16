from hr_assistant.rate_limit import RateLimiter


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_limit_per_client():
    limiter = RateLimiter(per_client=2, total=100, clock=Clock())
    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")  # other clients are counted separately


def test_limit_for_everyone_together():
    limiter = RateLimiter(per_client=10, total=2, clock=Clock())
    assert limiter.allow("a") and limiter.allow("b")
    assert not limiter.allow("c")


def test_old_questions_stop_counting():
    clock = Clock()
    limiter = RateLimiter(per_client=1, total=100, window_seconds=3600, clock=clock)
    assert limiter.allow("a")
    clock.now = 3601
    assert limiter.allow("a")


def test_refused_question_is_not_counted():
    limiter = RateLimiter(per_client=1, total=1, clock=Clock())
    assert limiter.allow("a")
    assert not limiter.allow("b")  # refused because of the total, must not count for b
    assert len(limiter._hits["b"]) == 0


def test_zero_turns_the_limit_off():
    limiter = RateLimiter(per_client=0, total=0, clock=Clock())
    assert all(limiter.allow("a") for _ in range(100))
