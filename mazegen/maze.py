from typing import Optional

NORTH: int = 0b0001
EAST: int = 0b0010
SOUTH: int = 0b0100
WEST: int = 0b1000

ALL_WALLS: int = NORTH | EAST | SOUTH | WEST

OPPOSITE: dict[int, int] = {
    NORTH: SOUTH,
    SOUTH: NORTH,
    EAST: WEST,
    WEST: EAST,
}

DIRECTION_DELTA: dict[int, tuple[int, int]] = {
    NORTH: (-1, 0),
    SOUTH: (1, 0),
    EAST: (0, 1),
    WEST: (0, -1),
}

ALL_DIRECTIONS: list[int] = [NORTH, EAST, SOUTH, WEST]

DIGIT_4: list[list[int]] = [
    [1, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1]
]

DIGIT_2: list[list[int]] = [
    [1, 1, 1],
    [0, 0, 1],
    [1, 1, 1],
    [1, 0, 0],
    [1, 1, 1]
]

PATTERN_42: list[list[int]] = [
    [*DIGIT_4[r], 0, *DIGIT_2[r]] for r in range(5)
]

PATTERN_HEIGHT: int = 5
PATTERN_WIDTH: int = 7

MIN_PATTERN_WIDTH: int = PATTERN_WIDTH + 2
MIN_PATTERN_HEIGHT: int = PATTERN_HEIGHT + 2


