"""Main application window."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
from typing import Optional, List

from game.board import Board, Stone
from game.rules import GoRules
from game.game_tree import GameTree
from sgf.parser import SGFParser
from sgf.writer import SGFWriter
from katago.engine import KataGoEngine
from katago.analysis import GameAnalyzer, PositionAnalysis
from ui.board_canvas import BoardCanvas
from ui.control_panel import ControlPanel
from ui.analysis_panel import AnalysisPanel
from utils.config import Config
from utils.katago_setup import run_setup


class GoAnalysisTool(tk.Tk):
    """Main application window."""

    def __init__(self):
        """Initialize the application."""
        super().__init__()

        self.title("Go Analysis Tool")
        self.geometry("1200x800")

        # Load configuration
        self.app_config = Config()

        # Game state
        self.board = Board(19)
        self.rules = GoRules(self.board)
        self.game_tree = GameTree(19)
        self.current_player = Stone.BLACK

        # Analysis state
        self.katago_engine: Optional[KataGoEngine] = None
        self.analyzer: Optional[GameAnalyzer] = None
        self.analysis_results: List[PositionAnalysis] = []
        self.is_analyzing = False

        # Mode
        self.play_mode = True  # True = play mode, False = analysis mode

        # Track current SGF file for screenshot output
        self.current_sgf_path: Optional[str] = None

        self._setup_ui()
        self._setup_menu()
        self._bind_callbacks()

        # Try to initialize KataGo
        self._init_katago()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        # Main container
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left side: Board
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.board_canvas = BoardCanvas(left_frame, self.board)
        self.board_canvas.pack()

        # Right side: Controls and Analysis
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Mode selector with radio buttons
        mode_frame = tk.LabelFrame(right_frame, text="Mode", padx=10, pady=5)
        mode_frame.pack(fill=tk.X, pady=5)

        self.mode_var = tk.StringVar(value="play")

        play_radio = tk.Radiobutton(
            mode_frame,
            text="Play Mode",
            variable=self.mode_var,
            value="play",
            command=self._set_play_mode,
            font=("Arial", 10)
        )
        play_radio.pack(anchor=tk.W, pady=2)

        analysis_radio = tk.Radiobutton(
            mode_frame,
            text="Analysis Mode",
            variable=self.mode_var,
            value="analysis",
            command=self._set_analysis_mode,
            font=("Arial", 10)
        )
        analysis_radio.pack(anchor=tk.W, pady=2)

        # Control panel
        self.control_panel = ControlPanel(right_frame)
        self.control_panel.pack(fill=tk.BOTH, expand=True)

        # Analysis panel
        self.analysis_panel = AnalysisPanel(right_frame)
        self.analysis_panel.pack(fill=tk.BOTH, expand=True)

    def _setup_menu(self) -> None:
        """Set up the menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(label="New Game", command=self._new_game)
        file_menu.add_command(label="Open SGF", command=self._open_sgf)
        file_menu.add_command(label="Save SGF", command=self._save_sgf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        settings_menu.add_command(label="Auto Setup KataGo", command=self._auto_setup_katago)
        settings_menu.add_command(label="Configure KataGo", command=self._configure_katago)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)

        help_menu.add_command(label="About", command=self._show_about)

    def _bind_callbacks(self) -> None:
        """Bind UI callbacks."""
        # Board canvas
        self.board_canvas.set_click_callback(self._on_board_click)

        # Control panel
        self.control_panel.on_previous = self._go_previous
        self.control_panel.on_next = self._go_next
        self.control_panel.on_first = self._go_first
        self.control_panel.on_last = self._go_last
        self.control_panel.on_pass = self._play_pass

        # Analysis panel
        self.analysis_panel.analyze_btn.config(command=self._analyze_game)
        self.analysis_panel.analyze_pos_btn.config(command=self._analyze_position)
        self.analysis_panel.on_error_click = self._jump_to_error

    def _init_katago(self) -> None:
        """Initialize KataGo if configured."""
        if self.app_config.is_katago_configured():
            try:
                self.katago_engine = KataGoEngine(
                    self.app_config.get_katago_executable(),
                    self.app_config.get_katago_config(),
                    self.app_config.get_katago_model(),
                    self.app_config.get_analysis_timeout()
                )

                if self.katago_engine.start():
                    num_threads = self.app_config.get_analysis_threads()
                    self.analyzer = GameAnalyzer(
                        self.katago_engine,
                        self.app_config.get_error_threshold(),
                        num_threads
                    )
                    print(f"KataGo initialized successfully (analysis threads: {num_threads})")
                else:
                    print("Failed to start KataGo")
                    self.katago_engine = None

            except Exception as e:
                print(f"Error initializing KataGo: {e}")
                self.katago_engine = None

    def _new_game(self) -> None:
        """Create a new game."""
        # Ask for board size
        size = simpledialog.askinteger("New Game", "Board size:", initialvalue=19, minvalue=9, maxvalue=19)

        if size and size in (9, 13, 19):
            self.board = Board(size)
            self.rules = GoRules(self.board)
            self.game_tree = GameTree(size)
            self.current_player = Stone.BLACK

            # Clear SGF path for new game
            self.current_sgf_path = None

            # Update UI
            self.board_canvas.set_board(self.board)
            self.analysis_panel.board_size = size
            self.analysis_panel.komi = self.game_tree.get_komi()
            self._update_display()

    def _open_sgf(self) -> None:
        """Open an SGF file."""
        filename = filedialog.askopenfilename(
            title="Open SGF",
            filetypes=[("SGF files", "*.sgf"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.game_tree = SGFParser.parse_file(filename)
                self.board = Board(self.game_tree.board_size)
                self.rules = GoRules(self.board)

                # Track the SGF path for screenshot output
                self.current_sgf_path = filename

                # Update canvas to use new board
                self.board_canvas.set_board(self.board)
                self.analysis_panel.board_size = self.game_tree.board_size
                self.analysis_panel.komi = self.game_tree.get_komi()

                # Replay to current position
                self.game_tree.go_to_root()
                # Skip to first actual move (skip root and any metadata nodes)
                while self.game_tree.current.children:
                    self.game_tree.go_to_next()
                    # Stop if we reach a node with an actual move
                    if self.game_tree.current.move is not None or self.game_tree.current.is_pass:
                        break
                self._replay_to_current()

                self._update_display()
                messagebox.showinfo("Success", "SGF file loaded successfully")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load SGF: {e}")

    def _save_sgf(self) -> None:
        """Save game to SGF file."""
        filename = filedialog.asksaveasfilename(
            title="Save SGF",
            defaultextension=".sgf",
            filetypes=[("SGF files", "*.sgf"), ("All files", "*.*")]
        )

        if filename:
            try:
                SGFWriter.write_file(self.game_tree, filename)
                messagebox.showinfo("Success", "Game saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save SGF: {e}")

    def _auto_setup_katago(self) -> None:
        """Automatically download and setup KataGo."""
        result = messagebox.askyesno(
            "Auto Setup KataGo",
            "This will automatically download KataGo, a neural network, and generate configuration.\n\n"
            "Download size: ~100-200 MB\n"
            "Install location: ./katago_data/\n\n"
            "Continue?"
        )

        if not result:
            return

        # Show progress window
        progress_window = tk.Toplevel(self)
        progress_window.title("Setting up KataGo")
        progress_window.geometry("500x200")
        progress_window.transient(self)

        tk.Label(
            progress_window,
            text="Please wait while KataGo is being downloaded and configured...",
            wraplength=450
        ).pack(pady=20)

        progress_text = tk.Text(progress_window, height=8, width=60)
        progress_text.pack(padx=10, pady=10)

        # Redirect stdout to the text widget
        import sys
        from io import StringIO

        def run_setup_thread():
            # Capture output
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                katago_path, config_path, model_path = run_setup()

                output = sys.stdout.getvalue()
                sys.stdout = old_stdout

                # Update UI
                self.after(0, lambda: progress_text.insert(tk.END, output))

                if katago_path and config_path and model_path:
                    # Save to config
                    self.app_config.set('katago', 'executable_path', katago_path)
                    self.app_config.set('katago', 'config_path', config_path)
                    self.app_config.set('katago', 'model_path', model_path)
                    self.app_config.save()

                    # Reinitialize KataGo
                    if self.katago_engine:
                        self.katago_engine.stop()

                    self.after(0, lambda: self._init_katago())
                    self.after(0, lambda: progress_window.destroy())
                    self.after(0, lambda: messagebox.showinfo(
                        "Success",
                        "KataGo has been set up successfully!\n\n"
                        "You can now use the analysis features."
                    ))
                else:
                    self.after(0, lambda: messagebox.showerror(
                        "Setup Failed",
                        "Failed to set up KataGo. Please check the output and try manual configuration."
                    ))

            except Exception as e:
                sys.stdout = old_stdout
                self.after(0, lambda: messagebox.showerror(
                    "Error",
                    f"Setup failed with error: {e}"
                ))
                self.after(0, lambda: progress_window.destroy())

        threading.Thread(target=run_setup_thread, daemon=True).start()

    def _configure_katago(self) -> None:
        """Configure KataGo paths."""
        dialog = tk.Toplevel(self)
        dialog.title("Configure KataGo")
        dialog.geometry("600x300")

        # Executable path
        tk.Label(dialog, text="KataGo Executable:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        exe_entry = tk.Entry(dialog, width=50)
        exe_entry.grid(row=0, column=1, padx=5, pady=5)
        exe_entry.insert(0, self.app_config.get_katago_executable())

        tk.Button(dialog, text="Browse", command=lambda: self._browse_file(exe_entry)).grid(row=0, column=2, padx=5)

        # Config path
        tk.Label(dialog, text="Config File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        config_entry = tk.Entry(dialog, width=50)
        config_entry.grid(row=1, column=1, padx=5, pady=5)
        config_entry.insert(0, self.app_config.get_katago_config())

        tk.Button(dialog, text="Browse", command=lambda: self._browse_file(config_entry)).grid(row=1, column=2, padx=5)

        # Model path
        tk.Label(dialog, text="Model File:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        model_entry = tk.Entry(dialog, width=50)
        model_entry.grid(row=2, column=1, padx=5, pady=5)
        model_entry.insert(0, self.app_config.get_katago_model())

        tk.Button(dialog, text="Browse", command=lambda: self._browse_file(model_entry)).grid(row=2, column=2, padx=5)

        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)

        def auto_setup():
            dialog.destroy()
            self._auto_setup_katago()

        def save_config():
            self.app_config.set('katago', 'executable_path', exe_entry.get())
            self.app_config.set('katago', 'config_path', config_entry.get())
            self.app_config.set('katago', 'model_path', model_entry.get())
            self.app_config.save()

            # Reinitialize KataGo
            if self.katago_engine:
                self.katago_engine.stop()

            self._init_katago()
            dialog.destroy()

        tk.Button(button_frame, text="Auto Setup", command=auto_setup, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save", command=save_config, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def _browse_file(self, entry: tk.Entry) -> None:
        """Browse for a file.

        Args:
            entry: Entry widget to update
        """
        filename = filedialog.askopenfilename()
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)

    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "Go Analysis Tool\\n\\nA tool for analyzing Go games using KataGo.\\n\\nSupports SGF files, gameplay, and AI analysis."
        )

    def _set_play_mode(self) -> None:
        """Switch to play mode."""
        self.play_mode = True
        self.mode_var.set("play")
        self.control_panel.set_play_mode(True)
        self.board_canvas.set_preview_stone(self.current_player)
        # Don't clear analysis overlays - let them show in both modes

    def _set_analysis_mode(self) -> None:
        """Switch to analysis mode."""
        self.play_mode = False
        self.mode_var.set("analysis")
        self.control_panel.set_play_mode(False)
        self.board_canvas.set_preview_stone(None)
        # Update display to show analysis if available
        if self.analysis_results:
            self._display_current_analysis()

    def _on_board_click(self, row: int, col: int) -> None:
        """Handle board click.

        Args:
            row: Row index
            col: Column index
        """
        if self.play_mode:
            self._play_move(row, col)

    def _play_move(self, row: int, col: int) -> None:
        """Play a move.

        Args:
            row: Row index
            col: Column index
        """
        result = self.rules.play_move(row, col, self.current_player)

        if result.valid:
            # Add to game tree
            self.game_tree.add_move(row, col, self.current_player)

            # Update display
            self.board_canvas.set_last_move(row, col)
            self.board_canvas.redraw()

            # Switch player
            self.current_player = Stone.WHITE if self.current_player == Stone.BLACK else Stone.BLACK

            self._update_display()
        else:
            messagebox.showwarning("Invalid Move", result.message)

    def _play_pass(self) -> None:
        """Play a pass move."""
        if self.play_mode:
            self.game_tree.add_pass(self.current_player)
            self.rules.pass_turn()

            # Switch player
            self.current_player = Stone.WHITE if self.current_player == Stone.BLACK else Stone.BLACK

            self._update_display()

    def _go_previous(self) -> None:
        """Go to previous move."""
        if self.game_tree.go_to_previous():
            # Check if we ended up at root (move 0)
            if self.game_tree.current.parent is None:
                # We're at root, don't allow this - go back to move 1
                self.game_tree.go_to_next()
                # CRITICAL: Must replay and update display after moving forward!
                self._replay_to_current()
                self._update_display()
            else:
                self._replay_to_current()
                self._update_display()

    def _go_next(self) -> None:
        """Go to next move."""
        if self.game_tree.go_to_next():
            self._replay_to_current()
            self._update_display()

    def _go_first(self) -> None:
        """Go to first move (skip root and metadata nodes)."""
        self.game_tree.go_to_root()
        # Skip to first actual move (skip root and any metadata nodes)
        while self.game_tree.current.children:
            self.game_tree.go_to_next()
            # Stop if we reach a node with an actual move
            if self.game_tree.current.move is not None or self.game_tree.current.is_pass:
                break
        self._replay_to_current()
        self._update_display()

    def _go_last(self) -> None:
        """Go to last move."""
        while self.game_tree.go_to_next():
            pass
        self._replay_to_current()
        self._update_display()

    def _replay_to_current(self) -> None:
        """Replay moves from root to current position."""
        # Clear board
        self.board.clear()
        self.rules = GoRules(self.board)

        # Get moves from root to current
        moves = self.game_tree.current.get_main_line()

        # Handle setup stones from first game node (which contains AB/AW properties)
        # The root is just a container, the first child has the actual game properties
        setup_node = None
        if moves and len(moves) > 0:
            # Check if root has children (SGF game data)
            if self.game_tree.root.children:
                setup_node = self.game_tree.root.children[0]
            elif moves[0].properties:
                setup_node = moves[0]

        if setup_node and setup_node.properties:
            root_props = setup_node.properties

            # Add Black stones (AB property)
            if 'AB' in root_props:
                ab_values = root_props['AB']
                if isinstance(ab_values, list):
                    for stone_pos in ab_values:
                        if stone_pos:
                            try:
                                from sgf.parser import SGFParser
                                row, col = SGFParser._sgf_to_coords(stone_pos)
                                self.board.set_stone(row, col, Stone.BLACK)
                            except Exception as e:
                                print(f"Error placing handicap stone at {stone_pos}: {e}")
                elif ab_values:
                    # Single value (old format)
                    try:
                        from sgf.parser import SGFParser
                        row, col = SGFParser._sgf_to_coords(ab_values)
                        self.board.set_stone(row, col, Stone.BLACK)
                    except Exception as e:
                        print(f"Error placing handicap stone at {ab_values}: {e}")

            # Add White stones (AW property)
            if 'AW' in root_props:
                aw_values = root_props['AW']
                if isinstance(aw_values, list):
                    for stone_pos in aw_values:
                        if stone_pos:
                            try:
                                from sgf.parser import SGFParser
                                row, col = SGFParser._sgf_to_coords(stone_pos)
                                self.board.set_stone(row, col, Stone.WHITE)
                            except Exception as e:
                                print(f"Error placing setup stone at {stone_pos}: {e}")
                elif aw_values:
                    # Single value (old format)
                    try:
                        from sgf.parser import SGFParser
                        row, col = SGFParser._sgf_to_coords(aw_values)
                        self.board.set_stone(row, col, Stone.WHITE)
                    except Exception as e:
                        print(f"Error placing setup stone at {aw_values}: {e}")

        # Replay each move
        for node in moves[1:]:  # Skip root
            if node.is_pass:
                self.rules.pass_turn()
            elif node.move:
                self.rules.play_move(node.move[0], node.move[1], node.color)

        # Update current player
        if moves:
            last_node = moves[-1]
            if last_node.color:
                self.current_player = Stone.WHITE if last_node.color == Stone.BLACK else Stone.BLACK
            else:
                self.current_player = Stone.BLACK

    def _update_display(self) -> None:
        """Update the display."""
        # Update board canvas
        self.board_canvas.redraw()

        # Update last move marker
        if self.game_tree.current.move:
            self.board_canvas.set_last_move(*self.game_tree.current.move)
        else:
            self.board_canvas.clear_last_move()

        # Update control panel
        current_move = self.game_tree.get_current_move_number()
        # Count total actual moves in the ENTIRE game (not just up to current position)
        total_moves = sum(1 for node in self.game_tree.get_main_line()
                          if node.move is not None or node.is_pass)

        self.control_panel.update_move_info(current_move, total_moves)

        # Update current player indicator
        # Determine next player based on move count (Black plays on odd moves, White on even)
        next_player = 'B' if current_move % 2 == 0 else 'W'
        self.control_panel.update_current_player(next_player)

        self.control_panel.set_navigation_enabled(
            self.game_tree.has_previous(),
            self.game_tree.has_next()
        )

        # Update variations
        variations = len(self.game_tree.get_variations())
        self.control_panel.update_variations(variations)

        # Show analysis overlays whenever analysis exists (regardless of mode)
        if self.analysis_results:
            self._display_current_analysis()

    def _display_current_analysis(self) -> None:
        """Display analysis for the current move (the move that was just played)."""
        current_move = self.game_tree.get_current_move_number()

        # Skip root (move 0) - no analysis to show
        if current_move == 0:
            self.board_canvas.set_top_move_candidates([])
            self.board_canvas.set_error_moves(set())
            return

        # Find the analysis for this move number
        current_analysis = None
        for analysis in self.analysis_results:
            if analysis.move_number == current_move:
                current_analysis = analysis
                break

        if current_analysis and current_analysis.top_moves:
            # Extract top 5 move candidates for board display
            candidates = []
            for i, move_analysis in enumerate(current_analysis.top_moves[:5]):
                if move_analysis.move and not move_analysis.is_pass:
                    row, col = move_analysis.move
                    candidates.append((row, col, i))  # (row, col, rank)

            # Update board canvas with candidates
            self.board_canvas.set_top_move_candidates(candidates)

            # Check if played move is in top 5
            played_in_top_5 = False
            if current_analysis.played_move_analysis:
                for move_analysis in current_analysis.top_moves[:5]:
                    # Compare moves - handle both regular moves and passes
                    if current_analysis.played_move_analysis.is_pass and move_analysis.is_pass:
                        played_in_top_5 = True
                        break
                    elif move_analysis.move == current_analysis.played_move_analysis.move:
                        played_in_top_5 = True
                        break

            # Show error marker only if this is an actual error (exceeds threshold)
            show_error_marker = False
            if current_analysis.played_move and current_analysis.is_error:
                if current_analysis.played_move_analysis and not current_analysis.played_move_analysis.is_pass:
                    show_error_marker = True

            if show_error_marker:
                self.board_canvas.set_error_moves({current_analysis.played_move})
            else:
                self.board_canvas.set_error_moves(set())

            # Determine whose turn it was when this move was played
            # The analysis before move N shows options for the player who played move N
            current_node = self.game_tree.current
            if current_node.color == Stone.BLACK:
                current_player_str = 'B'
            elif current_node.color == Stone.WHITE:
                current_player_str = 'W'
            else:
                # Root or unknown - default to Black
                current_player_str = 'B'

            # Update analysis panel with current position's analysis
            self.analysis_panel.display_position_analysis(current_analysis, current_player_str)
        else:
            # Clear candidates and errors if no analysis available
            self.board_canvas.set_top_move_candidates([])
            self.board_canvas.set_error_moves(set())
            self.analysis_panel.display_position_analysis(None)

    def _analyze_game(self) -> None:
        """Analyze the entire game."""
        if not self.analyzer:
            messagebox.showerror("Error", "KataGo is not configured. Please configure it in Settings.")
            return

        if self.is_analyzing:
            return

        # Run analysis in background thread
        def analyze_thread():
            self.is_analyzing = True
            self.analysis_panel.set_analyzing(True)

            def progress_callback(current, total):
                self.after(0, lambda: self.analysis_panel.set_progress(current, total))

            try:
                results = self.analyzer.analyze_game(
                    self.game_tree,
                    self.app_config.get_max_visits(),
                    progress_callback,
                    # Pass KataGo paths for parallel engine creation
                    self.app_config.get_katago_executable(),
                    self.app_config.get_katago_config(),
                    self.app_config.get_katago_model(),
                    self.app_config.get_analysis_timeout()
                )

                self.analysis_results = results

                # Extract errors - moves that exceed error threshold
                # Note: Moves that weren't in top 5 are now analyzed automatically
                errors = [(a.move_number, a.played_move, a.point_loss)
                         for a in results if a.is_error]

                # Extract tsumego positions (clear best move > 7 points better than 2nd best)
                tsumego_positions = []
                for a in results:
                    if len(a.top_moves) >= 2:
                        gap = abs(a.top_moves[0].score_lead - a.top_moves[1].score_lead)
                        if gap > 7.0:
                            tsumego_positions.append((a.move_number, gap))

                # Update UI
                self.after(0, lambda: self.analysis_panel.display_errors(errors))
                # Don't highlight all errors at once - only show error for current position

                self.after(0, lambda: messagebox.showinfo("Analysis Complete", f"Found {len(errors)} errors"))

                # Dump error screenshots
                self.after(0, lambda: self._dump_error_screenshots())

                # Dump tsumego screenshots
                if tsumego_positions:
                    self.after(0, lambda positions=tsumego_positions: self._dump_tsumego_screenshots(positions))

            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()  # Print full traceback to console
                self.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Analysis failed: {msg}"))

            finally:
                self.is_analyzing = False
                self.after(0, lambda: self.analysis_panel.set_analyzing(False))

        threading.Thread(target=analyze_thread, daemon=True).start()

    def _analyze_position(self) -> None:
        """Analyze current position."""
        if not self.analyzer:
            messagebox.showerror("Error", "KataGo is not configured.")
            return

        move_num = self.game_tree.get_current_move_number()

        # Run in background
        def analyze_thread():
            try:
                result = self.analyzer.analyze_position(
                    self.game_tree,
                    move_num,
                    self.app_config.get_max_visits()
                )

                if result:
                    self.after(0, lambda: self.analysis_panel.display_position_analysis(result))

            except Exception as e:
                messagebox.showerror("Error", f"Analysis failed: {e}")

        threading.Thread(target=analyze_thread, daemon=True).start()

    def _highlight_errors(self, errors: List[tuple]) -> None:
        """Highlight error moves on the board.

        Args:
            errors: List of error tuples
        """
        error_positions = set()

        for _, pos, _ in errors:
            if pos:
                error_positions.add(pos)

        self.board_canvas.set_error_moves(error_positions)

    def _jump_to_error(self, move_num: int) -> None:
        """Jump to an error move.

        Args:
            move_num: Move number to jump to
        """
        if self.game_tree.go_to_move_number(move_num):
            self._replay_to_current()
            self._update_display()
            # Analysis display is now handled automatically by _update_display()

    def _capture_screenshot(self, output_path: str) -> bool:
        """Capture a screenshot of the entire window.

        Args:
            output_path: Path to save the screenshot

        Returns:
            True if successful, False otherwise
        """
        try:
            from PIL import ImageGrab
            import os

            # Force update to ensure UI is fully rendered
            self.update_idletasks()
            self.update()

            # Get window position and size
            x = self.winfo_rootx()
            y = self.winfo_rooty()
            width = self.winfo_width()
            height = self.winfo_height()

            # Capture the window area
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save screenshot
            screenshot.save(output_path)
            print(f"Screenshot saved: {output_path}")
            return True

        except ImportError:
            print("ERROR: Pillow (PIL) is not installed. Please run: pip install Pillow")
            messagebox.showerror(
                "Screenshot Error",
                "Pillow library is not installed.\n\n"
                "To enable screenshots, run:\n"
                "pip install Pillow"
            )
            return False
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return False

    def _categorize_error(self, point_loss: float) -> str:
        """Categorize error by point loss.

        Args:
            point_loss: Point loss value

        Returns:
            Subfolder name for this error category
        """
        if point_loss >= 10.0:
            return "blunders"
        elif point_loss >= 7.0:
            return "errors"
        elif point_loss >= 5.0:
            return "mistakes"
        elif point_loss >= 2.0:
            return "inaccuracies"
        else:
            return "other"  # Fallback for errors below 2.0 points

    def _dump_error_screenshots(self) -> None:
        """Dump screenshots for all error positions after analysis."""
        if not self.analysis_results or not self.current_sgf_path:
            print("No analysis results or SGF path - skipping screenshot dump")
            return

        import os

        # Get SGF filename without extension
        sgf_basename = os.path.basename(self.current_sgf_path)
        sgf_name = os.path.splitext(sgf_basename)[0]

        # Create base output directory
        sgf_dir = os.path.dirname(self.current_sgf_path)
        base_output_dir = os.path.join(sgf_dir, sgf_name)

        # Extract errors
        errors = [(a.move_number, a.played_move, a.point_loss)
                  for a in self.analysis_results if a.is_error]

        if not errors:
            print("No errors to screenshot")
            messagebox.showinfo("Screenshots", "No errors found to screenshot.")
            return

        print(f"Dumping {len(errors)} error screenshots to {base_output_dir}/")

        # Switch to analysis mode for proper display
        original_mode = self.play_mode
        if self.play_mode:
            self._set_analysis_mode()

        # Categorize errors and create subfolders
        error_categories = {}
        for move_num, move_pos, point_loss in errors:
            category = self._categorize_error(point_loss)
            if category not in error_categories:
                error_categories[category] = []
            error_categories[category].append((move_num, move_pos, point_loss))

        # Create category subfolders
        for category in error_categories.keys():
            category_dir = os.path.join(base_output_dir, category)
            os.makedirs(category_dir, exist_ok=True)

        # Capture screenshot for each error
        success_count = 0
        for category, category_errors in error_categories.items():
            category_dir = os.path.join(base_output_dir, category)

            for move_num, move_pos, point_loss in category_errors:
                # Jump to error position
                if self.game_tree.go_to_move_number(move_num):
                    self._replay_to_current()
                    self._update_display()

                    # Give UI time to update
                    self.update_idletasks()
                    self.update()

                    # Generate filename
                    filename = f"move_{move_num:03d}_loss_{point_loss:.1f}pts.png"
                    output_path = os.path.join(category_dir, filename)

                    # Capture screenshot
                    if self._capture_screenshot(output_path):
                        success_count += 1

        # Restore original mode
        if original_mode:
            self._set_play_mode()

        print(f"Screenshot dump complete: {success_count}/{len(errors)} images saved")

        # Build summary message
        summary = f"Saved {success_count} error screenshots to:\n{base_output_dir}/\n\n"
        summary += "Categories:\n"
        for category in sorted(error_categories.keys()):
            count = len(error_categories[category])
            summary += f"  {category}: {count} error(s)\n"

        # Show completion message with path
        messagebox.showinfo(
            "Screenshots Complete",
            summary
        )

    def _capture_tsumego_screenshot(self, move_number: int, gap: float, output_dir: str) -> bool:
        """Capture a tsumego puzzle screenshot.

        Args:
            move_number: The move number of the tsumego (we'll screenshot move_number-1)
            gap: Score gap between top 2 moves
            output_dir: Directory to save screenshot

        Returns:
            True if successful
        """
        import os

        # Navigate to position before the tsumego move
        position_to_show = move_number - 1
        if not self.game_tree.go_to_move_number(position_to_show):
            return False

        self._replay_to_current()

        # CRITICAL: Update display to set last move marker and update navigation pane
        self._update_display()

        # Determine whose turn it is for the tsumego
        # (the player who will make move_number)
        player_to_move = 'black' if move_number % 2 == 1 else 'white'

        # Temporarily clear overlays (but keep last move marker)
        # Note: set_top_move_candidates() and set_error_moves() both call redraw()
        saved_candidates = self.board_canvas.top_move_candidates
        saved_errors = self.board_canvas.error_moves

        self.board_canvas.set_top_move_candidates([])  # Clears and redraws
        self.board_canvas.set_error_moves(set())        # Clears and redraws

        # Clear analysis panel text (Top 5 Moves pane)
        self.analysis_panel.display_position_analysis(None)

        # Update UI to render
        self.update_idletasks()
        self.update()

        # Capture screenshot
        filename = f"move_{position_to_show:03d}_{player_to_move}_to_move_gap_{gap:.1f}.png"
        output_path = os.path.join(output_dir, filename)
        success = self._capture_screenshot(output_path)

        # Restore overlays
        self.board_canvas.set_top_move_candidates(saved_candidates)
        self.board_canvas.set_error_moves(saved_errors)

        return success

    def _dump_tsumego_screenshots(self, tsumego_positions: list) -> None:
        """Dump screenshots for tsumego puzzle positions.

        Args:
            tsumego_positions: List of (move_number, gap) tuples
        """
        if not tsumego_positions or not self.current_sgf_path:
            print("No tsumego positions or SGF path - skipping tsumego screenshot dump")
            return

        import os

        # Get SGF filename without extension
        sgf_basename = os.path.basename(self.current_sgf_path)
        sgf_name = os.path.splitext(sgf_basename)[0]

        # Create tsumego directory
        sgf_dir = os.path.dirname(self.current_sgf_path)
        tsumego_dir = os.path.join(sgf_dir, sgf_name, "tsumego")
        os.makedirs(tsumego_dir, exist_ok=True)

        print(f"Dumping {len(tsumego_positions)} tsumego screenshots to {tsumego_dir}/")

        # Switch to analysis mode for proper display
        original_mode = self.play_mode
        if self.play_mode:
            self._set_analysis_mode()

        # Capture screenshot for each tsumego
        success_count = 0
        for move_num, gap in tsumego_positions:
            if self._capture_tsumego_screenshot(move_num, gap, tsumego_dir):
                success_count += 1

        # Restore original mode
        if original_mode:
            self._set_play_mode()

        print(f"Tsumego screenshot dump complete: {success_count}/{len(tsumego_positions)} images saved")

        # Show completion message
        messagebox.showinfo(
            "Tsumego Screenshots Complete",
            f"Saved {success_count} tsumego puzzle screenshots to:\n{tsumego_dir}/"
        )

    def destroy(self) -> None:
        """Clean up resources."""
        # Clean up analyzer engine pool
        if self.analyzer:
            self.analyzer._cleanup_engine_pool()

        # Stop primary engine
        if self.katago_engine:
            self.katago_engine.stop()

        super().destroy()
