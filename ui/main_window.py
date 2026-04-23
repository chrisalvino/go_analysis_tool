"""Main application window."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
from typing import Optional, List

from game.board import Board, Stone
from game.rules import GoRules
from game.game_tree import GameTree, GameNode
from sgf.parser import SGFParser
from sgf.writer import SGFWriter
from katago.engine import KataGoEngine
from katago.analysis import GameAnalyzer, PositionAnalysis
from ui.board_canvas import BoardCanvas
from ui.control_panel import ControlPanel
from ui.analysis_panel import AnalysisPanel
from ui.explore_window import ExploreWindow
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

        # Play AI mode settings
        self.ai_player_color = Stone.WHITE  # AI plays White by default
        self.is_ai_thinking = False  # Track if AI is currently analyzing/playing

        # Track current SGF file for screenshot output
        self.current_sgf_path: Optional[str] = None

        # Explore mode window
        self.explore_window: Optional[ExploreWindow] = None

        # Manual handicap setup mode
        self._setup_mode = False
        self._setup_stones_needed = 0
        self._setup_stones_placed = []

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

        self.play_radio = tk.Radiobutton(
            mode_frame,
            text="Play Mode",
            variable=self.mode_var,
            value="play",
            command=self._set_play_mode,
            font=("Arial", 10)
        )
        self.play_radio.pack(anchor=tk.W, pady=2)

        self.analysis_radio = tk.Radiobutton(
            mode_frame,
            text="Analysis Mode",
            variable=self.mode_var,
            value="analysis",
            command=self._set_analysis_mode,
            font=("Arial", 10)
        )
        self.analysis_radio.pack(anchor=tk.W, pady=2)

        play_ai_radio = tk.Radiobutton(
            mode_frame,
            text="Play AI Mode",
            variable=self.mode_var,
            value="play_ai",
            command=self._set_play_ai_mode,
            font=("Arial", 10)
        )
        play_ai_radio.pack(anchor=tk.W, pady=2)

        # Store reference for enable/disable based on KataGo availability
        self.play_ai_radio = play_ai_radio

        # Subframe for AI color choice (indented under Play AI radio)
        ai_color_frame = tk.Frame(mode_frame)
        ai_color_frame.pack(anchor=tk.W, padx=25)  # Indent to show it's part of Play AI

        self.ai_color_var = tk.StringVar(value="white")

        ai_white_radio = tk.Radiobutton(
            ai_color_frame,
            text="AI plays White",
            variable=self.ai_color_var,
            value="white",
            command=lambda: self._set_ai_color(Stone.WHITE),
            font=("Arial", 9)
        )
        ai_white_radio.pack(side=tk.LEFT, padx=5)

        ai_black_radio = tk.Radiobutton(
            ai_color_frame,
            text="AI plays Black",
            variable=self.ai_color_var,
            value="black",
            command=lambda: self._set_ai_color(Stone.BLACK),
            font=("Arial", 9)
        )
        ai_black_radio.pack(side=tk.LEFT, padx=5)

        # Store reference for enable/disable
        self.ai_color_frame = ai_color_frame

        explore_radio = tk.Radiobutton(
            mode_frame,
            text="Explore Mode",
            variable=self.mode_var,
            value="explore",
            command=self._set_explore_mode,
            font=("Arial", 10)
        )
        explore_radio.pack(anchor=tk.W, pady=2)

        # Store reference for enable/disable based on KataGo availability
        self.explore_radio = explore_radio

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
        file_menu.add_command(label="Save Analysis (JSON)", command=self._save_analysis_json)
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

    def _update_mode_availability(self) -> None:
        """Update which modes are available based on KataGo configuration."""
        if not hasattr(self, 'explore_radio'):
            return  # Not initialized yet

        # Explore mode and Play AI mode require KataGo to be configured
        mode_state = tk.NORMAL if self.analyzer else tk.DISABLED
        self.explore_radio.config(state=mode_state)

        # Also disable Play AI mode if KataGo not available
        if hasattr(self, 'play_ai_radio'):
            self.play_ai_radio.config(state=mode_state)

        # If explore/play_ai mode was selected but KataGo became unavailable, switch to play mode
        if self.mode_var.get() in ["explore", "play_ai"] and not self.analyzer:
            self._set_play_mode()

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

        # Update mode availability after initialization
        self._update_mode_availability()

    def _new_game(self) -> None:
        """Create a new game."""
        if self._setup_mode:
            self._cancel_setup_mode()

        from ui.new_game_dialog import NewGameDialog

        dialog = NewGameDialog(self)
        if dialog.result is None:
            return

        size = dialog.result['size']
        handicap = dialog.result['handicap']
        komi = dialog.result['komi']

        self.board = Board(size)
        self.rules = GoRules(self.board)
        self.game_tree = GameTree(size)

        # Set komi on root node
        self.game_tree.root.properties['KM'] = komi

        if handicap >= 2:
            # Set HA property on root
            self.game_tree.root.properties['HA'] = handicap

            # Enter setup mode for manual handicap stone placement
            self._setup_mode = True
            self._setup_stones_needed = handicap
            self._setup_stones_placed = []
            self.current_player = Stone.BLACK  # Preview stone is black during setup
        else:
            self.current_player = Stone.BLACK

        # Clear SGF path for new game
        self.current_sgf_path = None

        # Clear any existing analysis
        self.analysis_results = []
        self.analysis_panel.display_errors([])
        self.analysis_panel.display_position_analysis(None)  # Clear top 5 moves pane
        self.board_canvas.set_top_move_candidates([])
        self.board_canvas.set_error_moves(set())

        # Update UI
        self.board_canvas.set_board(self.board)
        self.analysis_panel.board_size = size
        self.analysis_panel.komi = komi
        self._update_display()

        # Activate setup mode UI after display update
        if self._setup_mode:
            self._set_setup_mode_ui(True)
            self.board_canvas.set_preview_stone(Stone.BLACK)
            self._update_setup_status()

    def _open_sgf(self) -> None:
        """Open an SGF file."""
        if self._setup_mode:
            self._cancel_setup_mode()

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

                # Clear any existing analysis before loading new game
                self.analysis_results = []
                self.analysis_panel.display_errors([])
                self.analysis_panel.display_position_analysis(None)  # Clear top 5 moves pane
                self.board_canvas.set_top_move_candidates([])
                self.board_canvas.set_error_moves(set())

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

                # Auto-load analysis if JSON file exists (after clearing old analysis)
                self._try_load_analysis_json(filename)

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
                    self.after(0, lambda: self._update_mode_availability())
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
            self._update_mode_availability()
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

        # Hide explore window if it exists
        if self.explore_window:
            self.explore_window.hide()
        # Don't clear analysis overlays - let them show in both modes

    def _set_analysis_mode(self) -> None:
        """Switch to analysis mode."""
        self.play_mode = False
        self.mode_var.set("analysis")
        self.control_panel.set_play_mode(False)
        self.board_canvas.set_preview_stone(None)

        # Hide explore window if it exists
        if self.explore_window:
            self.explore_window.hide()

        # Update display to show analysis if available
        if self.analysis_results:
            self._display_current_analysis()

    def _set_explore_mode(self) -> None:
        """Switch to explore mode."""
        self.mode_var.set("explore")
        self.control_panel.set_play_mode(True)  # Enable Pass button
        self.board_canvas.set_preview_stone(self.current_player)  # Show preview

        # Create and show explore window
        if not self.explore_window:
            self.explore_window = ExploreWindow(self, self.board.size)
        self.explore_window.show()

        # Show analysis overlays if available
        if self.analysis_results:
            self._display_current_analysis()

    def _set_ai_color(self, color: Stone) -> None:
        """Set which color the AI plays.

        Args:
            color: Stone.BLACK or Stone.WHITE
        """
        self.ai_player_color = color

    def _set_play_ai_mode(self) -> None:
        """Switch to Play AI mode."""
        if not self.analyzer:
            messagebox.showerror(
                "KataGo Required",
                "Play AI mode requires KataGo to be configured.\n"
                "Please configure it in Settings > Configure KataGo."
            )
            # Revert to play mode
            self.mode_var.set("play")
            return

        self.mode_var.set("play_ai")
        self.control_panel.set_play_mode(False)  # Disable Pass button

        # Set preview stone based on who goes first
        # If AI plays Black, user plays White and sees white preview
        # If AI plays White, user plays Black and sees black preview
        user_color = Stone.WHITE if self.ai_player_color == Stone.BLACK else Stone.BLACK
        self.board_canvas.set_preview_stone(user_color)

        # Clear any analysis overlays
        self.board_canvas.set_top_move_candidates([])
        self.board_canvas.set_error_moves(set())

        # Hide explore window if it exists
        if self.explore_window:
            self.explore_window.hide()

        # Reset AI thinking state
        self.is_ai_thinking = False

        # If AI plays Black (goes first), trigger AI move immediately
        if self.ai_player_color == Stone.BLACK and self.current_player == Stone.BLACK:
            self.after(500, self._play_ai_move)  # Small delay for UI to settle

    def _on_board_click(self, row: int, col: int) -> None:
        """Handle board click.

        Args:
            row: Row index
            col: Column index
        """
        if self._setup_mode:
            self._handle_setup_click(row, col)
            return

        mode = self.mode_var.get()

        # Block clicks in Play AI mode if it's AI's turn or AI is thinking
        if mode == "play_ai":
            if self.is_ai_thinking:
                return  # Silently ignore clicks while AI is thinking

            # Check if it's user's turn
            user_color = Stone.WHITE if self.ai_player_color == Stone.BLACK else Stone.BLACK
            if self.current_player != user_color:
                return  # Silently ignore - not user's turn

        if mode in ["play", "explore", "play_ai"]:
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

            # AUTO-ANALYZE in explore mode
            mode = self.mode_var.get()
            if mode == "explore" and self.analyzer:
                # Small delay to ensure UI updates first
                self.after(100, self._trigger_explore_analysis)

            # AUTO-PLAY AI MOVE in play_ai mode
            if mode == "play_ai" and self.analyzer:
                # Check if it's AI's turn
                if self.current_player == self.ai_player_color:
                    # Small delay to ensure UI updates first
                    self.after(100, self._play_ai_move)
        else:
            messagebox.showwarning("Invalid Move", result.message)

    def _play_pass(self) -> None:
        """Play a pass move."""
        if self._setup_mode:
            return
        mode = self.mode_var.get()
        if mode in ["play", "explore", "play_ai"]:
            self.game_tree.add_pass(self.current_player)
            self.rules.pass_turn()

            # Switch player
            self.current_player = Stone.WHITE if self.current_player == Stone.BLACK else Stone.BLACK

            self._update_display()

            # Auto-analyze in explore mode
            if mode == "explore" and self.analyzer:
                self.after(100, self._trigger_explore_analysis)

            # Auto-play AI move in play_ai mode
            if mode == "play_ai" and self.analyzer:
                if self.current_player == self.ai_player_color:
                    self.after(100, self._play_ai_move)

    def _go_previous(self) -> None:
        """Go to previous move."""
        if self._setup_mode:
            return
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
        if self._setup_mode:
            return
        if self.game_tree.go_to_next():
            self._replay_to_current()
            self._update_display()

    def _go_first(self) -> None:
        """Go to first move (skip root and metadata nodes)."""
        if self._setup_mode:
            return
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
        if self._setup_mode:
            return
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

    def _has_black_handicap(self) -> bool:
        """Check if the game has Black handicap stones.

        Returns:
            True if the game has Black handicap stones (AB property)
        """
        main_line = self.game_tree.get_main_line()
        if not main_line or len(main_line) < 2:
            return False

        # Check root node (main_line[0])
        root_props = main_line[0].properties if main_line[0].properties else None

        # If root has no AB, check first child (main_line[1])
        if not root_props or 'AB' not in root_props:
            if len(main_line) > 1 and main_line[1].properties:
                root_props = main_line[1].properties

        # Check if AB property exists and has Black handicap stones
        if root_props and 'AB' in root_props:
            ab_values = root_props['AB']
            # AB can be a list or a single value
            if isinstance(ab_values, list) and len(ab_values) > 0:
                return True
            elif ab_values:  # Single value
                return True

        return False

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
        # Check if this is a handicap game (Black handicap stones)
        has_black_handicap = self._has_black_handicap()

        if has_black_handicap:
            # In handicap games, White plays first (move 1), then alternates
            # Move 0 -> White, Move 1 -> Black, Move 2 -> White
            next_player = 'W' if current_move % 2 == 0 else 'B'
        else:
            # Normal game: Black plays first
            # Move 0 -> Black, Move 1 -> White, Move 2 -> Black
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

                # Extract tsumego positions (clear best move > threshold points better than 2nd best)
                tsumego_threshold = self.app_config.get_tsumego_threshold()
                tsumego_positions = []
                for a in results:
                    if len(a.top_moves) >= 2:
                        gap = abs(a.top_moves[0].score_lead - a.top_moves[1].score_lead)
                        if gap > tsumego_threshold:
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

                # Auto-save analysis to JSON
                if self.current_sgf_path:
                    import os
                    sgf_basename = os.path.splitext(self.current_sgf_path)[0]
                    analysis_path = f"{sgf_basename}_analysis.json"

                    from utils.analysis_export import export_analysis_to_json
                    success = export_analysis_to_json(
                        results,
                        self.current_sgf_path,
                        self.game_tree.board_size,
                        self.game_tree.get_komi(),
                        self.app_config.get_max_visits(),
                        analysis_path
                    )

                    if success:
                        print(f"Analysis auto-saved to: {analysis_path}")

                        # Generate PDF error report
                        pdf_path = f"{sgf_basename}_error_report.pdf"
                        self.after(0, lambda path=pdf_path: self._generate_pdf_report(path))

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

    def _trigger_explore_analysis(self) -> None:
        """Trigger automatic analysis in explore mode."""
        if not self.analyzer:
            return

        # Get current position and board info
        board_size = self.game_tree.board_size
        komi = self.game_tree.get_komi()
        rules = self.game_tree.get_rules()

        # Build complete move list including the move just played
        main_line = self.game_tree.current.get_main_line()
        moves_gtp = []

        # Skip root (index 0), iterate through all moves including current
        for node in main_line[1:]:
            if node.is_pass:
                moves_gtp.append('pass')
            elif node.move:
                gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1], board_size)
                moves_gtp.append(gtp_move)

        # Determine initial player (for handicap games)
        initial_stones = []
        # Extract handicap stones from root or first child
        root_props = None
        if main_line and len(main_line) > 0 and main_line[0].properties:
            root_props = main_line[0].properties

        if not root_props or ('AB' not in root_props and 'AW' not in root_props):
            if len(main_line) > 1 and main_line[1].properties:
                root_props = main_line[1].properties

        if root_props:
            # Add Black handicap stones (AB property)
            if 'AB' in root_props:
                ab_values = root_props['AB']
                if isinstance(ab_values, list):
                    for stone_pos in ab_values:
                        if stone_pos and len(stone_pos) == 2:
                            try:
                                row = ord(stone_pos[1]) - ord('a')
                                col = ord(stone_pos[0]) - ord('a')
                                gtp_move = KataGoEngine.coords_to_gtp(row, col, board_size)
                                initial_stones.append(["B", gtp_move])
                            except Exception as e:
                                print(f"Error converting handicap stone {stone_pos}: {e}")

        # Determine initial player
        if initial_stones and all(stone[0] == 'B' for stone in initial_stones):
            initial_player = 'W'  # White plays first in Black handicap games
        else:
            initial_player = 'B'  # Normal game

        # Run in background thread
        def analyze_thread():
            try:
                # Call KataGo engine directly with complete move list
                analysis_data = self.katago_engine.analyze_position(
                    moves=moves_gtp,
                    board_size=board_size,
                    komi=komi,
                    initial_player=initial_player,
                    max_visits=self.app_config.get_max_visits(),
                    initial_stones=initial_stones if initial_stones else None,
                    rules=rules
                )

                if analysis_data and 'moveInfos' in analysis_data:
                    # Parse move candidates
                    move_analyses = []
                    for move_info in analysis_data['moveInfos']:
                        move_str = move_info.get('move', '')
                        is_pass = move_str.lower() == 'pass'
                        move = None

                        if not is_pass:
                            try:
                                move = KataGoEngine.gtp_to_coords(move_str, board_size)
                            except:
                                continue

                        win_rate = move_info.get('winrate', 0.0)
                        score_lead = move_info.get('scoreLead', 0.0)
                        visits = move_info.get('visits', 0)
                        order = move_info.get('order', len(move_analyses))
                        pv = move_info.get('pv', [])

                        from katago.analysis import MoveAnalysis
                        move_analysis = MoveAnalysis(
                            move=move,
                            is_pass=is_pass,
                            win_rate=win_rate,
                            score_lead=score_lead,
                            visits=visits,
                            order=order,
                            pv=pv
                        )
                        move_analyses.append(move_analysis)

                    # CRITICAL: Deduplicate moves - keep the one with most visits
                    seen_moves = {}
                    for move_analysis in move_analyses:
                        # Create a key for this move (position or 'pass')
                        if move_analysis.is_pass:
                            key = 'pass'
                        else:
                            key = move_analysis.move  # (row, col) tuple

                        # Keep the one with more visits (more accurate analysis)
                        if key not in seen_moves or move_analysis.visits > seen_moves[key].visits:
                            seen_moves[key] = move_analysis

                    # Get deduplicated list
                    top_moves = list(seen_moves.values())

                    # Sort by score lead (descending)
                    top_moves.sort(key=lambda x: x.score_lead, reverse=True)

                    # Create a minimal PositionAnalysis object for display
                    from katago.analysis import PositionAnalysis
                    position_analysis = PositionAnalysis(
                        move_number=self.game_tree.get_current_move_number(),
                        played_move=None,  # No move played yet (we're showing what SHOULD be played)
                        played_move_analysis=None,
                        top_moves=top_moves[:5],  # Top 5
                        is_error=False,
                        point_loss=0.0
                    )

                    # Determine whose turn it is NEXT (after the move just played)
                    current_node = self.game_tree.current
                    if current_node.color == Stone.BLACK:
                        # Black just played, so White plays next
                        next_player_str = 'W'
                    elif current_node.color == Stone.WHITE:
                        # White just played, so Black plays next
                        next_player_str = 'B'
                    else:
                        # Default to Black
                        next_player_str = 'B'

                    # Update explore window instead of analysis panel
                    if self.explore_window:
                        self.after(0, lambda: self.explore_window.update_moves(
                            top_moves[:5], next_player_str
                        ))

                    # Also update board overlays
                    self.after(0, lambda: self._display_analysis_result(position_analysis))

            except Exception as e:
                print(f"Explore mode analysis error: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=analyze_thread, daemon=True).start()

    def _play_ai_move(self) -> None:
        """Play the best move according to AI analysis (for Play AI mode)."""
        if not self.analyzer:
            return

        # Set flag to block user clicks
        self.is_ai_thinking = True

        # Get current position and board info
        board_size = self.game_tree.board_size
        komi = self.game_tree.get_komi()
        rules = self.game_tree.get_rules()

        # Build complete move list including moves up to current position
        main_line = self.game_tree.current.get_main_line()
        moves_gtp = []

        # Skip root (index 0), iterate through all moves including current
        for node in main_line[1:]:
            if node.is_pass:
                moves_gtp.append('pass')
            elif node.move:
                gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1], board_size)
                moves_gtp.append(gtp_move)

        # Determine initial player (for handicap games)
        initial_stones = []
        root_props = None
        if main_line and len(main_line) > 0 and main_line[0].properties:
            root_props = main_line[0].properties

        if not root_props or ('AB' not in root_props and 'AW' not in root_props):
            if len(main_line) > 1 and main_line[1].properties:
                root_props = main_line[1].properties

        if root_props:
            # Add Black handicap stones (AB property)
            if 'AB' in root_props:
                ab_values = root_props['AB']
                if isinstance(ab_values, list):
                    for stone_pos in ab_values:
                        if stone_pos and len(stone_pos) == 2:
                            try:
                                row = ord(stone_pos[1]) - ord('a')
                                col = ord(stone_pos[0]) - ord('a')
                                gtp_move = KataGoEngine.coords_to_gtp(row, col, board_size)
                                initial_stones.append(["B", gtp_move])
                            except Exception as e:
                                print(f"Error converting handicap stone {stone_pos}: {e}")

        # Determine initial player
        if initial_stones and all(stone[0] == 'B' for stone in initial_stones):
            initial_player = 'W'  # White plays first in Black handicap games
        else:
            initial_player = 'B'  # Normal game

        # Run in background thread
        def analyze_thread():
            try:
                # Call KataGo engine directly with complete move list
                analysis_data = self.katago_engine.analyze_position(
                    moves=moves_gtp,
                    board_size=board_size,
                    komi=komi,
                    initial_player=initial_player,
                    max_visits=self.app_config.get_max_visits(),
                    initial_stones=initial_stones if initial_stones else None,
                    rules=rules
                )

                if analysis_data and 'moveInfos' in analysis_data:
                    # Get the best move (first in the list)
                    best_move_info = analysis_data['moveInfos'][0]
                    move_str = best_move_info.get('move', '')

                    if move_str.lower() == 'pass':
                        # AI wants to pass
                        self.after(0, self._play_pass)
                    else:
                        # AI wants to play a move
                        try:
                            row, col = KataGoEngine.gtp_to_coords(move_str, board_size)
                            # Play the move on the main thread
                            self.after(0, lambda r=row, c=col: self._play_move(r, c))
                        except Exception as e:
                            print(f"Error parsing AI move {move_str}: {e}")
                            self.after(0, lambda: setattr(self, 'is_ai_thinking', False))
                else:
                    # No moves available - reset flag
                    self.after(0, lambda: setattr(self, 'is_ai_thinking', False))

            except Exception as e:
                print(f"AI move error: {e}")
                import traceback
                traceback.print_exc()
                # Reset flag on error
                self.after(0, lambda: setattr(self, 'is_ai_thinking', False))

            finally:
                # Always reset the thinking flag
                self.after(0, lambda: setattr(self, 'is_ai_thinking', False))

        threading.Thread(target=analyze_thread, daemon=True).start()

    def _display_analysis_result(self, analysis: PositionAnalysis) -> None:
        """Display analysis result on board (for explore mode)."""
        if analysis and analysis.top_moves:
            # Extract top 5 move candidates for board display
            candidates = []
            for i, move_analysis in enumerate(analysis.top_moves[:5]):
                if move_analysis.move and not move_analysis.is_pass:
                    row, col = move_analysis.move
                    candidates.append((row, col, i))  # (row, col, rank)

            # Update board canvas with candidates
            self.board_canvas.set_top_move_candidates(candidates)
            self.board_canvas.redraw()

    def _save_analysis_json(self) -> None:
        """Save analysis results to JSON file."""
        if not self.analysis_results or not self.current_sgf_path:
            messagebox.showwarning("No Analysis", "No analysis results to save.")
            return

        import os
        from utils.analysis_export import export_analysis_to_json

        # Generate output filename
        sgf_basename = os.path.splitext(self.current_sgf_path)[0]
        default_path = f"{sgf_basename}_analysis.json"

        # Ask user for save location
        output_path = filedialog.asksaveasfilename(
            title="Save Analysis",
            defaultextension=".json",
            initialfile=os.path.basename(default_path),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if output_path:
            success = export_analysis_to_json(
                self.analysis_results,
                self.current_sgf_path,
                self.game_tree.board_size,
                self.game_tree.get_komi(),
                self.app_config.get_max_visits(),
                output_path
            )

            if success:
                messagebox.showinfo("Success", f"Analysis saved to:\n{output_path}")
            else:
                messagebox.showerror("Error", "Failed to save analysis.")

    def _generate_pdf_report(self, output_path: str) -> None:
        """Generate PDF error report from analysis results.

        Args:
            output_path: Path where PDF should be saved
        """
        if not self.analysis_results or not self.current_sgf_path:
            return

        try:
            from utils.pdf_report import generate_error_report_pdf

            success = generate_error_report_pdf(
                self.analysis_results,
                self.game_tree,
                self.current_sgf_path,
                output_path
            )

            if success:
                print(f"PDF error report saved: {output_path}")
            else:
                print(f"Failed to generate PDF report")

        except ImportError:
            print("ERROR: reportlab not installed. Run: pip install reportlab")
        except Exception as e:
            print(f"Error generating PDF report: {e}")
            import traceback
            traceback.print_exc()

    def _try_load_analysis_json(self, sgf_path: str) -> None:
        """Try to load analysis JSON file for the given SGF.

        Args:
            sgf_path: Path to the SGF file
        """
        import os
        from utils.analysis_export import import_analysis_from_json

        # Check for corresponding JSON file
        sgf_basename = os.path.splitext(sgf_path)[0]
        analysis_path = f"{sgf_basename}_analysis.json"

        if os.path.exists(analysis_path):
            print(f"Found analysis file: {analysis_path}")

            # Load the analysis
            loaded_analysis = import_analysis_from_json(analysis_path)

            if loaded_analysis:
                self.analysis_results = loaded_analysis

                # Extract errors for display
                errors = [(a.move_number, a.played_move, a.point_loss)
                         for a in loaded_analysis if a.is_error]

                # Update analysis panel with errors
                self.analysis_panel.display_errors(errors)

                # Update current position display
                self._update_display()

                print(f"Loaded analysis with {len(loaded_analysis)} positions, {len(errors)} errors")

                # Show notification to user
                messagebox.showinfo(
                    "Analysis Loaded",
                    f"Loaded saved analysis from:\n{os.path.basename(analysis_path)}\n\n"
                    f"Positions analyzed: {len(loaded_analysis)}\n"
                    f"Errors found: {len(errors)}"
                )
            else:
                print(f"Failed to load analysis from: {analysis_path}")
        else:
            # No JSON file exists - analysis was already cleared in _open_sgf
            # This block is now redundant but kept for completeness
            pass

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

            # Convert RGBA to RGB (JPEG doesn't support transparency/alpha channel)
            if screenshot.mode == 'RGBA':
                screenshot = screenshot.convert('RGB')

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save screenshot as JPEG with quality=75 for significant size reduction
            # This typically achieves 1/4 to 1/5 of PNG file size
            screenshot.save(output_path, format='JPEG', quality=75, optimize=True)
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
                    filename = f"move_{move_num:03d}_loss_{point_loss:.1f}pts.jpg"
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
        filename = f"move_{position_to_show:03d}_{player_to_move}_to_move_gap_{gap:.1f}.jpg"
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

    def _handle_setup_click(self, row: int, col: int) -> None:
        """Handle a board click during handicap setup mode.

        Args:
            row: Row index
            col: Column index
        """
        stone = self.board.get_stone(row, col)

        if stone == Stone.BLACK and (row, col) in self._setup_stones_placed:
            # Undo: remove a previously placed setup stone
            self.board.set_stone(row, col, Stone.EMPTY)
            self._setup_stones_placed.remove((row, col))
            self.board_canvas.redraw()
            self._update_setup_status()
        elif stone == Stone.EMPTY and len(self._setup_stones_placed) < self._setup_stones_needed:
            # Place a new setup stone
            self.board.set_stone(row, col, Stone.BLACK)
            self._setup_stones_placed.append((row, col))
            self.board_canvas.redraw()
            self._update_setup_status()

            # Check if all stones have been placed
            if len(self._setup_stones_placed) == self._setup_stones_needed:
                self._finalize_handicap_setup()

    def _finalize_handicap_setup(self) -> None:
        """Finalize manual handicap stone placement and create the game tree structure."""
        from game.handicap import positions_to_sgf

        # Create setup node (first child of root) with AB property
        setup_node = GameNode(parent=self.game_tree.root)
        self.game_tree.root.children.append(setup_node)

        # Set AB property with SGF coordinates of placed stones
        sgf_coords = positions_to_sgf(self._setup_stones_placed)
        setup_node.properties['AB'] = sgf_coords

        # Set current node to setup node and player to White
        self.game_tree.current = setup_node
        self.current_player = Stone.WHITE

        # Exit setup mode
        self._setup_mode = False
        self._set_setup_mode_ui(False)
        self._update_display()

    def _update_setup_status(self) -> None:
        """Update the control panel labels to show setup mode progress."""
        placed = len(self._setup_stones_placed)
        remaining = self._setup_stones_needed - placed
        self.control_panel.player_label.config(
            text=f"Place handicap stones: {remaining} remaining",
            fg="blue"
        )
        self.control_panel.move_label.config(
            text=f"Setup: {placed} / {self._setup_stones_needed} stones"
        )

    def _set_setup_mode_ui(self, enabled: bool) -> None:
        """Enable or disable UI controls during setup mode.

        Args:
            enabled: True to enter setup mode (disable controls),
                     False to exit setup mode (re-enable controls)
        """
        state = tk.DISABLED if enabled else tk.NORMAL

        # Disable/enable mode radio buttons
        self.play_radio.config(state=state)
        self.analysis_radio.config(state=state)
        self.play_ai_radio.config(state=state)
        self.explore_radio.config(state=state)

        # Disable/enable navigation buttons
        self.control_panel.first_btn.config(state=state)
        self.control_panel.prev_btn.config(state=state)
        self.control_panel.next_btn.config(state=state)
        self.control_panel.last_btn.config(state=state)
        self.control_panel.pass_btn.config(state=state)

        if not enabled:
            # Re-enable controls based on actual KataGo state
            self._update_mode_availability()

    def _cancel_setup_mode(self) -> None:
        """Cancel setup mode without creating game tree nodes."""
        if not self._setup_mode:
            return

        # Remove any placed stones from the board
        for row, col in self._setup_stones_placed:
            self.board.set_stone(row, col, Stone.EMPTY)

        self._setup_mode = False
        self._setup_stones_needed = 0
        self._setup_stones_placed = []
        self._set_setup_mode_ui(False)

    def destroy(self) -> None:
        """Clean up resources."""
        # Clean up analyzer engine pool
        if self.analyzer:
            self.analyzer._cleanup_engine_pool()

        # Stop primary engine
        if self.katago_engine:
            self.katago_engine.stop()

        # Close explore window
        if self.explore_window:
            self.explore_window.destroy()

        super().destroy()
