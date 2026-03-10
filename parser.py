from typing import Optional


MANDATORY_KEYS: set[str] = {
    "WIDTH",
    "HEIGHT",
    "ENTRY",
    "EXIT",
    "OUTPUT_FILE",
    "PERFECT",
}


class MazeConfig:
    """
    Parses and validates a maze configuration file.
    Reads a KEY=VALUE config file, validates all mandatory fields,
    and exposes the parsed values as typed attributes.

    Attributes:
        width (int): Number of columns in the maze.
        height (int): Number of rows in the maze.
        entry (tuple[int, int]): Entry cell as (row, col).
        exit (tuple[int, int]): Exit cell as (row, col).
        output_file (str): Path to the output file.
        perfect (bool): Whether the maze should be perfect.
        seed (Optional[int]): Random seed for reproducibility.
    """
    def __init__(self, filepath: str) -> None:
        self.height: int = 0
        self.width: int = 0
        self.entry: tuple[int, int] = (0, 0)
        self.exit: tuple[int, int] = (0, 0)
        self.seed: Optional[int] = 0
        self.perfect: bool = True
        self.output_file: str = ""
        self.animate: bool = False

        self.parse(filepath)

    def parse(self, filepath: str) -> None:
        """
        Read and parse the configuration file.

        filepath: Path to the configuration file.
        """
        raw: dict[str, str] = {}

        try:
            with open(filepath, "r") as f:
                for line_number, line in enumerate(f, start=1):
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue

                    if "=" not in line:
                        raise ValueError(
                            f"Line {line_number}: invalid format "
                            f"'{line}' (expected KEY=VALUE)."
                        )

                    key, _, value = line.partition("=")
                    key = key.strip().upper()
                    value = value.strip()

                    if not key:
                        raise ValueError(
                                f"Line {line_number}: empty key found.")

                    raw[key] = value

        except FileNotFoundError:
            raise FileNotFoundError(
                    f"Configuration file '{filepath}' not found.")

        self.validate_mandatory_keys(raw)
        self.populate(raw)
        self.validate_bounds()

    def validate_mandatory_keys(self, raw: dict[str, str]) -> None:
        """
        Ensure all mandatory keys are present.

        raw: Dictionary of raw parsed key-value pairs.
        """
        missing = MANDATORY_KEYS - raw.keys()
        if missing:
            raise ValueError(
                "Missing mandatory configuration keys: "
                f"{', '.join(sorted(missing))}."
            )

    def populate(self, raw: dict[str, str]) -> None:
        """
        Convert raw string values into typed attributes.

        raw: Dictionary of raw parsed key-value pairs.

        """
        self.width = self.parse_positive_int(raw["WIDTH"], "WIDTH")
        self.height = self.parse_positive_int(raw["HEIGHT"], "HEIGHT")
        self.entry = self.parse_coordinates(raw["ENTRY"], "ENTRY")
        self.exit = self.parse_coordinates(raw["EXIT"], "EXIT")
        self.output_file = self.parse_output_file(raw["OUTPUT_FILE"])
        self.perfect = self.parse_bool(raw["PERFECT"], "PERFECT")

        if "ANIMATE" in raw:
            self.animate = self.parse_bool(raw["ANIMATE"], "ANIMATE")

        if "SEED" in raw:
            self.seed = self.parse_int(raw["SEED"], "SEED")

    def validate_bounds(self) -> None:
        """
        Validate that entry and exit are inside maze bounds and not identical.
        """
        if self.width < 2 or self.height < 2:
            raise ValueError(
                "Maze dimensions must be at least 2x2, "
                f"got {self.width}x{self.height}."
            )

        e_row, e_col = self.entry
        if not (0 <= e_row < self.height and 0 <= e_col < self.width):
            raise ValueError(
                f"ENTRY {self.entry} is outside maze bounds "
                f"({self.height} rows x {self.width} cols)."
            )

        x_row, x_col = self.exit
        if not (0 <= x_row < self.height and 0 <= x_col < self.width):
            raise ValueError(
                f"EXIT {self.exit} is outside maze bounds "
                f"({self.height} rows x {self.width} cols)."
            )

        if self.entry == self.exit:
            raise ValueError(
                "ENTRY and EXIT must be different cells, "
                f"both given as {self.entry}."
            )

    def parse_positive_int(self, value: str, key: str) -> int:
        """
        Parse a string as a positive integer.

        value: Raw string value.
        key: Config key name (for error messages).

        Returns:
            Parsed positive integer.
        """
        try:
            result = int(value)
        except ValueError:
            raise ValueError(f"{key} must be an integer, got '{value}'.")
        if result <= 0:
            raise ValueError(
                    f"{key} must be a positive integer, got {result}.")
        return result

    def parse_int(self, value: str, key: str) -> int:
        """
        Parse a string as an integer.

        value: Raw string value.
        key: Config key name (for error messages).

        Returns:
            Parsed integer.
        """
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"{key} must be an integer, got '{value}'.")

    def parse_coordinates(self, value: str, key: str) -> tuple[int, int]:
        """
        Parse a coordinate string of the form 'x,y' into (row, col).

        value: Raw coordinate string, e.g. '0,0' or '19,14'.
        key: Config key name (for error messages).

        Returns:
            Tuple of (row, col).
        """
        parts = value.split(",")
        if len(parts) != 2:
            raise ValueError(f"{key} must be in 'x,y' format, got '{value}'.")
        try:
            col = int(parts[0].strip())
            row = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                    f"{key} coordinates must be integers, got '{value}'.")
        if col < 0 or row < 0:
            raise ValueError(
                    f"{key} coordinates must be non-negative, got '{value}'.")
        return (row, col)

    def parse_bool(self, value: str, key: str) -> bool:
        """
        Parse a string as a boolean (True/False).

        value: Raw string value.
        key: Config key name (for error messages).

        Returns:
            Parsed boolean.
        """
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        raise ValueError(f"{key} must be 'True/true/TRUE' "
                         "or 'False/false/FALSE', "
                         f"got '{value}'.")

    def parse_output_file(self, value: str) -> str:
        """
        Validate and return the output file path.

        value: Raw string value.

        Returns:
            The output file path string.
        """
        if not value:
            raise ValueError("OUTPUT_FILE must not be empty.")
        return value
