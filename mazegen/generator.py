import random
from typing import Generator, Iterator, Optional
from collections import namedtuple

from mazegen.maze import (
    DIRECTION_DELTA,
    MIN_PATTERN_HEIGHT,
    Maze,
    ALL_DIRECTIONS,
    MIN_PATTERN_WIDTH,
)

GenerationStep = namedtuple(
    "GenerationStep",
    ["row", "col", "prev_row", "prev_col", "direction", "backtrack", "done"],
)


class MazeGenerator:
    """
    Generates a maze using the Recursive Backtracker (DFS) algorithm.

    Attributes:
        maze (Maze): The Maze object being generated (modified in place).
        seed (Optional[int]): Random seed for reproducibility.
        perfect (bool): Whether to produce a perfect maze.
        braid_ratio (float): Fraction of dead ends to braid (0.0–1.0).
            Only used when perfect=False.
    """

    def __init__(
        self,
        maze: Maze,
        seed: Optional[int] = None,
        perfect: bool = True,
        braid_ratio: float = 1,
    ) -> None:
        """
        Initialise the generator.

        Args:
            maze: A freshly created Maze object (all walls closed, not yet
                  carved). The generator modifies it in place.
            seed: Optional integer seed for the random number generator.
                  Using the same seed on the same maze dimensions produces
                  an identical maze every time.
            perfect: If True, generate a perfect maze (one unique path)
        """
        self.maze: Maze = maze
        self.seed: Optional[int] = seed
        self.perfect: bool = perfect
        self.braid_ratio: float = max(0.0, min(1.0, braid_ratio))
        self.rng: random.Random = random.Random(seed)

    def generate(self) -> Generator[GenerationStep, None, None]:
        """
        Run the Recursive Backtracker algorithm, yielding after each step.

        The '42' pattern is stamped before generation begins (if the maze
        is large enough).

        Yields:
            GenerationStep: One per carve or backtrack action, plus a final
            step with done=True when generation is complete.
        """
        if not self.maze.stamp_42():
            min_width = MIN_PATTERN_WIDTH
            min_height = MIN_PATTERN_HEIGHT
            print(
                "Warning: maze is too small to fit the '42' pattern "
                "(minimum "
                f"{min_width}"
                " cols x "
                f"{min_height}"
                " rows required)"
            )

        self.rng = random.Random(self.seed)

        start_row, start_col = self.maze.entry
        yield from self.backtrack(start_row, start_col)

        if not self.perfect:
            self.braid()

    def generate_full(self) -> None:
        """
        Run the full generation algorithm to completion without yielding.
        """
        for _ in self.generate():
            pass

    def backtrack(self,
                  start_row: int,
                  start_col: int) -> Iterator[GenerationStep]:
        """
        Recursive Backtracker implemented iteratively using an explicit stack.

       Args:
            start_row: Row of the starting cell (usually entry).
            start_col: Column of the starting cell (usually entry).

        Yields:
            GenerationStep for each carve or backtrack, ending with a
            final step where done=True.
        """
        maze = self.maze
        maze.mark_visited(start_row, start_col)

        stack: list[tuple[int, int]] = [(start_row, start_col)]

        prev_row: int = start_row
        prev_col: int = start_col
        prev_direction: int = 0

        while stack:
            row, col = stack[-1]
            neighbors = maze.get_unvisited_neighbors(row, col)

            if neighbors:
                n_row, n_col, direction = self.rng.choice(neighbors)

                maze.remove_wall(row, col, direction)
                maze.mark_visited(n_row, n_col)
                stack.append((n_row, n_col))

                prev_direction = direction
                yield GenerationStep(
                    row=n_row,
                    col=n_col,
                    prev_row=row,
                    prev_col=col,
                    direction=direction,
                    backtrack=False,
                    done=False,
                )

                prev_row = n_row
                prev_col = n_col
            else:
                stack.pop()
                if stack:
                    back_row, back_col = stack[-1]
                    yield GenerationStep(
                        row=back_row,
                        col=back_col,
                        prev_row=row,
                        prev_col=col,
                        direction=prev_direction,
                        backtrack=True,
                        done=False,
                    )
        yield GenerationStep(
            row=prev_row,
            col=prev_col,
            prev_row=prev_row,
            prev_col=prev_col,
            direction=prev_direction,
            backtrack=False,
            done=True,
        )

    def braid(self) -> None:
        """
        Introduce loops into a perfect maze by removing extra walls.

        The braid_ratio attribute controls what fraction of dead ends are
        braided.
        """
        maze = self.maze
        dead_ends: list[tuple[int, int]] = []

        for row in range(maze.height):
            for col in range(maze.width):
                if (row, col) in maze.pattern_42_cells:
                    continue
                open_count = sum(
                    1
                    for direction in ALL_DIRECTIONS
                    if not maze.has_wall(row, col, direction)
                    and maze.is_valid_cell(
                        row + DIRECTION_DELTA[direction][0],
                        col + DIRECTION_DELTA[direction][1],
                    )
                )
                if open_count == 1:
                    dead_ends.append((row, col))
        self.rng.shuffle(dead_ends)
        braid_count = int(len(dead_ends) * self.braid_ratio)
        candidates = dead_ends[:braid_count]

        for row, col in candidates:
            safe_walls: list[int] = []
            for direction in ALL_DIRECTIONS:
                if not maze.has_wall(row, col, direction):
                    continue
                d_row, d_col = DIRECTION_DELTA[direction]
                n_row, n_col = row + d_row, col + d_col

                if not maze.is_valid_cell(n_row, n_col):
                    continue
                if (n_row, n_col) in maze.pattern_42_cells:
                    continue
                if not maze.would_create_3x3_open(row, col, direction):
                    safe_walls.append(direction)

            if safe_walls:
                chosen = self.rng.choice(safe_walls)
                maze.remove_wall(row, col, chosen)
