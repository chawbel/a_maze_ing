import sys
import signal
import ctypes
from typing import Optional

from mazegen.maze import Maze
from mazegen.generator import MazeGenerator
from mazegen.solver import MazeSolver
from parser import MazeConfig

from libmlx import mlx, mlx_loop_hook_func

from display.renderer import MazeRenderer, WIN_W, WIN_H
from display.interaction import (
    AppState, KeyHandler, _directions_to_cells,
    SPEED_STEPS,
)

_mlx_ptr = None

def _signal_handler(sig, frame):
    """Clean shutdown on Ctrl+C (avoids GLFW callback issues on exit)."""
    if _mlx_ptr is not None:
        mlx.mlx_terminate(_mlx_ptr)
    sys.exit(0)


def write_output(maze: Maze, solver: MazeSolver, filepath: str) -> None:
    entry_row, entry_col = maze.entry
    exit_row,  exit_col  = maze.exit
    with open(filepath, "w") as f:
        for row in maze.to_hex_grid():
            f.write(row + "\n")
        f.write("\n")
        f.write(f"{entry_col},{entry_row}\n")
        f.write(f"{exit_col},{exit_row}\n")
        f.write(solver.path_string() + "\n")


def _build_maze(config: MazeConfig) -> Maze:
    return Maze(width=config.width, height=config.height,
                entry=config.entry, exit_cell=config.exit)


def _make_regen_cb(config: MazeConfig):
    """Return closure: builds + generates + solves a fresh maze, returns (maze, dirs)."""
    def _regen():
        maze = _build_maze(config)
        MazeGenerator(maze, seed=None, perfect=config.perfect).generate_full()
        solver = MazeSolver(maze)
        return maze, solver.solve()
    return _regen


class AnimationState:
    C_FRONTIER = (0xFF << 24) | (0x44 << 16) | (0xFF << 8) | 0xFF

    def __init__(self, gen_iter):
        self._iter       = gen_iter
        self.active      = True
        self.speed_index = 2
        self.frontier    = None

    def advance(self, state: AppState, renderer: MazeRenderer) -> None:
        for _ in range(SPEED_STEPS[self.speed_index]):
            try:
                step = next(self._iter)
                if step.done:
                    self._finish(state, renderer)
                    return
                self.frontier = (step.row, step.col)
            except StopIteration:
                self._finish(state, renderer)
                return
        renderer.render(state.maze, path=[], show_42=state.show_42)
        if self.frontier:
            renderer.paint_cell(state.maze, *self.frontier, self.C_FRONTIER)

    def _finish(self, state: AppState, renderer: MazeRenderer) -> None:
        self.active   = False
        self.frontier = None
        solver = MazeSolver(state.maze)
        state.solution_cells = _directions_to_cells(state.maze.entry, solver.solve())
        renderer.render(state.maze,
                        path    = state.solution_cells if state.show_solution else [],
                        show_42 = state.show_42)


def main() -> None:
    global _mlx_ptr

    signal.signal(signal.SIGINT, _signal_handler)

    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py <config_file>", file=sys.stderr)
        sys.exit(1)

    try:
        config = MazeConfig(sys.argv[1])
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    animate: bool = getattr(config, "animate", False)

    try:
        maze      = _build_maze(config)
        generator = MazeGenerator(maze, seed=config.seed, perfect=config.perfect)

        if animate:
            gen_iter = generator.generate()
        else:
            generator.generate_full()
            gen_iter = None

    except ValueError as e:
        print(f"Maze error: {e}", file=sys.stderr)
        sys.exit(1)

    if not animate:
        try:
            solver = MazeSolver(maze)
            write_output(maze, solver, config.output_file)
            print(f"Maze written to {config.output_file}")
            solution_cells = _directions_to_cells(maze.entry, solver.solve())
        except (ValueError, OSError) as e:
            print(f"Output error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        solution_cells = []

    title   = b"A-Maze-ing  |  R=new  S=solution  C=colour  F=42  ESC=quit"
    mlx_ptr = mlx.mlx_init(WIN_W, WIN_H, title, True)
    if not mlx_ptr:
        err = mlx.mlx_strerror(mlx.mlx_get_errno()).decode()
        print(f"mlx_init failed: {err}", file=sys.stderr)
        sys.exit(1)
    _mlx_ptr = mlx_ptr

    try:
        renderer = MazeRenderer(mlx, mlx_ptr)
    except RuntimeError as e:
        print(f"Renderer error: {e}", file=sys.stderr)
        mlx.mlx_terminate(mlx_ptr)
        sys.exit(1)

    state = AppState(
        maze           = maze,
        solution_cells = solution_cells,
        show_solution  = False,
        show_42        = True,
        theme_index    = 0,
        mlx_ptr        = mlx_ptr,
    )

    anim: Optional[AnimationState] = None
    if animate and gen_iter is not None:
        anim = AnimationState(gen_iter)

    regen_cb   = _make_regen_cb(config)
    key_handler = KeyHandler(state, regen_cb, renderer, mlx, anim)

    renderer.render(maze, path=[], show_42=state.show_42)

    @mlx_loop_hook_func
    def _frame(param):
        key_handler.poll(mlx_ptr)
        if anim is not None and anim.active:
            anim.advance(state, renderer)

    mlx.mlx_loop_hook(mlx_ptr, _frame, ctypes.cast(mlx_ptr, ctypes.c_void_p))

    mlx.mlx_loop(mlx_ptr)

    renderer.destroy()
    mlx.mlx_terminate(mlx_ptr)


if __name__ == "__main__":
    main()
