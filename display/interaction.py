from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

from libmlx import (
    MLX_KEY_LEFT_ALT,
    MLX_KEY_LEFT_CONTROL,
    MLX_KEY_LEFT_SHIFT,
    MLX_KEY_RIGHT_CONTROL,
    MLX_KEY_RIGHT_SHIFT,
    MLX_KEY_RIGHT_ALT,
)
from mazegen.maze import Maze, NORTH, EAST, SOUTH, WEST, DIRECTION_DELTA

if TYPE_CHECKING:
    from display.renderer import MazeRenderer


KEY_ESC = 256
KEY_R = 82
KEY_S = 83
KEY_C = 67
KEY_F = 70
KEY_EQUAL = 61
KEY_MINUS = 45


THEMES = [
    {
        "C_BG": 0x000000,
        "C_WALL": 0xE8E8E8,
        "C_ENTRY": 0x00DD55,
        "C_EXIT": 0xFF3333,
        "C_PATH": 0xFFDD00,
        "C_PATH_BORDER": 0xFF8800,
        "C_42": 0xAA6600,
        "C_FRONTIER": 0xFF44FF,
    },
    {
        "C_BG": 0x0A1628,
        "C_WALL": 0x5BAAF5,
        "C_ENTRY": 0x44FF88,
        "C_EXIT": 0xFF4444,
        "C_PATH": 0xFFEE55,
        "C_PATH_BORDER": 0xFFAA00,
        "C_42": 0x00CCDD,
        "C_FRONTIER": 0xFF88FF,
    },
    {
        "C_BG": 0x0D1F0D,
        "C_WALL": 0x44BB55,
        "C_ENTRY": 0xAAFF44,
        "C_EXIT": 0xFF4422,
        "C_PATH": 0xFFFF88,
        "C_PATH_BORDER": 0xBBDD00,
        "C_42": 0xDDFF00,
        "C_FRONTIER": 0xFFFF44,
    },
    {
        "C_BG": 0x120800,
        "C_WALL": 0xFF7700,
        "C_ENTRY": 0x88FF44,
        "C_EXIT": 0xFF2244,
        "C_PATH": 0xFFDD88,
        "C_PATH_BORDER": 0xFF9900,
        "C_42": 0xFF0044,
        "C_FRONTIER": 0xFFEE00,
    },
    {
        "C_BG": 0x050A14,
        "C_WALL": 0x88DDFF,
        "C_ENTRY": 0x44FFCC,
        "C_EXIT": 0xFF4466,
        "C_PATH": 0xCCEEFF,
        "C_PATH_BORDER": 0x44AAFF,
        "C_42": 0xCC44FF,
        "C_FRONTIER": 0x44FFFF,
    },
]


THEME_NAMES = ["Classic", "Blueprint", "Forest", "Ember", "Ice"]


def _directions_to_cells(
    start: tuple[int, int], directions: list[str]
) -> list[tuple[int, int]]:
    """Convert solver direction list → (row, col) cell list for renderer."""
    _D = {"N": NORTH, "E": EAST, "S": SOUTH, "W": WEST}
    path = [start]
    row, col = start
    for letter in directions:
        dr, dc = DIRECTION_DELTA[_D[letter]]
        row += dr
        col += dc
        path.append((row, col))
    return path


@dataclass
class AppState:
    maze: Maze
    solution_cells: list[tuple[int, int]] = field(default_factory=list)
    show_solution: bool = False
    show_42: bool = True
    theme_index: int = 0
    mlx_ptr: object = None

    @property
    def active_theme(self):
        return THEMES[self.theme_index]

    @property
    def theme_name(self):
        return THEME_NAMES[self.theme_index]


class KeyHandler:
    """
    Wraps mlx_is_key_down into edge-triggered (press, not hold) events.

    Call .poll(mlx_mod, mlx_ptr) once per frame from the loop hook.
    Each watched key fires its action exactly once per press, ignoring hold.
    """

    def __init__(
        self,
        state: AppState,
        regenerate_cb: Callable,
        renderer: "MazeRenderer",
        mlx_mod,
        anim=None,
    ) -> None:
        self._state = state
        self._regen = regenerate_cb
        self._renderer = renderer
        self._mlx_mod = mlx_mod
        self._anim = anim
        self._down: set = set()

    def set_anim(self, anim) -> None:
        self._anim = anim

    def poll(self, mlx_ptr) -> None:
        """Call once per frame. Fires actions on key-down edges."""
        mod = self._mlx_mod
        is_down = lambda k: mod.mlx_is_key_down(mlx_ptr, k)

        ctrl_held = is_down(MLX_KEY_LEFT_CONTROL) or is_down(MLX_KEY_RIGHT_CONTROL)
        shift_held = is_down(MLX_KEY_LEFT_SHIFT) or is_down(MLX_KEY_RIGHT_SHIFT)
        alt_held = is_down(MLX_KEY_LEFT_ALT) or is_down(MLX_KEY_RIGHT_ALT)
        modifier_held = ctrl_held or shift_held or alt_held

        currently_down = {k for k in _WATCHED if is_down(k)}
        just_pressed = currently_down - self._down
        self._down = currently_down

        for key in just_pressed:
            if key == KEY_EQUAL and modifier_held:
                self._dispatch(key)
            elif key != KEY_EQUAL and not modifier_held:
                self._dispatch(key)

    def _dispatch(self, key: int) -> None:
        state = self._state
        renderer = self._renderer
        anim = self._anim

        if key == KEY_ESC:
            self._mlx_mod.mlx_close_window(state.mlx_ptr)
            return

        if key == KEY_R:
            new_maze, dirs = self._regen()
            state.maze = new_maze
            state.solution_cells = _directions_to_cells(new_maze.entry, dirs)
            _redraw(state, renderer)
            return

        if key == KEY_S:
            state.show_solution = not state.show_solution
            _redraw(state, renderer)
            return

        if key == KEY_C:
            state.theme_index = (state.theme_index + 1) % len(THEMES)
            renderer.apply_theme(state.active_theme)
            _redraw(state, renderer)
            return

        if key == KEY_F:
            state.show_42 = not state.show_42
            _redraw(state, renderer)
            return

        if anim is not None and anim.active:
            if key == KEY_EQUAL:
                anim.speed_index = min(anim.speed_index + 1, len(SPEED_STEPS) - 1)
            elif key == KEY_MINUS:
                anim.speed_index = max(anim.speed_index - 1, 0)


_WATCHED = {KEY_ESC, KEY_R, KEY_S, KEY_C, KEY_F, KEY_EQUAL, KEY_MINUS}

SPEED_STEPS = [1, 3, 8, 20, 60]


def _redraw(state: AppState, renderer: "MazeRenderer") -> None:
    renderer.render(
        state.maze,
        path=state.solution_cells if state.show_solution else [],
        show_42=state.show_42,
    )
