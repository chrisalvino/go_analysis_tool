"""Board state management for Go game."""

from typing import Set, Tuple, Optional, List
from enum import Enum


class Stone(Enum):
    """Represents the color of a stone."""
    EMPTY = 0
    BLACK = 1
    WHITE = 2


class Board:
    """Represents a Go board with stones and captures."""

    def __init__(self, size: int = 19):
        """Initialize a board of given size (9, 13, or 19).

        Args:
            size: Board size (default 19)
        """
        if size not in (9, 13, 19):
            raise ValueError("Board size must be 9, 13, or 19")

        self.size = size
        self.board = [[Stone.EMPTY for _ in range(size)] for _ in range(size)]
        self.captures = {Stone.BLACK: 0, Stone.WHITE: 0}

    def is_valid_position(self, row: int, col: int) -> bool:
        """Check if position is on the board.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            True if position is valid
        """
        return 0 <= row < self.size and 0 <= col < self.size

    def get_stone(self, row: int, col: int) -> Stone:
        """Get the stone at a position.

        Args:
            row: Row index
            col: Column index

        Returns:
            Stone at position
        """
        if not self.is_valid_position(row, col):
            raise ValueError(f"Invalid position: ({row}, {col})")
        return self.board[row][col]

    def set_stone(self, row: int, col: int, stone: Stone) -> None:
        """Set a stone at a position (internal use).

        Args:
            row: Row index
            col: Column index
            stone: Stone to place
        """
        if not self.is_valid_position(row, col):
            raise ValueError(f"Invalid position: ({row}, {col})")
        self.board[row][col] = stone

    def get_adjacent_positions(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get all adjacent positions (up, down, left, right).

        Args:
            row: Row index
            col: Column index

        Returns:
            List of adjacent positions
        """
        adjacent = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_position(new_row, new_col):
                adjacent.append((new_row, new_col))
        return adjacent

    def get_group(self, row: int, col: int) -> Set[Tuple[int, int]]:
        """Get all stones in the group containing the position.

        Args:
            row: Row index
            col: Column index

        Returns:
            Set of positions in the group
        """
        stone = self.get_stone(row, col)
        if stone == Stone.EMPTY:
            return set()

        group = set()
        to_check = [(row, col)]

        while to_check:
            r, c = to_check.pop()
            if (r, c) in group:
                continue

            group.add((r, c))

            for adj_r, adj_c in self.get_adjacent_positions(r, c):
                if self.get_stone(adj_r, adj_c) == stone and (adj_r, adj_c) not in group:
                    to_check.append((adj_r, adj_c))

        return group

    def count_liberties(self, row: int, col: int) -> int:
        """Count liberties of the group containing the position.

        Args:
            row: Row index
            col: Column index

        Returns:
            Number of liberties
        """
        group = self.get_group(row, col)
        if not group:
            return 0

        liberties = set()
        for r, c in group:
            for adj_r, adj_c in self.get_adjacent_positions(r, c):
                if self.get_stone(adj_r, adj_c) == Stone.EMPTY:
                    liberties.add((adj_r, adj_c))

        return len(liberties)

    def remove_group(self, row: int, col: int) -> int:
        """Remove a group of stones from the board.

        Args:
            row: Row index
            col: Column index

        Returns:
            Number of stones removed
        """
        group = self.get_group(row, col)
        for r, c in group:
            self.board[r][c] = Stone.EMPTY
        return len(group)

    def clone(self) -> 'Board':
        """Create a deep copy of the board.

        Returns:
            New Board instance with same state
        """
        new_board = Board(self.size)
        new_board.board = [row[:] for row in self.board]
        new_board.captures = self.captures.copy()
        return new_board

    def clear(self) -> None:
        """Clear all stones from the board."""
        self.board = [[Stone.EMPTY for _ in range(self.size)] for _ in range(self.size)]
        self.captures = {Stone.BLACK: 0, Stone.WHITE: 0}

    def __str__(self) -> str:
        """String representation of the board."""
        lines = []
        for row in self.board:
            line = ""
            for stone in row:
                if stone == Stone.BLACK:
                    line += "X "
                elif stone == Stone.WHITE:
                    line += "O "
                else:
                    line += ". "
            lines.append(line)
        return "\n".join(lines)
