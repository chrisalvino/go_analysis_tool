"""Board canvas for rendering Go board."""

import tkinter as tk
from typing import Optional, Tuple, Callable, Set
from game.board import Board, Stone


class BoardCanvas(tk.Canvas):
    """Canvas widget for displaying and interacting with Go board."""

    def __init__(self, parent, board: Board, **kwargs):
        """Initialize the board canvas.

        Args:
            parent: Parent widget
            board: Board to display
            **kwargs: Additional canvas options
        """
        self.board = board
        self.cell_size = 35
        self.margin = 25

        # Calculate canvas size
        width = 2 * self.margin + (board.size - 1) * self.cell_size
        height = 2 * self.margin + (board.size - 1) * self.cell_size

        super().__init__(parent, width=width, height=height, bg='#DCB35C', **kwargs)

        # Interaction state
        self.click_callback: Optional[Callable[[int, int], None]] = None
        self.last_move: Optional[Tuple[int, int]] = None
        self.error_moves: Set[Tuple[int, int]] = set()
        self.hover_pos: Optional[Tuple[int, int]] = None
        self.preview_stone: Optional[Stone] = None
        self.top_move_candidates: list = []  # List of (row, col, rank) for top moves

        # Bind events
        self.bind('<Button-1>', self._on_click)
        self.bind('<Motion>', self._on_motion)

        # Draw initial board
        self.redraw()

    def set_click_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set the callback for click events.

        Args:
            callback: Function to call with (row, col) when clicked
        """
        self.click_callback = callback

    def set_board(self, board: Board) -> None:
        """Set a new board and reconfigure canvas.

        Args:
            board: New board to display
        """
        self.board = board

        # Reconfigure canvas size for new board
        width = 2 * self.margin + (board.size - 1) * self.cell_size
        height = 2 * self.margin + (board.size - 1) * self.cell_size
        self.config(width=width, height=height)

        # Clear markers
        self.last_move = None
        self.error_moves = set()

        # Redraw with new board
        self.redraw()

    def set_preview_stone(self, stone: Optional[Stone]) -> None:
        """Set the stone color for preview.

        Args:
            stone: Stone color to preview, or None to disable
        """
        self.preview_stone = stone

    def redraw(self) -> None:
        """Redraw the entire board."""
        self.delete('all')
        self._draw_grid()
        self._draw_star_points()
        self._draw_coordinates()
        self._draw_stones()
        self._draw_last_move_marker()
        self._draw_error_markers()
        self._draw_move_candidates()

    def _draw_grid(self) -> None:
        """Draw the board grid."""
        size = self.board.size

        # Draw horizontal lines
        for i in range(size):
            y = self.margin + i * self.cell_size
            x1 = self.margin
            x2 = self.margin + (size - 1) * self.cell_size
            self.create_line(x1, y, x2, y, fill='black', width=1)

        # Draw vertical lines
        for i in range(size):
            x = self.margin + i * self.cell_size
            y1 = self.margin
            y2 = self.margin + (size - 1) * self.cell_size
            self.create_line(x, y1, x, y2, fill='black', width=1)

    def _draw_star_points(self) -> None:
        """Draw star points on the board."""
        size = self.board.size
        radius = 3

        # Star point positions based on board size
        if size == 19:
            points = [(3, 3), (3, 9), (3, 15), (9, 3), (9, 9), (9, 15), (15, 3), (15, 9), (15, 15)]
        elif size == 13:
            points = [(3, 3), (3, 9), (6, 6), (9, 3), (9, 9)]
        elif size == 9:
            points = [(2, 2), (2, 6), (4, 4), (6, 2), (6, 6)]
        else:
            points = []

        for row, col in points:
            x = self.margin + col * self.cell_size
            y = self.margin + row * self.cell_size
            self.create_oval(x - radius, y - radius, x + radius, y + radius, fill='black')

    def _draw_coordinates(self) -> None:
        """Draw coordinate labels."""
        size = self.board.size

        # Column labels (A, B, C, ...)
        for i in range(size):
            x = self.margin + i * self.cell_size
            label = chr(ord('A') + i if i < 8 else ord('A') + i + 1)  # Skip 'I'
            self.create_text(x, self.margin - 12, text=label, font=('Arial', 10))
            self.create_text(x, self.margin + (size - 1) * self.cell_size + 12, text=label, font=('Arial', 10))

        # Row labels (1, 2, 3, ...)
        for i in range(size):
            y = self.margin + i * self.cell_size
            label = str(size - i)
            self.create_text(self.margin - 12, y, text=label, font=('Arial', 10))
            self.create_text(self.margin + (size - 1) * self.cell_size + 12, y, text=label, font=('Arial', 10))

    def _draw_stones(self) -> None:
        """Draw all stones on the board."""
        for row in range(self.board.size):
            for col in range(self.board.size):
                stone = self.board.get_stone(row, col)
                if stone != Stone.EMPTY:
                    self._draw_stone(row, col, stone)

    def _draw_stone(self, row: int, col: int, stone: Stone, alpha: float = 1.0) -> None:
        """Draw a single stone.

        Args:
            row: Row index
            col: Column index
            stone: Stone color
            alpha: Opacity (0-1)
        """
        x = self.margin + col * self.cell_size
        y = self.margin + row * self.cell_size
        radius = self.cell_size // 2 - 2

        if stone == Stone.BLACK:
            color = 'black' if alpha == 1.0 else '#555555'
        else:
            color = 'white' if alpha == 1.0 else '#CCCCCC'

        self.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=color,
            outline='black',
            width=1,
            tags='stone'
        )

    def _draw_last_move_marker(self) -> None:
        """Draw a marker on the last move."""
        if self.last_move is not None:
            row, col = self.last_move
            x = self.margin + col * self.cell_size
            y = self.margin + row * self.cell_size
            radius = 5

            # Red circle marker
            self.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                outline='red',
                width=2,
                tags='marker'
            )

    def _draw_error_markers(self) -> None:
        """Draw markers for error moves."""
        for row, col in self.error_moves:
            x = self.margin + col * self.cell_size
            y = self.margin + row * self.cell_size
            size = 8

            # Red X marker
            self.create_line(
                x - size, y - size, x + size, y + size,
                fill='red', width=3, tags='error'
            )
            self.create_line(
                x - size, y + size, x + size, y - size,
                fill='red', width=3, tags='error'
            )

    def _draw_move_candidates(self) -> None:
        """Draw numbered markers for top move candidates."""
        for row, col, rank in self.top_move_candidates:
            x = self.margin + col * self.cell_size
            y = self.margin + row * self.cell_size
            radius = 12

            # Draw circle with rank number
            # Color: Green for #1, fading to yellow/orange for lower ranks
            if rank == 0:
                color = '#00CC00'  # Bright green for best move
            elif rank == 1:
                color = '#66CC00'  # Green-yellow
            elif rank == 2:
                color = '#CCCC00'  # Yellow
            elif rank == 3:
                color = '#CC9900'  # Orange
            else:
                color = '#CC6600'  # Dark orange

            # Draw circle
            self.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                outline=color,
                width=3,
                tags='candidate'
            )

            # Draw rank number
            self.create_text(
                x, y,
                text=str(rank + 1),  # Display as 1-5 instead of 0-4
                font=('Arial', 12, 'bold'),
                fill=color,
                tags='candidate'
            )

    def set_last_move(self, row: int, col: int) -> None:
        """Set the last move position.

        Args:
            row: Row index
            col: Column index
        """
        self.last_move = (row, col)
        self.redraw()

    def clear_last_move(self) -> None:
        """Clear the last move marker."""
        self.last_move = None
        self.redraw()

    def set_error_moves(self, errors: Set[Tuple[int, int]]) -> None:
        """Set the error move positions.

        Args:
            errors: Set of (row, col) positions
        """
        self.error_moves = errors
        self.redraw()

    def set_top_move_candidates(self, candidates: list) -> None:
        """Set the top move candidates to display on the board.

        Args:
            candidates: List of (row, col, rank) tuples where rank is 0-4 for top 5 moves
        """
        self.top_move_candidates = candidates
        self.redraw()

    def _coords_to_position(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """Convert canvas coordinates to board position.

        Args:
            x: Canvas x coordinate
            y: Canvas y coordinate

        Returns:
            (row, col) or None if outside board
        """
        col = round((x - self.margin) / self.cell_size)
        row = round((y - self.margin) / self.cell_size)

        if self.board.is_valid_position(row, col):
            return (row, col)
        return None

    def _on_click(self, event) -> None:
        """Handle click event.

        Args:
            event: Click event
        """
        pos = self._coords_to_position(event.x, event.y)
        if pos is not None and self.click_callback is not None:
            row, col = pos
            self.click_callback(row, col)

    def _on_motion(self, event) -> None:
        """Handle mouse motion event.

        Args:
            event: Motion event
        """
        pos = self._coords_to_position(event.x, event.y)
        if pos != self.hover_pos:
            self.hover_pos = pos
            # Could add hover preview here if desired
