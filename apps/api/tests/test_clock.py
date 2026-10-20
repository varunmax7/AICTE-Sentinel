from app.core import clock


def test_clock_demo_offset_roundtrip() -> None:
    clock.reset_offset()
    try:
        before = clock.now()
        clock.set_offset_seconds(3600)
        after = clock.now()
        assert (after - before).total_seconds() > 3500
    finally:
        clock.reset_offset()


def test_clock_offset_zero_by_default() -> None:
    clock.reset_offset()
    assert clock.get_offset_seconds() == 0
