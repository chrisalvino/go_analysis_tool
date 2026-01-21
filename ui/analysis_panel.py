"""Analysis panel for displaying KataGo analysis results."""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List
from katago.analysis import PositionAnalysis, MoveAnalysis


class AnalysisPanel(tk.Frame):
    """Panel for displaying analysis results."""

    def __init__(self, parent, **kwargs):
        """Initialize the analysis panel.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.on_error_click: Optional[Callable[[int], None]] = None
        self.board_size = 19  # Default, will be updated
        self.komi = 6.5  # Default komi, will be updated

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Analysis controls
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        self.analyze_btn = tk.Button(controls_frame, text="Analyze Game")
        self.analyze_btn.pack(fill=tk.X, pady=2)

        self.analyze_pos_btn = tk.Button(controls_frame, text="Analyze Position")
        self.analyze_pos_btn.pack(fill=tk.X, pady=2)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            controls_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status label
        self.status_label = tk.Label(controls_frame, text="Ready", fg="gray")
        self.status_label.pack(pady=2)

        # Top moves section
        top_moves_frame = tk.LabelFrame(self, text="Top 5 Moves", padx=5, pady=5)
        top_moves_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Top moves list
        self.top_moves_text = tk.Text(top_moves_frame, height=12, width=35, wrap=tk.WORD)
        top_moves_scroll = tk.Scrollbar(top_moves_frame, command=self.top_moves_text.yview)
        self.top_moves_text.config(yscrollcommand=top_moves_scroll.set)

        self.top_moves_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        top_moves_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.top_moves_text.config(state=tk.DISABLED)

        # Errors section
        errors_frame = tk.LabelFrame(self, text="Errors", padx=5, pady=5)
        errors_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Error list with scrollbar
        error_list_frame = tk.Frame(errors_frame)
        error_list_frame.pack(fill=tk.BOTH, expand=True)

        self.error_listbox = tk.Listbox(error_list_frame, height=10)
        error_scroll = tk.Scrollbar(error_list_frame, command=self.error_listbox.yview)
        self.error_listbox.config(yscrollcommand=error_scroll.set)

        self.error_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        error_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.error_listbox.bind('<<ListboxSelect>>', self._on_error_select)

    def set_analyzing(self, is_analyzing: bool) -> None:
        """Set the analyzing state.

        Args:
            is_analyzing: Whether analysis is in progress
        """
        if is_analyzing:
            self.analyze_btn.config(state=tk.DISABLED)
            self.analyze_pos_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Starting analysis...", fg="black")
            self.progress_var.set(0)
        else:
            self.analyze_btn.config(state=tk.NORMAL)
            self.analyze_pos_btn.config(state=tk.NORMAL)
            self.status_label.config(text="", fg="black")
            self.progress_var.set(0)

    def set_progress(self, current: int, total: int) -> None:
        """Set the progress bar.

        Args:
            current: Current move number
            total: Total moves
        """
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.status_label.config(text=f"Move {current} of {total} ({progress:.0f}%)", fg="black")

    def display_position_analysis(self, analysis: Optional[PositionAnalysis], current_player: str = 'B') -> None:
        """Display analysis for a position.

        Args:
            analysis: Position analysis data
            current_player: 'B' or 'W' for current player to move
        """
        self.top_moves_text.config(state=tk.NORMAL)
        self.top_moves_text.delete(1.0, tk.END)

        if analysis is None or not analysis.top_moves:
            self.top_moves_text.insert(tk.END, "No analysis available")
            self.top_moves_text.config(state=tk.DISABLED)
            return

        # Display top moves
        played_in_top_5 = False
        for i, move in enumerate(analysis.top_moves):
            rank = i + 1

            # Format move
            if move.is_pass:
                move_str = "Pass"
            elif move.move:
                row, col = move.move
                col_letter = chr(ord('A') + col if col < 8 else ord('A') + col + 1)
                row_num = self.board_size - row  # Use dynamic board size
                move_str = f"{col_letter}{row_num}"
            else:
                move_str = "?"

            # Format score - KataGo's score_lead already accounts for komi
            # Positive means current player is ahead
            score = move.score_lead
            score_str = f"{score:+.1f}"

            # Create line showing move and score
            line = f"{rank}. {move_str:5s} | Score: {score_str:6s}\n"

            # Highlight if this is the played move - handle both regular moves and passes
            if analysis.played_move_analysis:
                if analysis.played_move_analysis.is_pass and move.is_pass:
                    line = f">>> {line}"
                    played_in_top_5 = True
                elif move.move == analysis.played_move_analysis.move:
                    line = f">>> {line}"
                    played_in_top_5 = True

            self.top_moves_text.insert(tk.END, line)

        # Check if we have a played move to display
        if analysis.played_move_analysis and not played_in_top_5:
            # Played move was analyzed but not in top 5
            self.top_moves_text.insert(tk.END, "\n")

            # Format the played move
            if analysis.played_move_analysis.is_pass:
                move_str = "Pass"
            elif analysis.played_move_analysis.move:
                row, col = analysis.played_move_analysis.move
                col_letter = chr(ord('A') + col if col < 8 else ord('A') + col + 1)
                row_num = self.board_size - row
                move_str = f"{col_letter}{row_num}"
            else:
                move_str = "?"

            score = analysis.played_move_analysis.score_lead
            score_str = f"{score:+.1f}"

            line = f">>> Played: {move_str:5s} | Score: {score_str:6s}"

            # Color: red if error, green if just not in top 5 but not an error
            tag_name = "played_move_error" if analysis.is_error else "played_move_ok"
            self.top_moves_text.insert(tk.END, line, tag_name)

            if analysis.point_loss > 0:
                self.top_moves_text.insert(tk.END, f" (-{analysis.point_loss:.1f})", tag_name)

        # Show point loss if in top 5
        elif analysis.point_loss > 0 and played_in_top_5:
            self.top_moves_text.insert(tk.END, f"\nPoint loss: {analysis.point_loss:.1f}")

            if analysis.is_error:
                self.top_moves_text.insert(tk.END, " [ERROR]", "error")

        self.top_moves_text.tag_config("error", foreground="red", font=("Arial", 10, "bold"))
        self.top_moves_text.tag_config("played_move_error", foreground="red")
        self.top_moves_text.tag_config("played_move_ok", foreground="green")
        self.top_moves_text.config(state=tk.DISABLED)

    def display_errors(self, errors: List[tuple]) -> None:
        """Display error list.

        Args:
            errors: List of (move_number, position, point_loss) tuples
        """
        self.error_listbox.delete(0, tk.END)

        if not errors:
            self.error_listbox.insert(tk.END, "No errors found")
            return

        for move_num, pos, point_loss in errors:
            if pos:
                row, col = pos
                col_letter = chr(ord('A') + col if col < 8 else ord('A') + col + 1)
                row_num = self.board_size - row  # Use dynamic board size
                move_str = f"{col_letter}{row_num}"
            else:
                move_str = "Pass"

            error_text = f"Move {move_num}: {move_str} (-{point_loss:.1f})"
            self.error_listbox.insert(tk.END, error_text)

    def _on_error_select(self, event) -> None:
        """Handle error selection.

        Args:
            event: Selection event
        """
        selection = self.error_listbox.curselection()
        if selection and self.on_error_click:
            index = selection[0]
            # Extract move number from the error text
            error_text = self.error_listbox.get(index)
            if error_text.startswith("Move "):
                try:
                    move_num = int(error_text.split(":")[0].replace("Move ", ""))
                    self.on_error_click(move_num)
                except ValueError:
                    pass

    def clear_analysis(self) -> None:
        """Clear all analysis displays."""
        self.top_moves_text.config(state=tk.NORMAL)
        self.top_moves_text.delete(1.0, tk.END)
        self.top_moves_text.config(state=tk.DISABLED)

        self.error_listbox.delete(0, tk.END)

        self.status_label.config(text="", fg="black")
        self.progress_var.set(0)
