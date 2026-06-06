"""Reusable option picker: arrow-key menu with numbered-menu fallback.

Renders an arrow-key navigable list of AI suggestions plus a "type your own"
entry and an optional "let AI decide" entry when the terminal is interactive,
and degrades to a numbered ``rich`` menu otherwise. No third-party TUI
dependency: raw key reads use stdlib ``msvcrt`` (Windows) or ``termios``/``tty``
(POSIX), and any failure routes to the numbered fallback.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional, Sequence

from rich import box
from rich.live import Live
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from app.cli.console import console as _console
from app.core.i18n import t

Option = tuple[str, str, str]


@dataclass
class PickResult:
    kind: str
    value: str
    index: int


def _custom_label(label: Optional[str]) -> str:
    return label if label is not None else t("picker.custom")


def _auto_label(label: Optional[str]) -> str:
    return label if label is not None else t("picker.auto")


def _is_interactive() -> bool:
    try:
        return bool(_console.is_terminal and sys.stdin.isatty())
    except Exception:
        return False


def _read_key_windows() -> Optional[str]:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        return {"H": "up", "P": "down"}.get(ch2)
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x03":
        raise KeyboardInterrupt
    if ch == "\x1b":
        return "escape"
    if ch.isdigit():
        return ch
    return None


def _decode_escape_seq(seq: str) -> Optional[str]:
    """Map the bytes following an ESC to a key name.

    Returns 'up'/'down' for the arrow sequences we act on, and None for any
    other/unknown sequence (Left, Right, Home, End, F-keys, ...) so they are
    silently ignored — matching the Windows reader, which returns None for
    unmapped special keys rather than aborting.
    """
    return {"[A": "up", "[B": "down"}.get(seq)


def _read_key_posix() -> Optional[str]:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            # Distinguish a lone ESC (abort) from an escape sequence (arrows).
            # Raw mode sets VMIN=1/VTIME=0, so reading the continuation bytes of
            # a bare ESC would block forever. A real sequence delivers its bytes
            # immediately, so poll briefly and only read more if input is pending.
            ready, _, _ = select.select([fd], [], [], 0.05)
            if not ready:
                return "escape"
            seq = sys.stdin.read(2)
            return _decode_escape_seq(seq)
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch.isdigit():
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key() -> Optional[str]:
    if sys.platform == "win32":
        return _read_key_windows()
    return _read_key_posix()


def _build_rows(
    suggestions: Sequence[str],
    allow_custom: bool,
    allow_auto: bool,
    custom_label: Optional[str],
    auto_label: Optional[str],
) -> list[Option]:
    rows: list[Option] = [("suggestion", s, s) for s in suggestions]
    if allow_custom:
        rows.append(("custom", "", _custom_label(custom_label)))
    if allow_auto:
        rows.append(("auto", "", _auto_label(auto_label)))
    return rows


def _menu_text(prompt: str, rows: Sequence[Option], selected: int, n_sugg: int) -> Text:
    text = Text()
    if prompt:
        text.append(prompt + "\n", style="bold cyan")
    text.append(t("picker.hint_arrows") + "\n\n", style="dim")
    for i, (_kind, _value, label) in enumerate(rows):
        if i == n_sugg and i > 0:
            text.append("  " + "─" * 30 + "\n", style="dim")
        if i == selected:
            text.append(f"❯ {i + 1}. {label}\n", style="reverse bold")
        else:
            text.append(f"  {i + 1}. {label}\n")
    return text


def _resolve(rows: Sequence[Option], index: int) -> PickResult:
    kind, value, _label = rows[index]
    if kind == "custom":
        while True:
            typed = Prompt.ask(t("picker.custom_prompt")).strip()
            if typed:
                return PickResult("custom", typed, -1)
    if kind == "auto":
        return PickResult("auto", "", -1)
    return PickResult("suggestion", value, index)


def _pick_arrows_index(prompt: str, rows: Sequence[Option], n_sugg: int, default_index: int) -> int:
    """Run the arrow-key menu and return the chosen row index.

    Returns the index only; the caller resolves it AFTER the Live region has
    exited, so a custom-row Prompt.ask never fights the live display.
    """
    selected = default_index
    with Live(_menu_text(prompt, rows, selected, n_sugg), console=_console, auto_refresh=False) as live:
        while True:
            key = _read_key()
            if key == "up":
                selected = (selected - 1) % len(rows)
            elif key == "down":
                selected = (selected + 1) % len(rows)
            elif key is not None and key.isdigit():
                num = int(key) - 1
                if 0 <= num < len(rows):
                    selected = num
                    live.update(_menu_text(prompt, rows, selected, n_sugg), refresh=True)
                    return selected
            elif key == "enter":
                return selected
            elif key == "escape":
                raise KeyboardInterrupt
            live.update(_menu_text(prompt, rows, selected, n_sugg), refresh=True)


def _pick_numbered(prompt: str, rows: Sequence[Option], n_sugg: int, default_index: int) -> PickResult:
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("#", style="dim", justify="right")
    table.add_column("opt")
    for i, (kind, _value, label) in enumerate(rows):
        if i == n_sugg and i > 0:
            table.add_row("", "─" * 20)
        table.add_row(str(i + 1), label)
    _console.print(f"[bold cyan]{prompt}[/]")
    _console.print(table)
    while True:
        raw = Prompt.ask(t("picker.choose"), default=str(default_index + 1)).strip()
        if raw.isdigit():
            num = int(raw) - 1
            if 0 <= num < len(rows):
                return _resolve(rows, num)
            _console.print(f"[red]{t('general.invalid')}[/]")
            continue
        return PickResult("custom", raw, -1)


def pick(
    prompt: str,
    suggestions: Sequence[str],
    *,
    allow_custom: bool = True,
    allow_auto: bool = False,
    custom_label: Optional[str] = None,
    auto_label: Optional[str] = None,
    default_index: int = 0,
) -> PickResult:
    clean = [s for s in suggestions if isinstance(s, str) and s.strip()][:5]
    rows = _build_rows(clean, allow_custom, allow_auto, custom_label, auto_label)
    if not rows:
        rows = _build_rows([], True, allow_auto, custom_label, auto_label)
    n_sugg = len(clean)
    start = default_index if 0 <= default_index < len(rows) else 0
    if _is_interactive():
        try:
            chosen = _pick_arrows_index(prompt, rows, n_sugg, start)
        except KeyboardInterrupt:
            raise
        except Exception:
            return _pick_numbered(prompt, rows, n_sugg, start)
        return _resolve(rows, chosen)
    return _pick_numbered(prompt, rows, n_sugg, start)


def _numbered_index(prompt: str, rows: Sequence[Option], n_sugg: int, default_index: int) -> int:
    """Numbered-menu fallback for select(): loops until a valid index is given."""
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("#", style="dim", justify="right")
    table.add_column("opt")
    for i, (_kind, _value, label) in enumerate(rows):
        if i == n_sugg and i > 0:
            table.add_row("", "─" * 20)
        table.add_row(str(i + 1), label)
    if prompt:
        _console.print(f"[bold cyan]{prompt}[/]")
    _console.print(table)
    while True:
        raw = Prompt.ask(t("picker.choose_number"), default=str(default_index + 1)).strip()
        if raw.isdigit():
            num = int(raw) - 1
            if 0 <= num < len(rows):
                return num
        _console.print(f"[red]{t('general.invalid')}[/]")


def select(
    prompt: str,
    labels: Sequence[str],
    *,
    default_index: int = 0,
    divider_before: Optional[int] = None,
) -> int:
    """Pick one option from a fixed list of labels; returns the chosen index.

    Same arrow-key UI as pick() (↑/↓ + Enter, or a number), degrading to the
    numbered menu when non-interactive. ``divider_before`` draws a separator
    before that row index (e.g. before an action row like "new" / "done").
    """
    if not labels:
        raise ValueError("select() requires at least one option")
    rows: list[Option] = [("option", lbl, lbl) for lbl in labels]
    n = divider_before if divider_before is not None else len(rows)
    start = default_index if 0 <= default_index < len(rows) else 0
    if _is_interactive():
        try:
            return _pick_arrows_index(prompt, rows, n, start)
        except KeyboardInterrupt:
            raise
        except Exception:
            pass
    return _numbered_index(prompt, rows, n, start)


def confirm(
    prompt: str,
    *,
    default: bool = True,
    yes_label: Optional[str] = None,
    no_label: Optional[str] = None,
) -> bool:
    """Yes/No confirmation rendered as the same arrow-key menu. Returns True for yes."""
    yes = yes_label if yes_label is not None else t("picker.yes")
    no = no_label if no_label is not None else t("picker.no")
    return select(prompt, [yes, no], default_index=0 if default else 1) == 0
