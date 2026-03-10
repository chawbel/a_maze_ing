from collections import deque
from typing import Optional

from mazegen.maze import (
    Maze,
    NORTH,
    EAST,
    SOUTH,
    WEST,
)

DIRECTION_LETTER: dict[int, str] = {
    NORTH: "N",
    EAST:  "E",
    SOUTH: "S",
    WEST:  "W",
}


class MazeSolver:
    """
    Solves a Maze using Breadth-First Search (BFS).

    BFS explores cells layer by layer from the entry cell, guaranteeing
    that the first time the exit is reached the path taken is the shortest
    possible (fewest steps).

    Attributes:
        maze (Maze): The Maze instance to solve.
    """

    def __init__(self, maze: Maze) -> None:
        """
        Initialize the solver with a generated Maze.

        Args:
            maze: A fully generated Maze instance.
        """
        self.maze: Maze = maze
        self._path: Optional[list[str]] = None

    def solve(self) -> list[str]:
        """
        Find the shortest path from entry to exit using BFS.

        The path is cached after the first call calling solve() again
        returns the cached result without re-running BFS.

        Returns:
            A list of single-character direction strings (e.g. ['N','E','S']).
            Returns an empty list if no path exists (should never happen in a
            valid fully-connected maze).
        """
        if self._path is not None:
            return self._path

        self._path = self._bfs()
        return self._path

    def path_string(self) -> str:
        """
        Return the solution path as a single concatenated string.

        Calls solve() internally if needed.

        Returns:
            A string like 'NEESSWN...' representing the shortest path.
            Returns an empty string if no path exists.
        """
        return "".join(self.solve())

    def _bfs(self) -> list[str]:
        """
        Run BFS from maze.entry to maze.exit.

        Uses get_open_neighbors() from the Maze class to follow only
        passages (open walls), so the solver never passes through walls.

        The algorithm tracks each visited cell and the direction taken to
        reach it, then reconstructs the path by walking back from the exit
        to the entry.

        Returns:
            Shortest path as a list of direction strings, or [] if unreachable.
        """
        start_row, start_col = self.maze.entry
        exit_row, exit_col = self.maze.exit

        queue: deque[tuple[int, int]] = deque()
        queue.append((start_row, start_col))

        came_from: dict[
            tuple[int, int],
            Optional[tuple[int, int, int]]
        ] = {}
        came_from[(start_row, start_col)] = None

        while queue:
            row, col = queue.popleft()

            if row == exit_row and col == exit_col:
                return self._reconstruct_path(came_from, exit_row, exit_col)

            for n_row, n_col, direction in self.maze.get_open_neighbors(
                row, col
            ):
                if (n_row, n_col) not in came_from:
                    came_from[(n_row, n_col)] = (row, col, direction)
                    queue.append((n_row, n_col))

        return []

    def _reconstruct_path(
        self,
        came_from: dict[
            tuple[int, int],
            Optional[tuple[int, int, int]]
        ],
        exit_row: int,
        exit_col: int,
    ) -> list[str]:
        """
        Walk back through the came_from map to build the solution path.

        The path is built in reverse (exit to entry) and then reversed before
        returning so it reads entry to exit.

        Args:
            came_from: Mapping from each visited cell to its parent info.
            exit_row:  Row of the exit cell.
            exit_col:  Column of the exit cell.

        Returns:
            Ordered list of direction strings from entry to exit.
        """
        path: list[str] = []
        current: tuple[int, int] = (exit_row, exit_col)

        while came_from[current] is not None:
            parent_info = came_from[current]
            assert parent_info is not None
            parent_row, parent_col, direction = parent_info
            path.append(DIRECTION_LETTER[direction])
            current = (parent_row, parent_col)

        path.reverse()
        return path
