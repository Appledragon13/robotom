"""
adventure_ui.py
───────────────
Reusable terminal UI for text-based adventures.

Layout
┌─────────────────────────────────┐
│  DIALOGUE / STORY  (tall)       │
│                                 │
│                                 │
├─────────────────────────────────┤
│  CHOICES  (short)               │
│  [1] Go north   [2] Open door   │
└─────────────────────────────────┘

Usage
-----
    from gameUI import AdventureUI

    ui = AdventureUI()
    choice = ui.show(
        dialogue="You stand at a crossroads. The wind howls.",
        choices=["Go north", "Go south", "Check inventory"]
    )
    ui.close()

    # Or use as a context manager (auto-closes):
    with AdventureUI() as ui:
        choice = ui.show("You enter a dark cave...", ["Light torch", "Go back"])

    # Ask the player to type something (e.g. their name):
    with AdventureUI() as ui:
        name = ui.input_str("What is your name, traveller?", prompt="Name: ")

Typewriter effect
-----------------
    Pass type_speed (seconds per character) to AdventureUI to enable the
    typewriter animation.  A value of 0 disables it (instant render).
    The player can skip the animation at any time by pressing any key.

        ui = AdventureUI(type_speed=0.03)   # fast
        ui = AdventureUI(type_speed=0.06)   # default — classic RPG feel
        ui = AdventureUI(type_speed=0)      # instant (original behaviour)
"""

import curses
import textwrap
import time


# ── Colour pair IDs ──────────────────────────────────────────────────────────
_PAIR_BORDER   = 1   # box borders + title
_PAIR_DIALOGUE = 2   # story text
_PAIR_CHOICE   = 3   # choice text (normal)
_PAIR_SELECTED = 4   # highlighted choice
_PAIR_INPUT    = 5   # text input line


