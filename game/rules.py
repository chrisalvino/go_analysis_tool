"""Go game rules implementation."""

from typing import Optional, Tuple, Set
from game.board import Board, Stone


class MoveResult:
    """Result of attempting a move."""

    def __init__(self, valid: bool, message: str = "", captures: int = 0):
        """Initialize move result.

        Args:
            valid: Whether the move is valid
            message: Error message if invalid
            captures: Number of stones captured
        """
        self.valid = valid
        self.message = message
        self.captures = captures


class GoRules:
    """Go game rules engine."""

    def __init__(self, board: Board):
        """Initialize rules engine.

        Args:
            board: The board to apply rules to
        """
        self.board = board
        self.ko_point: Optional[Tuple[int, int]] = None

    def is_suicide(self, row: int, col: int, stone: Stone) -> bool:
        """Check if a move would be suicide.

        A move is suicide if it results in the played stone's group
        having no liberties.

        Args:
            row: Row index
            col: Column index
            stone: Stone color to place

        Returns:
            True if move is suicide
        """
        # Temporarily place the stone
        original = self.board.get_stone(row, col)
        self.board.set_stone(row, col, stone)

        # Check if this group would have liberties
        has_liberties = self.board.count_liberties(row, col) > 0

        # Restore original state
        self.board.set_stone(row, col, original)

        return not has_liberties

    def get_captured_groups(self, row: int, col: int, stone: Stone) -> Set[Tuple[int, int]]:
        """Get all opponent groups that would be captured by this move.

        Args:
            row: Row index
            col: Column index
            stone: Stone color to place

        Returns:
            Set of positions of captured stones
        """
        opponent = Stone.WHITE if stone == Stone.BLACK else Stone.BLACK
        captured = set()

        # Check adjacent groups
        for adj_r, adj_c in self.board.get_adjacent_positions(row, col):
            if self.board.get_stone(adj_r, adj_c) == opponent:
                # Temporarily place the stone to check captures
                original = self.board.get_stone(row, col)
                self.board.set_stone(row, col, stone)

                # If adjacent group has no liberties, it's captured
                if self.board.count_liberties(adj_r, adj_c) == 0:
                    captured.update(self.board.get_group(adj_r, adj_c))

                # Restore
                self.board.set_stone(row, col, original)

        return captured

    def is_valid_move(self, row: int, col: int, stone: Stone) -> MoveResult:
        """Check if a move is valid according to Go rules.

        Args:
            row: Row index
            col: Column index
            stone: Stone color to place

        Returns:
            MoveResult indicating validity and details
        """
        # Check position is on board
        if not self.board.is_valid_position(row, col):
            return MoveResult(False, "Position is off the board")

        # Check position is empty
        if self.board.get_stone(row, col) != Stone.EMPTY:
            return MoveResult(False, "Position is already occupied")

        # Check for ko
        if self.ko_point == (row, col):
            return MoveResult(False, "Ko rule violation")

        # Check for captures
        captured = self.get_captured_groups(row, col, stone)

        # If there are captures, the move is valid (not suicide)
        if captured:
            return MoveResult(True, "", len(captured))

        # If no captures, check for suicide
        if self.is_suicide(row, col, stone):
            return MoveResult(False, "Suicide move not allowed")

        return MoveResult(True, "", 0)

    def play_move(self, row: int, col: int, stone: Stone) -> MoveResult:
        """Play a move on the board.

        Args:
            row: Row index
            col: Column index
            stone: Stone color to place

        Returns:
            MoveResult indicating success and details
        """
        result = self.is_valid_move(row, col, stone)
        if not result.valid:
            return result

        # Place the stone
        self.board.set_stone(row, col, stone)

        # Remove captured groups
        captured_positions = self.get_captured_groups(row, col, stone)
        total_captures = 0

        for cap_r, cap_c in captured_positions:
            # Only remove if this stone still exists (avoid double removal)
            if self.board.get_stone(cap_r, cap_c) != Stone.EMPTY:
                count = self.board.remove_group(cap_r, cap_c)
                total_captures += count

        # Update capture count
        self.board.captures[stone] += total_captures

        # Update ko point
        # Ko applies when exactly one stone is captured and the capturing
        # stone would be immediately recapturable
        self.ko_point = None
        if total_captures == 1:
            # Check if this was a single stone captured
            if len(captured_positions) == 1:
                # Check if the placed stone's group has only one liberty
                if self.board.count_liberties(row, col) == 1:
                    # The ko point is the position of the captured stone
                    self.ko_point = list(captured_positions)[0]

        result.captures = total_captures
        return result

    def pass_turn(self) -> None:
        """Pass the turn (clears ko)."""
        self.ko_point = None

    def clear_ko(self) -> None:
        """Clear the ko point."""
        self.ko_point = None
