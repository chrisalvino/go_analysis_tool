"""New Game dialog with board size, handicap, and komi settings."""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any


class NewGameDialog(tk.Toplevel):
    """Modal dialog for creating a new game with size, handicap, and komi."""

    def __init__(self, parent):
        """Initialize the dialog.

        Args:
            parent: Parent window
        """
        super().__init__(parent)
        self.title("New Game")
        self.transient(parent)
        self.grab_set()

        self.result: Optional[Dict[str, Any]] = None
        self._komi_manually_edited = False

        self._setup_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # Wait for the dialog to close
        self.wait_window()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        main_frame = tk.Frame(self, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Board Size
        size_frame = tk.LabelFrame(main_frame, text="Board Size", padx=10, pady=5)
        size_frame.pack(fill=tk.X, pady=(0, 10))

        self.size_var = tk.IntVar(value=19)
        for size in (9, 13, 19):
            tk.Radiobutton(
                size_frame,
                text=f"{size}x{size}",
                variable=self.size_var,
                value=size,
                font=("Arial", 10)
            ).pack(side=tk.LEFT, padx=10)

        # Handicap
        handicap_frame = tk.LabelFrame(main_frame, text="Handicap", padx=10, pady=5)
        handicap_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(handicap_frame, text="Stones:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.handicap_var = tk.IntVar(value=0)
        self.handicap_spin = tk.Spinbox(
            handicap_frame,
            from_=0, to=9,
            textvariable=self.handicap_var,
            width=5,
            font=("Arial", 10),
            command=self._on_handicap_changed
        )
        self.handicap_spin.pack(side=tk.LEFT)
        # Also bind key release for manual typing in spinbox
        self.handicap_spin.bind('<KeyRelease>', lambda e: self._on_handicap_changed())

        # Komi
        komi_frame = tk.LabelFrame(main_frame, text="Komi", padx=10, pady=5)
        komi_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(komi_frame, text="Value:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.komi_var = tk.StringVar(value="6.5")
        self.komi_entry = tk.Entry(
            komi_frame,
            textvariable=self.komi_var,
            width=8,
            font=("Arial", 10)
        )
        self.komi_entry.pack(side=tk.LEFT)
        # Track manual edits to komi
        self.komi_entry.bind('<Key>', self._on_komi_key)

        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame, text="OK", command=self._ok,
            width=10, font=("Arial", 10)
        ).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(
            btn_frame, text="Cancel", command=self._cancel,
            width=10, font=("Arial", 10)
        ).pack(side=tk.RIGHT)

    def _on_handicap_changed(self) -> None:
        """Update komi when handicap changes (unless user manually edited komi)."""
        if self._komi_manually_edited:
            return

        try:
            handicap = self.handicap_var.get()
        except tk.TclError:
            return

        if handicap >= 2:
            self.komi_var.set("0.5")
        else:
            self.komi_var.set("6.5")

    def _on_komi_key(self, event) -> None:
        """Mark komi as manually edited when user types in the field."""
        # Ignore modifier keys, tab, etc.
        if event.keysym in ('Tab', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                            'Alt_L', 'Alt_R', 'Meta_L', 'Meta_R', 'Caps_Lock'):
            return
        self._komi_manually_edited = True

    def _ok(self) -> None:
        """Accept the dialog."""
        try:
            size = self.size_var.get()
            handicap = self.handicap_var.get()
            komi = float(self.komi_var.get())
        except (tk.TclError, ValueError):
            tk.messagebox.showerror("Invalid Input", "Please enter valid values.", parent=self)
            return

        if size not in (9, 13, 19):
            tk.messagebox.showerror("Invalid Size", "Board size must be 9, 13, or 19.", parent=self)
            return

        if not (0 <= handicap <= 9):
            tk.messagebox.showerror("Invalid Handicap", "Handicap must be between 0 and 9.", parent=self)
            return

        self.result = {
            'size': size,
            'handicap': handicap,
            'komi': komi
        }
        self.destroy()

    def _cancel(self) -> None:
        """Cancel the dialog."""
        self.result = None
        self.destroy()
