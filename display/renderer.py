from __future__ import annotations
from typing import Optional
from mazegen.maze import Maze, NORTH, EAST, SOUTH, WEST
import ctypes

WIN_W: int = 1280
WIN_H: int = 720
MARGIN: int = 20
MIN_CELL: int = 4
WALL_T: int = 2

C_BG: int = 0x000000FF
C_WALL: int = 0xFFFFFFFF
C_ENTRY: int = 0x00CC44FF
C_EXIT: int = 0xDD2222FF
C_PATH: int = 0xFFDD00FF
C_PATH_BORDER: int = 0xFF8800FF
C_42: int = 0x3355AAFF


def _to_rgba(rrggbb: int) -> int:
    """Convert 0x00RRGGBB theme color to 0xRRGGBBAA."""
    return (
        ((rrggbb & 0xFF0000) << 8)
        | ((rrggbb & 0x00FF00) << 8)
        | ((rrggbb & 0x0000FF) << 8)
        | 0xFF
    )


def _cell_size(maze: Maze) -> int:
    return max(
        min((WIN_W - 2 * MARGIN) // maze.width, (WIN_H - 2 * MARGIN) // maze.height),
        MIN_CELL,
    )


def _grid_origin(maze: Maze, cs: int) -> tuple[int, int]:
    return (WIN_W - cs * maze.width) // 2, (WIN_H - cs * maze.height) // 2


def _cell_px(row: int, col: int, cs: int, x0: int, y0: int) -> tuple[int, int]:
    return x0 + col * cs, y0 + row * cs


def _fill(pixels, img_w, img_h, px, py, pw, ph, color):
    r = (color >> 24) & 0xFF
    g = (color >> 16) & 0xFF
    b = (color >> 8)  & 0xFF
    a =  color        & 0xFF

    x0c = max(px, 0)
    x1c = min(px + pw, img_w)
    y0c = max(py, 0)
    y1c = min(py + ph, img_h)

    if x0c >= x1c or y0c >= y1c:
        return

    row_bytes = (x1c - x0c) * 4
    row_buf   = (ctypes.c_uint8 * row_bytes)(*([r, g, b, a] * (x1c - x0c)))

    for y in range(y0c, y1c):
        offset = (y * img_w + x0c) * 4
        ctypes.memmove(
            ctypes.addressof(pixels.contents) + offset,
            row_buf,
            row_bytes,
        )

def _bg(pixels, color):
    _fill(pixels, WIN_W, WIN_H, 0, 0, WIN_W, WIN_H, color)


def _walls(pixels, maze, cs, x0, y0, color):
    t = WALL_T
    for row in range(maze.height):
        for col in range(maze.width):
            px, py = _cell_px(row, col, cs, x0, y0)
            w = maze.get_cell(row, col)
            if w & NORTH:
                _fill(pixels, WIN_W, WIN_H, px, py, cs + t, t, color)
            if w & SOUTH:
                _fill(pixels, WIN_W, WIN_H, px, py + cs, cs + t, t, color)
            if w & WEST:
                _fill(pixels, WIN_W, WIN_H, px, py, t, cs + t, color)
            if w & EAST:
                _fill(pixels, WIN_W, WIN_H, px + cs, py, t, cs + t, color)


def _highlight42(pixels, maze, cs, x0, y0, color):
    if not maze.has_42_pattern:
        return
    inset = max(WALL_T, cs // 6)
    size = max(cs - 2 * inset, 1)
    for row, col in maze.pattern_42_cells:
        px, py = _cell_px(row, col, cs, x0, y0)
        _fill(pixels, WIN_W, WIN_H, px + inset, py + inset, size, size, color)


def _markers(pixels, maze, cs, x0, y0, c_entry, c_exit):
    inset = max(WALL_T + 1, cs // 5)
    size = max(cs - 2 * inset, 1)
    for (row, col), color in [(maze.entry, c_entry), (maze.exit, c_exit)]:
        px, py = _cell_px(row, col, cs, x0, y0)
        _fill(pixels, WIN_W, WIN_H, px + inset, py + inset, size, size, color)


def _solution(pixels, maze, path, cs, x0, y0, c_path, c_border):
    if not path:
        return
    dot = max(2, cs // 4)
    bh = max(1, cs // 6)

    def ctr(row, col):
        px, py = _cell_px(row, col, cs, x0, y0)
        return px + cs // 2, py + cs // 2

    for i in range(len(path) - 1):
        cx0, cy0 = ctr(*path[i])
        cx1, cy1 = ctr(*path[i + 1])
        bx = min(cx0, cx1) - bh
        by = min(cy0, cy1) - bh
        _fill(
            pixels,
            WIN_W,
            WIN_H,
            bx,
            by,
            abs(cx1 - cx0) + 2 * bh,
            abs(cy1 - cy0) + 2 * bh,
            c_path,
        )
    for row, col in path:
        cx, cy = ctr(row, col)
        _fill(pixels, WIN_W, WIN_H, cx - dot, cy - dot, 2 * dot, 2 * dot, c_border)


class MazeRenderer:
    """
    Stateless MLX42 renderer.

    Usage:
        renderer = MazeRenderer(mlx_mod, mlx_ptr)
        renderer.render(maze)
        renderer.render(maze, path=cells, show_42=True)
        renderer.apply_theme(theme_dict)   # theme_dict uses 0x00RRGGBB values
        renderer.destroy()
    """

    def __init__(self, mlx_mod, mlx_ptr) -> None:
        """
        Args:
            mlx_mod: The imported libmlx module (from libmlx import *  → pass mlx).
            mlx_ptr: mlx_t* returned by mlx_mod.mlx_init().
        """
        self._m = mlx_mod
        self._ptr = mlx_ptr

        img = mlx_mod.mlx_new_image(mlx_ptr, WIN_W, WIN_H)
        if not img:
            raise RuntimeError("mlx_new_image failed")
        self._img = img

        if mlx_mod.mlx_image_to_window(mlx_ptr, img, 0, 0) == -1:
            raise RuntimeError("mlx_image_to_window failed")

        self._pixels = img.contents.pixels

        self.c_bg = C_BG
        self.c_wall = C_WALL
        self.c_entry = C_ENTRY
        self.c_exit = C_EXIT
        self.c_path = C_PATH
        self.c_path_border = C_PATH_BORDER
        self.c_42 = C_42

    def apply_theme(self, theme: dict) -> None:
        """Accept 0x00RRGGBB theme dict (from interaction.py) and convert."""

        def g(k, fb):
            v = theme.get(k)
            return _to_rgba(v) if v is not None else fb

        self.c_bg = g("C_BG", self.c_bg)
        self.c_wall = g("C_WALL", self.c_wall)
        self.c_entry = g("C_ENTRY", self.c_entry)
        self.c_exit = g("C_EXIT", self.c_exit)
        self.c_path = g("C_PATH", self.c_path)
        self.c_path_border = g("C_PATH_BORDER", self.c_path_border)
        self.c_42 = g("C_42", self.c_42)

    def render(
        self,
        maze: Maze,
        path: Optional[list[tuple[int, int]]] = None,
        show_42: bool = True,
    ) -> None:
        """Repaint the pixel buffer. MLX42 displays it next frame automatically."""
        cs = _cell_size(maze)
        x0, y0 = _grid_origin(maze, cs)
        px = self._pixels

        _bg(px, self.c_bg)
        if show_42:
            _highlight42(px, maze, cs, x0, y0, self.c_42)
        _walls(px, maze, cs, x0, y0, self.c_wall)
        _markers(px, maze, cs, x0, y0, self.c_entry, self.c_exit)
        if path:
            _solution(px, maze, path, cs, x0, y0, self.c_path, self.c_path_border)

    def paint_cell(self, maze: Maze, row: int, col: int, color: int) -> None:
        """Paint one cell interior — used by animation to highlight frontier."""
        cs = _cell_size(maze)
        x0, y0 = _grid_origin(maze, cs)
        px, py = _cell_px(row, col, cs, x0, y0)
        inset = max(WALL_T + 1, cs // 5)
        size = max(cs - 2 * inset, 1)
        _fill(self._pixels, WIN_W, WIN_H, px + inset, py + inset, size, size, color)

    def destroy(self) -> None:
        if self._img is not None:
            self._m.mlx_delete_image(self._ptr, self._img)
            self._img = None

    @staticmethod
    def window_size() -> tuple[int, int]:
        return WIN_W, WIN_H