class AdventureUI:
    """
    A full-screen curses UI split into a tall dialogue panel and a compact
    choices panel. Entirely reusable — call show() as many times as you like.

    Parameters
    ----------
    title : str
        Text shown in the top border of the dialogue box.
    dialogue_ratio : float
        Fraction of the screen height given to the dialogue panel (0–1).
    scroll_speed : int
        Lines scrolled per UP/DOWN or j/k key press.
    type_speed : float
        Seconds between each character during the typewriter animation.
        Set to 0 to disable the effect (text appears instantly).
        The player can always press any key to skip straight to the end.
    """

    def __init__(
        self,
        title: str = "[ Adventure ]",
        dialogue_ratio: float = 0.72,
        scroll_speed: int = 1,
        type_speed: float = 0.04,
    ):
        self.title          = title
        self.dialogue_ratio = dialogue_ratio
        self.scroll_speed   = scroll_speed
        self.type_speed     = type_speed
        self._stdscr        = None
        self._init_curses()

    # ── context manager ──────────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── public API ───────────────────────────────────────────────────────────

    def show(self, dialogue: str, choices: list[str]) -> int:
        """
        Render the UI and wait for the player to pick a choice.

        The dialogue text is revealed with a typewriter effect (controlled by
        ``type_speed``).  The player can press any key to skip straight to the
        end of the animation, after which the choices panel appears and the
        normal scroll / number-key input loop begins.

        Parameters
        ----------
        dialogue : str
            Narrative / story text. Long strings are word-wrapped automatically.
            Supports \\n for manual line breaks.
        choices : list[str]
            List of option strings, e.g. ["Go north", "Open door"].
            Maximum 9 choices (keys 1-9).

        Returns
        -------
        int
            1-based index of the chosen option.
        """
        if not choices:
            raise ValueError("choices must not be empty")
        if len(choices) > 9:
            raise ValueError("maximum 9 choices supported")

        rows, cols = self._stdscr.getmaxyx()
        dialogue_h = max(5, int(rows * self.dialogue_ratio))
        choices_h  = rows - dialogue_h
        inner_w    = cols - 4
        d_lines    = self._wrap(dialogue, inner_w)

        # ── typewriter phase ─────────────────────────────────────────────────
        self._typewrite_dialogue(d_lines, dialogue_h, cols)

        # ── draw choices panel, then enter scroll / pick loop ────────────────
        scroll_offset = 0

        while True:
            self._stdscr.erase()
            rows, cols = self._stdscr.getmaxyx()

            dialogue_h = max(5, int(rows * self.dialogue_ratio))
            choices_h  = rows - dialogue_h

            inner_w      = cols - 4
            d_lines      = self._wrap(dialogue, inner_w)
            max_scroll   = max(0, len(d_lines) - (dialogue_h - 2))
            scroll_offset = min(scroll_offset, max_scroll)
            visible      = d_lines[scroll_offset : scroll_offset + dialogue_h - 2]

            self._draw_dialogue(0,          0, dialogue_h, cols, visible,
                                scroll_offset, max_scroll)
            self._draw_choices (dialogue_h, 0, choices_h,  cols, choices)

            self._stdscr.refresh()
            key = self._stdscr.getch()

            if key in (curses.KEY_UP, ord('k')):
                scroll_offset = max(0, scroll_offset - self.scroll_speed)
                continue
            if key in (curses.KEY_DOWN, ord('j')):
                scroll_offset = min(max_scroll, scroll_offset + self.scroll_speed)
                continue
            if key == curses.KEY_PPAGE:
                scroll_offset = max(0, scroll_offset - (dialogue_h - 3))
                continue
            if key == curses.KEY_NPAGE:
                scroll_offset = min(max_scroll, scroll_offset + (dialogue_h - 3))
                continue

            if ord('1') <= key <= ord('9'):
                idx = key - ord('0')
                if 1 <= idx <= len(choices):
                    return idx

    def show_message(self, dialogue: str, prompt: str = "[ Press any key ]"):
        """
        Display a message with no choices — just press any key to continue.
        Useful for cut-scenes, game-over screens, or introductions.
        The typewriter effect applies here too; pressing a key skips it.
        """
        rows, cols = self._stdscr.getmaxyx()
        inner_w    = cols - 4
        d_lines    = self._wrap(dialogue, inner_w)
        dialogue_h = rows - 3

        self._typewrite_dialogue(d_lines, dialogue_h, cols)

        # After typing (or skip), redraw fully then show the prompt
        self._stdscr.erase()
        rows, cols = self._stdscr.getmaxyx()
        self._draw_dialogue(0, 0, rows - 3, cols, d_lines[:rows - 5], 0, 0)

        prompt_row = rows - 3
        attr = curses.color_pair(_PAIR_BORDER) | curses.A_BOLD
        safe_prompt = prompt[: cols - 2]
        pad = (cols - len(safe_prompt)) // 2
        self._safe_addstr(prompt_row + 1, pad, safe_prompt, attr)
        self._stdscr.refresh()
        self._stdscr.getch()

    def input_str(self, dialogue: str, prompt: str = "> ", max_len: int = 40) -> str:
        """
        Show dialogue text then let the player type a free-text answer.
        Returns the string they typed when they press Enter.

        Parameters
        ----------
        dialogue : str
            Prompt / flavour text shown in the top panel.
        prompt : str
            Short label shown next to the input cursor (e.g. "Name: ").
        max_len : int
            Maximum characters the player can type.
        """
        curses.echo()
        curses.curs_set(1)

        self._stdscr.erase()
        rows, cols = self._stdscr.getmaxyx()

        dialogue_h = max(5, int(rows * self.dialogue_ratio))
        choices_h  = rows - dialogue_h

        inner_w = cols - 4
        d_lines = self._wrap(dialogue, inner_w)
        visible = d_lines[: dialogue_h - 2]

        self._draw_dialogue(0, 0, dialogue_h, cols, visible, 0, 0)

        # Draw the input box
        self._draw_box(dialogue_h, 0, choices_h, cols, "[ Type your answer ]")
        attr_input = curses.color_pair(_PAIR_INPUT) | curses.A_BOLD
        self._safe_addstr(dialogue_h + 1, 2, prompt, attr_input)
        self._stdscr.refresh()

        input_col = 2 + len(prompt)
        result = self._stdscr.getstr(dialogue_h + 1, input_col, max_len)

        curses.noecho()
        curses.curs_set(0)

        return result.decode("utf-8", errors="replace").strip()

    def close(self):
        """Restore the terminal to its original state."""
        if self._stdscr:
            curses.nocbreak()
            self._stdscr.keypad(False)
            curses.echo()
            curses.endwin()
            self._stdscr = None

    # ── private helpers ──────────────────────────────────────────────────────

    def _typewrite_dialogue(self, d_lines: list[str], dialogue_h: int, cols: int):
        """
        Reveal the dialogue text character-by-character inside the dialogue box.

        The animation runs at ``self.type_speed`` seconds per character.
        If ``type_speed`` is 0 the text is rendered instantly.
        Pressing any key during the animation skips straight to the full text.

        Uses ``curses.halfdelay`` so each getch() times out quickly (allowing
        the per-character delay loop) while still detecting a skip keypress.

        Parameters
        ----------
        d_lines : list[str]
            Pre-wrapped lines of dialogue text.
        dialogue_h : int
            Height (rows) allocated to the dialogue panel.
        cols : int
            Full terminal width.
        """
        if self.type_speed <= 0:
            # Instant — just draw everything and return
            self._stdscr.erase()
            visible = d_lines[: dialogue_h - 2]
            self._draw_dialogue(0, 0, dialogue_h, cols, visible, 0, 0)
            self._stdscr.refresh()
            return

        attr       = curses.color_pair(_PAIR_DIALOGUE)
        max_rows   = dialogue_h - 2          # usable text rows inside the box
        visible    = d_lines[:max_rows]      # only the first screenful

        # halfdelay(n) makes getch() block for up to n tenths of a second,
        # returning ERR on timeout.  We use the shortest non-zero value (1 = 0.1 s)
        # so the skip check is responsive, and manage the per-char timing ourselves.
        curses.halfdelay(1)

        skipped   = False
        row_idx   = 0        # which line we're currently printing
        col_idx   = 0        # character position within that line
        last_tick = time.monotonic()

        try:
            while row_idx < len(visible):
                now = time.monotonic()

                # ── skip check ───────────────────────────────────────────────
                key = self._stdscr.getch()
                if key != curses.ERR:
                    skipped = True
                    break

                # ── wait for the next character slot ─────────────────────────
                if now - last_tick < self.type_speed:
                    continue
                last_tick = now

                line = visible[row_idx]

                # Draw the box border once per line (first char of each line)
                if col_idx == 0:
                    self._stdscr.erase()
                    self._draw_box(0, 0, dialogue_h, cols, self.title)
                    # Redraw all already-completed lines
                    for prev_i in range(row_idx):
                        self._safe_addstr(1 + prev_i, 2, visible[prev_i], attr)

                if col_idx < len(line):
                    # Print one more character on the current line
                    partial = line[: col_idx + 1]
                    self._safe_addstr(1 + row_idx, 2, partial, attr)
                    col_idx += 1
                else:
                    # Finished this line — move to the next
                    self._safe_addstr(1 + row_idx, 2, line, attr)
                    row_idx += 1
                    col_idx  = 0

                self._stdscr.refresh()

        finally:
            # Restore blocking getch for the interactive phase
            curses.cbreak()

        # If skipped (or finished), render the complete visible text instantly
        self._stdscr.erase()
        self._draw_dialogue(0, 0, dialogue_h, cols, visible, 0, 0)
        self._stdscr.refresh()

    def _init_curses(self):
        self._stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self._stdscr.keypad(True)

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(_PAIR_BORDER,   curses.COLOR_GREEN,  curses.COLOR_BLACK)
            curses.init_pair(_PAIR_DIALOGUE, curses.COLOR_GREEN,  curses.COLOR_BLACK)
            curses.init_pair(_PAIR_CHOICE,   curses.COLOR_GREEN,  curses.COLOR_BLACK)
            curses.init_pair(_PAIR_SELECTED, curses.COLOR_BLACK,  curses.COLOR_GREEN)
            curses.init_pair(_PAIR_INPUT,    curses.COLOR_GREEN,  curses.COLOR_BLACK)
            self._stdscr.bkgd(' ', curses.color_pair(_PAIR_DIALOGUE))

    def _wrap(self, text: str, width: int) -> list[str]:
        lines = []
        for paragraph in text.split('\n'):
            if paragraph.strip() == '':
                lines.append('')
            else:
                lines.extend(textwrap.wrap(paragraph, width) or [''])
        return lines

    def _draw_box(self, top: int, left: int, height: int, width: int,
                  title: str = "", colour_pair: int = _PAIR_BORDER):
        attr = curses.color_pair(colour_pair) | curses.A_BOLD
        rows, cols = self._stdscr.getmaxyx()

        def s(r, c, ch):
            if 0 <= r < rows and 0 <= c < cols - 1:
                try:
                    self._stdscr.addch(r, c, ch, attr)
                except curses.error:
                    pass

        s(top,            left,           curses.ACS_ULCORNER)
        s(top,            left+width-1,   curses.ACS_URCORNER)
        s(top+height-1,   left,           curses.ACS_LLCORNER)
        s(top+height-1,   left+width-1,   curses.ACS_LRCORNER)

        for c in range(left+1, left+width-1):
            s(top,          c, curses.ACS_HLINE)
            s(top+height-1, c, curses.ACS_HLINE)

        for r in range(top+1, top+height-1):
            s(r, left,          curses.ACS_VLINE)
            s(r, left+width-1,  curses.ACS_VLINE)

        if title:
            t = f" {title} "[:width - 4]
            col = left + (width - len(t)) // 2
            self._safe_addstr(top, col, t, attr)

    def _safe_addstr(self, row: int, col: int, text: str, attr: int = 0):
        rows, cols = self._stdscr.getmaxyx()
        if row < 0 or row >= rows or col < 0 or col >= cols:
            return
        max_len = cols - col - 1
        if max_len <= 0:
            return
        try:
            self._stdscr.addstr(row, col, text[:max_len], attr)
        except curses.error:
            pass

    def _draw_dialogue(self, top: int, left: int, height: int, width: int,
                       lines: list[str], scroll: int, max_scroll: int):
        self._draw_box(top, left, height, width, self.title)
        attr = curses.color_pair(_PAIR_DIALOGUE)

        for i, line in enumerate(lines):
            row = top + 1 + i
            if row >= top + height - 1:
                break
            self._safe_addstr(row, left + 2, line, attr)

        if scroll > 0:
            self._safe_addstr(top + 1, width - 3, "▲",
                              curses.color_pair(_PAIR_BORDER) | curses.A_BOLD)
        if scroll < max_scroll:
            self._safe_addstr(top + height - 2, width - 3, "▼",
                              curses.color_pair(_PAIR_BORDER) | curses.A_BOLD)

    def _draw_choices(self, top: int, left: int, height: int, width: int,
                      choices: list[str]):
        self._draw_box(top, left, height, width, "[ Choices ]")
        attr = curses.color_pair(_PAIR_CHOICE)

        inner_w = width - 4
        tags    = [f"[{i+1}] {c}" for i, c in enumerate(choices)]
        row     = top + 1

        single_line = "   ".join(tags)
        if len(single_line) <= inner_w:
            self._safe_addstr(row, left + 2, single_line, attr)
        else:
            col_w   = inner_w // 2
            left_c  = left + 2
            right_c = left + 2 + col_w
            for idx, tag in enumerate(tags):
                r = row + idx // 2
                c = left_c if idx % 2 == 0 else right_c
                if r < top + height - 1:
                    self._safe_addstr(r, c, tag[:col_w - 1], attr)

        hint = "↑↓ scroll · 1-9 choose"
        hint_col = width - len(hint) - 3
        self._safe_addstr(
            top + height - 2, max(left + 2, hint_col), hint,
            curses.color_pair(_PAIR_BORDER)
        )