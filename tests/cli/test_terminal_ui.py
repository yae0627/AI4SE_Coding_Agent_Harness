from ai4se_agent.cli.output_buffer import OutputBuffer
from ai4se_agent.cli.viewport import Viewport


# ── OutputBuffer ────────────────────────────────────────────────
def test_buffer_append_and_get_all():
    buf = OutputBuffer()
    buf.append("line 1")
    buf.append("line 2")
    assert buf.get_all() == ["line 1", "line 2"]


def test_buffer_len():
    buf = OutputBuffer()
    assert len(buf) == 0
    buf.append("a")
    assert len(buf) == 1


def test_buffer_clear():
    buf = OutputBuffer()
    buf.append("x")
    buf.clear()
    assert buf.get_all() == []


def test_buffer_extend():
    buf = OutputBuffer()
    buf.extend(["a", "b", "c"])
    assert buf.get_all() == ["a", "b", "c"]


# ── Viewport ────────────────────────────────────────────────────
def test_viewport_default_state():
    vp = Viewport(height=10)
    assert vp.height == 10
    assert vp.offset == 0
    assert vp.follow_mode is True


def test_viewport_scroll_up():
    vp = Viewport(height=5)
    vp.scroll_up(3)
    assert vp.offset == 3
    assert vp.follow_mode is False


def test_viewport_scroll_down():
    vp = Viewport(height=5)
    vp.offset = 10
    vp.scroll_down(3)
    assert vp.offset == 7


def test_viewport_scroll_down_clamped():
    vp = Viewport(height=5)
    vp.offset = 2
    vp.scroll_down(10)
    assert vp.offset == 0


def test_viewport_reset():
    vp = Viewport(height=5)
    vp.offset = 20
    vp.follow_mode = False
    vp.reset()
    assert vp.offset == 0
    assert vp.follow_mode is True


def test_viewport_visible_range_no_scroll():
    vp = Viewport(height=5)
    buf = OutputBuffer()
    for i in range(10):
        buf.append(f"line {i}")
    start, end = vp.visible_range(len(buf))
    assert start == 5   # 10 total - 5 height = start
    assert end == 10


def test_viewport_visible_range_with_scroll():
    vp = Viewport(height=5)
    vp.offset = 3
    buf = OutputBuffer()
    for i in range(15):
        buf.append(f"line {i}")
    start, end = vp.visible_range(len(buf))
    # 15 total - 5 height - 3 offset = 7
    assert start == 7
    assert end == 12


def test_viewport_visible_range_empty_buffer():
    vp = Viewport(height=5)
    start, end = vp.visible_range(0)
    assert start == 0
    assert end == 0


def test_viewport_auto_follow_after_reset():
    vp = Viewport(height=5)
    vp.scroll_up(10)
    assert vp.follow_mode is False
    vp.reset()
    assert vp.follow_mode is True
    assert vp.offset == 0