class Maze:
    """
    Represents a rectangular maze grid.

    Each cell is stored as a 4-bit integer where each bit represents
    a wall direction (NORTH=1, EAST=2, SOUTH=4, WEST=8).
    A bit value of 1 means the wall is closed; 0 means open.

    All cells start fully closed (0xF). Walls are removed during
    generation to carve passages. The remove_wall method always
    updates both sides of a shared wall to maintain coherence.

    Attributes:
        width (int): Number of columns in the maze.
        height (int): Number of rows in the maze.
        entry (tuple[int, int]): Entry cell as (row, col).
        exit (tuple[int, int]): Exit cell as (row, col).
        grid (list[list[int]]): 2D list of wall bitmasks.
        visited (list[list[bool]]): Tracks visited cells during generation.
        pattern_42_cells (set[tuple[int, int]]): Cells used by '42' pattern.
        has_42_pattern (bool):
            Whether the '42' pattern was successfully stamped.
    """

    def __init__(self,
                 width: int,
                 height: int,
                 entry: tuple[int, int],
                 exit_cell: tuple[int, int]) -> None:
        """
        Initialize the maze grid with all walls closed.

        Args:
            width: Number of columns (must be >= 2).
            height: Number of rows (must be >= 2).
            entry: Entry cell coordinates as (row, col).
            exit_cell: Exit cell coordinates as (row, col).

        Raises:
            ValueError: If dimensions are invalid or entry/exit are out of
                        bounds or identical.
        """

        self._validate_params(width, height, entry, exit_cell)
        self.width: int = width
        self.height: int = height
        self.entry: tuple[int, int] = entry
        self.exit: tuple[int, int] = exit_cell

        self.grid: list[list[int]] = [
            [ALL_WALLS] * width for _ in range(height)
        ]

        self.visited: list[list[bool]] = [
            [False] * width for _ in range(height)
        ]

        self.pattern_42_cells: set[tuple[int, int]] = set()
        self.has_42_pattern: bool = False

    @staticmethod
    def _validate_params(
        width: int,
        height: int,
        entry: tuple[int, int],
        exit_cell: tuple[int, int],
            ) -> None:
        """
        Validate constructor parameters.

        Args:
            width: Maze width.
            height: Maze height.
            entry: Entry cell (row, col).
            exit_cell: Exit cell (row, col).

        Raises:
            ValueError: On any invalid parameter.
        """
        if width < 2 or height < 2:
            raise ValueError(
                f"Maze dimensions must be at least 2x2, got {width}x{height}"
            )

        entry_row, entry_col = entry
        exit_row, exit_col = exit_cell

        if not (0 <= entry_row < height and 0 <= entry_col < width):
            raise ValueError(
                f"Entry {entry} is outside maze bounds "
                f"({height} rows x {width} cols)"
            )

        if not (0 <= exit_row < height and 0 <= exit_col < width):
            raise ValueError(
                f"Exit {exit_cell} is outside maze bounds "
                f"({height} rows x {width} cols)"
            )

        if entry == exit_cell:
            raise ValueError(
                f"Entry and exit must be different cells, both given as "
                f"{entry}"
            )

    def get_cell(self, row: int, col: int) -> int:
        """
        Return the wall bitmask for a cell.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            Integer bitmask (0–15) representing which walls are closed.
        """
        return self.grid[row][col]

    def is_valid_cell(self, row: int, col: int) -> bool:
        """
        Check whether (row, col) is within maze bounds.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            True if the cell is inside the maze, False otherwise.
        """
        return 0 <= row < self.height and 0 <= col < self.width

    def is_visited(self, row: int, col: int) -> bool:
        """
        Check whether a cell has been visited during generation.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            True if visited, False otherwise.
        """
        return self.visited[row][col]

    def mark_visited(self, row: int, col: int) -> None:
        """
        Mark a cell as visited.

        Args:
            row: Row index.
            col: Column index.
        """
        self.visited[row][col] = True

    def remove_wall(self, row: int, col: int, direction: int) -> None:
        """
        Remove a wall between a cell and its neighbor in the given direction.

        Both the current cell and its neighbor are updated simultaneously
        to maintain wall coherence a shared wall is always either present
        on both sides or absent on both sides.

        Args:
            row: Row of the current cell.
            col: Column of the current cell.
            direction: One of NORTH, EAST, SOUTH, WEST.

        Raises:
            ValueError:
                If the neighbor in the given direction is out of bounds.
        """
        d_row, d_col = DIRECTION_DELTA[direction]
        n_row, n_col = row + d_row, col + d_col

        if not self.is_valid_cell(n_row, n_col):
            raise ValueError(
                f"Cannot remove wall at ({row}, {col} facing)"
                f"direction {direction}: neighbor ({n_row}, {n_col}) "
                f"is out of bounds"
            )

        self.grid[row][col] &= ~direction
        self.grid[n_row][n_col] &= ~OPPOSITE[direction]

    def has_wall(self, row: int, col: int, direction: int) -> bool:
        """
        Check whether a wall exists in a given direction from a cell.

        Args:
            row: Row index.
            col: Column index.
            direction: One of NORTH, EAST, SOUTH, WEST.

        Returns:
            True if the wall is closed, False if open.
        """
        return bool(self.grid[row][col] & direction)

    def get_open_neighbors(
        self, row: int, col: int
            ) -> list[tuple[int, int, int]]:
        """
        Return all neighbors reachable from (row, col) through open walls.

        Used by the solver to traverse the maze.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            List of (neighbor_row, neighbor_col, direction) tuples for each
            open wall leading to a valid in-bounds neighbor.
        """
        neighbors: list[tuple[int, int, int]] = []
        for direction in ALL_DIRECTIONS:
            if not self.has_wall(row, col, direction):
                d_row, d_col = DIRECTION_DELTA[direction]
                n_row, n_col = row + d_row, col + d_col
                if self.is_valid_cell(n_row, n_col):
                    neighbors.append((n_row, n_col, direction))
        return neighbors

    def get_unvisited_neighbors(
        self, row: int, col: int
            ) -> list[tuple[int, int, int]]:
        """
        Return all valid unvisited neighbors of (row, col).

        Used by the generator to find cells to carve into.
        Does not check walls only bounds and visited status.
        Skips cells that belong to the '42' pattern.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            List of (neighbor_row, neighbor_col, direction) tuples.
        """
        neighbors: list[tuple[int, int, int]] = []
        for direction in ALL_DIRECTIONS:
            d_row, d_col = DIRECTION_DELTA[direction]
            n_row, n_col = row + d_row, col + d_col
            if (
                    self.is_valid_cell(n_row, n_col)
                    and not self.is_visited(n_row, n_col)
                    and (n_row, n_col) not in self.pattern_42_cells
            ):
                neighbors.append((n_row, n_col, direction))
        return neighbors

    def stamp_42(self) -> bool:
        """
        Pre-place the '42' pattern on the grid before generation.

        The pattern is centered in the maze. Cells belonging to '42'
        are marked as fully closed (all walls = 0xF) and as visited
        so the generator skips them entirely.

        Returns:
            True if the pattern was successfully stamped.
            False if the maze is too small to fit the pattern.
        """
        if self.width < MIN_PATTERN_WIDTH or self.height < MIN_PATTERN_HEIGHT:
            self.has_42_pattern = False
            return False

        start_row: int = (self.height - PATTERN_HEIGHT) // 2
        start_col: int = (self.width - PATTERN_WIDTH) // 2

        for r in range(PATTERN_HEIGHT):
            for c in range(PATTERN_WIDTH):
                if PATTERN_42[r][c] == 1:
                    maze_row = start_row + r
                    maze_col = start_col + c

                    self.grid[maze_row][maze_col] = ALL_WALLS
                    self.visited[maze_row][maze_col] = True
                    self.pattern_42_cells.add((maze_row, maze_col))
        self.has_42_pattern = True
        return True

    def get_42_bounds(self) -> Optional[tuple[int, int, int, int]]:
        """
        Return the bounding box of the '42' pattern in the grid.

        Returns:
            Tuple of (start_row, start_col, end_row, end_col) if the
            pattern exists, None otherwise.
        """
        if not self.has_42_pattern or not self.pattern_42_cells:
            return None
        rows = [r for r, _ in self.pattern_42_cells]
        cols = [c for _, c in self.pattern_42_cells]
        return (min(rows), min(cols), max(rows), max(cols))

    def has_3x3_open_area(self, row: int, col: int) -> bool:
        """
        Check whether a 3x3 block starting at (row, col) is fully open.

        Used during generation and braiding to prevent open areas
        wider than 2 cells as required by the subject.

        A cell is considered 'open enough to contribute to a 3x3 area'
        if it has no internal walls (i.e., no walls toward its neighbors
        within the 3x3 block).

        Args:
            row: Top-left row of the 3x3 block to check.
            col: Top-left column of the 3x3 block to check.

        Returns:
            True if a forbidden 3x3 open area exists at this position.
        """
        for r in range(row, row + 3):
            for c in range(col, col + 3):
                if not self.is_valid_cell(r, c):
                    return False

        for r in range(row, row + 2):
            for c in range(col, col + 3):
                if self.has_wall(r, c, SOUTH):
                    return False

        for r in range(row, row + 3):
            for c in range(col, col + 2):
                if self.has_wall(r, c, EAST):
                    return False

        return True

    def would_create_3x3_open(self,
                              row: int,
                              col: int, direction: int) -> bool:
        """
        Check whether removing a wall would create a forbidden 3x3 open area.

        Should be called before removing a wall during braiding to enforce
        the corridor width constraint.

        Args:
            row: Row of the cell.
            col: Column of the cell.
            direction: Wall direction to be removed.

        Returns:
            True if removing this wall would create a 3x3 open area.
        """
        d_row, d_col = DIRECTION_DELTA[direction]
        n_row, n_col = row + d_row, col + d_col

        self.grid[row][col] &= ~direction
        self.grid[n_row][n_col] &= ~OPPOSITE[direction]

        found: bool = False
        for check_row in range(row - 2, row + 1):
            for check_col in range(col - 2, col + 1):
                if self.has_3x3_open_area(check_row, check_col):
                    found = True
                    break
            if found:
                break

        self.grid[row][col] |= direction
        self.grid[n_row][n_col] |= OPPOSITE[direction]

        return found

    def to_hex_grid(self) -> list[str]:
        """
        Serialize the maze grid to a list of hex strings.

        Each cell becomes one uppercase hex character (0–F).
        Each string in the returned list represents one row.

        Returns:
            List of strings, one per row, each containing width hex digits.

        Example:
            A 3x2 maze returns something like:
            ['9F3', 'C56']
        """
        return [
                ''.join(format(cell, 'X') for cell in row)
                for row in self.grid
                ]
