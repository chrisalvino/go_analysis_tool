"""Explore mode popup window for displaying top move analysis."""

import tkinter as tk
from typing import List
from katago.analysis import MoveAnalysis


class ExploreWindow(tk.Toplevel):
    """Popup window for displaying explore mode analysis."""

    def __init__(self, parent, board_size: int = 19):
        """Initialize explore window.

        Args:
            parent: Parent window (main application)
            board_size: Size of the Go board
        """
        super().__init__(parent)

        self.title("Explore Mode - Top Moves")
        self.board_size = board_size

        # Window properties
        self.transient(parent)  # Stay on top of parent
        self.attributes('-topmost', True)  # Always on top

        # Position window to the right of main window
        self.geometry("300x400+1220+100")  # x, y offset from screen

        self._setup_ui()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

    def _setup_ui(self):
        """Set up the UI components."""
        # Header
        header = tk.Label(
            self,
            text="Top 5 Responses",
            font=("Arial", 14, "bold"),
            pady=10
        )
        header.pack()

        # Moves list
        self.moves_text = tk.Text(
            self,
            height=20,
            width=35,
            font=("Arial", 11),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.moves_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def update_moves(self, top_moves: List[MoveAnalysis], player: str):
        """Update the moves display.

        Args:
            top_moves: List of top move analyses
            player: 'B' or 'W' for whose moves these are
        """
        self.moves_text.config(state=tk.NORMAL)
        self.moves_text.delete(1.0, tk.END)

        player_name = "Black" if player == 'B' else "White"
        self.title(f"Explore Mode - {player_name}'s Top Responses")

        for i, move in enumerate(top_moves[:5]):
            rank = i + 1

            # Format move coordinate
            if move.is_pass:
                move_str = "Pass"
            elif move.move:
                row, col = move.move
                col_letter = chr(ord('A') + col if col < 8 else ord('A') + col + 1)
                row_num = self.board_size - row
                move_str = f"{col_letter}{row_num}"
            else:
                move_str = "?"

            # Format score
            score = move.score_lead
            score_str = f"{score:+.1f}"

            # Create line
            line = f"{rank}. {move_str:5s}  Score: {score_str:6s}\n"
            self.moves_text.insert(tk.END, line)

        self.moves_text.config(state=tk.DISABLED)

    def show(self):
        """Show the window."""
        self.deiconify()

    def hide(self):
        """Hide the window."""
        self.withdraw()
