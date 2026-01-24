"""Control panel for game navigation."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ControlPanel(tk.Frame):
    """Control panel for game navigation and actions."""

    def __init__(self, parent, **kwargs):
        """Initialize the control panel.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        # Callbacks
        self.on_previous: Optional[Callable[[], None]] = None
        self.on_next: Optional[Callable[[], None]] = None
        self.on_first: Optional[Callable[[], None]] = None
        self.on_last: Optional[Callable[[], None]] = None
        self.on_pass: Optional[Callable[[], None]] = None
        self.on_variation_change: Optional[Callable[[int], None]] = None

        # State
        self.current_move = 0
        self.total_moves = 0
        self.variations_count = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Navigation section
        nav_frame = tk.LabelFrame(self, text="Navigation", padx=10, pady=10)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)

        # First/Previous/Next/Last buttons
        button_frame = tk.Frame(nav_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.first_btn = tk.Button(button_frame, text="|<", width=5, command=self._handle_first)
        self.first_btn.pack(side=tk.LEFT, padx=2)

        self.prev_btn = tk.Button(button_frame, text="<", width=5, command=self._handle_previous)
        self.prev_btn.pack(side=tk.LEFT, padx=2)

        self.next_btn = tk.Button(button_frame, text=">", width=5, command=self._handle_next)
        self.next_btn.pack(side=tk.LEFT, padx=2)

        self.last_btn = tk.Button(button_frame, text=">|", width=5, command=self._handle_last)
        self.last_btn.pack(side=tk.LEFT, padx=2)

        # Move counter
        self.move_label = tk.Label(nav_frame, text="Move: 0 / 0")
        self.move_label.pack(pady=5)

        # Current player indicator
        self.player_label = tk.Label(nav_frame, text="Next: Black ●", font=("Arial", 10, "bold"))
        self.player_label.pack(pady=2)

        # Variation selector
        var_frame = tk.Frame(nav_frame)
        var_frame.pack(fill=tk.X, pady=5)

        tk.Label(var_frame, text="Variation:").pack(side=tk.LEFT, padx=5)

        self.variation_var = tk.IntVar(value=0)
        self.variation_spin = tk.Spinbox(
            var_frame,
            from_=0,
            to=0,
            textvariable=self.variation_var,
            width=5,
            command=self._handle_variation_change,
            state='readonly'
        )
        self.variation_spin.pack(side=tk.LEFT, padx=5)

        # Game actions section
        actions_frame = tk.LabelFrame(self, text="Game Actions", padx=10, pady=10)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        self.pass_btn = tk.Button(actions_frame, text="Pass", command=self._handle_pass)
        self.pass_btn.pack(fill=tk.X, pady=2)

        # Game info section
        info_frame = tk.LabelFrame(self, text="Game Info", padx=10, pady=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.info_text = tk.Text(info_frame, height=8, width=30, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        self.info_text.config(state=tk.DISABLED)

    def _handle_previous(self) -> None:
        """Handle previous button click."""
        if self.on_previous:
            self.on_previous()

    def _handle_next(self) -> None:
        """Handle next button click."""
        if self.on_next:
            self.on_next()

    def _handle_first(self) -> None:
        """Handle first button click."""
        if self.on_first:
            self.on_first()

    def _handle_last(self) -> None:
        """Handle last button click."""
        if self.on_last:
            self.on_last()

    def _handle_pass(self) -> None:
        """Handle pass button click."""
        if self.on_pass:
            self.on_pass()

    def _handle_variation_change(self) -> None:
        """Handle variation change."""
        if self.on_variation_change:
            self.on_variation_change(self.variation_var.get())

    def update_move_info(self, current: int, total: int) -> None:
        """Update move information display.

        Args:
            current: Current move number (1-based, 0 for root)
            total: Total actual moves (excluding root and metadata nodes)
        """
        self.current_move = current
        self.total_moves = total

        # Display move numbers (move 0 = root/no moves, move 1+ = actual moves)
        if current == 0:
            display_current = "-"
            display_total = "-" if total == 0 else total
        else:
            display_current = current
            display_total = total

        self.move_label.config(text=f"Move: {display_current} / {display_total}")

        # Update button states
        self.first_btn.config(state=tk.NORMAL if current > 0 else tk.DISABLED)
        self.prev_btn.config(state=tk.NORMAL if current > 0 else tk.DISABLED)
        # Note: We'll update next/last based on whether there are more moves

    def update_current_player(self, player: str) -> None:
        """Update the current player indicator.

        Args:
            player: 'B' for Black or 'W' for White
        """
        if player == 'B' or player == 'BLACK':
            self.player_label.config(text="Next: Black ●", fg="black")
        else:
            self.player_label.config(text="Next: White ○", fg="gray")

    def update_variations(self, count: int) -> None:
        """Update variation count.

        Args:
            count: Number of variations
        """
        self.variations_count = count
        self.variation_spin.config(to=max(0, count - 1))

        if count <= 1:
            self.variation_spin.config(state=tk.DISABLED)
        else:
            self.variation_spin.config(state='readonly')

    def set_navigation_enabled(self, previous: bool, next_move: bool) -> None:
        """Set which navigation buttons are enabled.

        Args:
            previous: Whether previous buttons are enabled
            next_move: Whether next buttons are enabled
        """
        prev_state = tk.NORMAL if previous else tk.DISABLED
        next_state = tk.NORMAL if next_move else tk.DISABLED

        self.first_btn.config(state=prev_state)
        self.prev_btn.config(state=prev_state)
        self.next_btn.config(state=next_state)
        self.last_btn.config(state=next_state)

    def set_game_info(self, info: str) -> None:
        """Set the game information text.

        Args:
            info: Information text to display
        """
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)
        self.info_text.config(state=tk.DISABLED)

    def set_play_mode(self, enabled: bool) -> None:
        """Set whether play mode controls are enabled.

        Args:
            enabled: Whether to enable play mode
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.pass_btn.config(state=state)
