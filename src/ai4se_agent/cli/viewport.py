class Viewport:
    """Manages which portion of the output buffer is visible.

    offset=0 means show the newest content (bottom of buffer).
    follow_mode=True means auto-scroll to newest on each append.
    """

    def __init__(self, height: int):
        self.height = height
        self.offset = 0
        self.follow_mode = True

    def visible_range(self, total_lines: int) -> tuple[int, int]:
        """Return (start, end) slice indices into the buffer."""
        if total_lines == 0:
            return 0, 0
        available = min(self.height, total_lines)
        max_offset = total_lines - available
        self.offset = min(self.offset, max_offset)
        start = total_lines - available - self.offset
        end = start + available
        return max(0, start), end

    def scroll_up(self, lines: int = 5) -> None:
        self.offset += lines
        self.follow_mode = False

    def scroll_down(self, lines: int = 5) -> None:
        self.offset = max(0, self.offset - lines)
        if self.offset == 0:
            self.follow_mode = True

    def reset(self) -> None:
        self.offset = 0
        self.follow_mode = True
