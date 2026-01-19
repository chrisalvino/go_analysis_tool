"""KataGo analysis for move evaluation and error detection."""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from game.game_tree import GameTree, GameNode
from game.board import Stone
from katago.engine import KataGoEngine


@dataclass
class MoveAnalysis:
    """Analysis data for a single move."""
    move: Optional[Tuple[int, int]]  # None for pass
    is_pass: bool
    win_rate: float  # Internal evaluation metric (not displayed to user)
    score_lead: float
    visits: int
    order: int  # Ranking (0 = best)


@dataclass
class PositionAnalysis:
    """Analysis data for a position."""
    move_number: int
    played_move: Optional[Tuple[int, int]]
    played_move_analysis: Optional[MoveAnalysis]
    top_moves: List[MoveAnalysis]
    is_error: bool
    point_loss: float


class GameAnalyzer:
    """Analyzes Go games using KataGo."""

    def __init__(self, engine: KataGoEngine, error_threshold: float = 3.0, num_threads: int = 1):
        """Initialize game analyzer.

        Args:
            engine: Primary KataGo engine instance
            error_threshold: Point loss threshold for errors
            num_threads: Number of parallel analysis threads (1-8)
        """
        self.primary_engine = engine
        self.error_threshold = error_threshold
        self.num_threads = max(1, min(8, num_threads))
        self.engine_pool: List[KataGoEngine] = []
        self.pool_lock = threading.Lock()

    def _create_engine_pool(self, katago_path: str, config_path: str, model_path: str, analysis_timeout: int) -> None:
        """Create a pool of KataGo engines for parallel analysis.

        Args:
            katago_path: Path to KataGo executable
            config_path: Path to config file
            model_path: Path to model file
            analysis_timeout: Timeout in seconds for analysis operations
        """
        # Clean up existing pool
        self._cleanup_engine_pool()

        # Create engines for parallel analysis (excluding primary)
        for i in range(self.num_threads - 1):
            try:
                engine = KataGoEngine(katago_path, config_path, model_path, analysis_timeout)
                if engine.start():
                    self.engine_pool.append(engine)
                    print(f"Started analysis engine {i + 2}/{self.num_threads}")
                else:
                    print(f"Failed to start analysis engine {i + 2}")
            except Exception as e:
                print(f"Error creating engine {i + 2}: {e}")

    def _cleanup_engine_pool(self) -> None:
        """Clean up engine pool."""
        with self.pool_lock:
            for engine in self.engine_pool:
                try:
                    engine.stop()
                except:
                    pass
            self.engine_pool.clear()

    def analyze_game(
        self,
        game_tree: GameTree,
        max_visits: int = 200,
        progress_callback: Optional[callable] = None,
        katago_path: str = None,
        config_path: str = None,
        model_path: str = None,
        analysis_timeout: int = 120
    ) -> List[PositionAnalysis]:
        """Analyze all moves in a game.

        Args:
            game_tree: Game tree to analyze
            max_visits: Maximum visits per position
            progress_callback: Optional callback(move_num, total) for progress
            katago_path: Path to KataGo executable (for parallel engines)
            config_path: Path to config (for parallel engines)
            model_path: Path to model (for parallel engines)
            analysis_timeout: Timeout in seconds for analysis operations

        Returns:
            List of position analyses
        """
        # Get main line moves
        main_line = game_tree.get_main_line()

        if not main_line:
            return []

        board_size = game_tree.board_size

        # Decide between sequential and parallel analysis
        if self.num_threads <= 1 or not all([katago_path, config_path, model_path]):
            # Sequential analysis (single-threaded)
            return self._analyze_sequential(
                main_line, board_size, max_visits, progress_callback
            )
        else:
            # Parallel analysis (multi-threaded)
            print(f"Using {self.num_threads} parallel analysis threads")
            return self._analyze_parallel(
                main_line, board_size, max_visits, progress_callback,
                katago_path, config_path, model_path, analysis_timeout
            )

    def _analyze_sequential(
        self,
        main_line: List[GameNode],
        board_size: int,
        max_visits: int,
        progress_callback: Optional[callable]
    ) -> List[PositionAnalysis]:
        """Sequential single-threaded analysis.

        Args:
            main_line: List of game nodes to analyze
            board_size: Board size
            max_visits: Maximum visits per position
            progress_callback: Progress callback

        Returns:
            List of position analyses
        """
        results = []

        # Set up board
        self.primary_engine.set_board_size(board_size)
        self.primary_engine.clear_board()

        # Analyze each move
        for i, node in enumerate(main_line):
            if progress_callback:
                progress_callback(i + 1, len(main_line))

            # Skip root
            if node.move is None and not node.is_pass:
                continue

            # Get analysis before the move
            import time
            start_time = time.time()
            print(f"Analyzing move {i}/{len(main_line)}...")
            analysis_data = self.primary_engine.analyze_position(max_visits)
            elapsed = time.time() - start_time
            print(f"Move {i} completed in {elapsed:.1f}s")

            if analysis_data is None:
                print(f"WARNING: Move {i} returned None (likely timeout)")
                continue

            # Parse and create analysis
            pos_analysis = self._create_position_analysis(
                i, node, analysis_data, board_size
            )

            # Debug: Print what we got
            if pos_analysis.is_error:
                print(f"DEBUG: Error detected at move {i}: point_loss={pos_analysis.point_loss:.1f}")
            elif i < 5:  # Print first few moves for debugging
                if pos_analysis.played_move_analysis and pos_analysis.top_moves:
                    best = pos_analysis.top_moves[0]
                    played = pos_analysis.played_move_analysis
                    print(f"DEBUG Move {i}: Best Score={best.score_lead:.1f}, Played Score={played.score_lead:.1f}, Loss={pos_analysis.point_loss:.1f}")

            results.append(pos_analysis)

            # Play the move on the engine's board
            if node.is_pass:
                color = 'B' if node.color == Stone.BLACK else 'W'
                self.primary_engine.play_move(color, 'pass')
            elif node.move:
                color = 'B' if node.color == Stone.BLACK else 'W'
                gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1], board_size)
                self.primary_engine.play_move(color, gtp_move)

        return results

    def _analyze_parallel(
        self,
        main_line: List[GameNode],
        board_size: int,
        max_visits: int,
        progress_callback: Optional[callable],
        katago_path: str,
        config_path: str,
        model_path: str,
        analysis_timeout: int
    ) -> List[PositionAnalysis]:
        """Parallel multi-threaded analysis.

        Args:
            main_line: List of game nodes to analyze
            board_size: Board size
            max_visits: Maximum visits per position
            progress_callback: Progress callback
            katago_path: Path to KataGo executable
            config_path: Path to config
            model_path: Path to model
            analysis_timeout: Timeout in seconds for analysis operations

        Returns:
            List of position analyses
        """
        # Create engine pool for parallel analysis
        self._create_engine_pool(katago_path, config_path, model_path, analysis_timeout)

        # All engines (primary + pool)
        all_engines = [self.primary_engine] + self.engine_pool
        actual_threads = len(all_engines)

        print(f"Using {actual_threads} parallel analysis threads")

        # Create locks for each engine to prevent concurrent access
        engine_locks = [threading.Lock() for _ in all_engines]

        results = [None] * len(main_line)
        completed_count = [0]  # Use list for mutable closure
        lock = threading.Lock()

        def analyze_move(move_index: int, node: GameNode, engine: KataGoEngine, engine_lock: threading.Lock) -> Optional[PositionAnalysis]:
            """Analyze a single move."""
            import time
            try:
                # Skip root
                if node.move is None and not node.is_pass:
                    return None

                start_time = time.time()
                print(f"[Thread] Starting move {move_index}/{len(main_line)}...")

                # Lock this engine to prevent concurrent access
                with engine_lock:
                    # Set up board to this position
                    engine.set_board_size(board_size)
                    engine.clear_board()

                    # Replay moves up to this position
                    for j in range(move_index):
                        prev_node = main_line[j]
                        if prev_node.is_pass:
                            color = 'B' if prev_node.color == Stone.BLACK else 'W'
                            success = engine.play_move(color, 'pass')
                            if not success:
                                print(f"WARNING: Failed to replay pass at move {j}")
                        elif prev_node.move:
                            color = 'B' if prev_node.color == Stone.BLACK else 'W'
                            gtp_move = KataGoEngine.coords_to_gtp(prev_node.move[0], prev_node.move[1], board_size)
                            success = engine.play_move(color, gtp_move)
                            if not success:
                                print(f"WARNING: Failed to replay move {j} ({gtp_move})")
                                # Try to recover by clearing and restarting
                                engine.clear_board()
                                # Re-replay from the beginning
                                for k in range(j + 1):
                                    retry_node = main_line[k]
                                    if retry_node.is_pass:
                                        retry_color = 'B' if retry_node.color == Stone.BLACK else 'W'
                                        engine.play_move(retry_color, 'pass')
                                    elif retry_node.move:
                                        retry_color = 'B' if retry_node.color == Stone.BLACK else 'W'
                                        retry_gtp = KataGoEngine.coords_to_gtp(retry_node.move[0], retry_node.move[1], board_size)
                                        engine.play_move(retry_color, retry_gtp)
                                break

                    # Analyze the position before this move
                    analysis_data = engine.analyze_position(max_visits)

                elapsed = time.time() - start_time
                print(f"[Thread] Move {move_index} completed in {elapsed:.1f}s")

                if analysis_data is None:
                    print(f"WARNING: Move {move_index} returned None (likely timeout)")
                    return None

                # Create analysis
                pos_analysis = self._create_position_analysis(
                    move_index, node, analysis_data, board_size
                )

                # Update progress
                with lock:
                    completed_count[0] += 1
                    if progress_callback:
                        progress_callback(completed_count[0], len(main_line))

                return pos_analysis

            except Exception as e:
                print(f"Error analyzing move {move_index}: {e}")
                return None

        # Submit tasks to thread pool
        with ThreadPoolExecutor(max_workers=actual_threads) as executor:
            # Map moves to engines in round-robin fashion
            futures = {}

            for i, node in enumerate(main_line):
                # Assign to engine based on index (round-robin)
                engine_idx = i % actual_threads
                engine = all_engines[engine_idx]
                engine_lock = engine_locks[engine_idx]

                # Submit task
                future = executor.submit(analyze_move, i, node, engine, engine_lock)
                futures[future] = i

            # Collect results as they complete
            for future in as_completed(futures):
                move_idx = futures[future]
                try:
                    result = future.result()
                    if result:
                        results[move_idx] = result
                except Exception as e:
                    print(f"Error processing move {move_idx}: {e}")

        # Clean up engine pool
        self._cleanup_engine_pool()

        # Filter out None results and return
        return [r for r in results if r is not None]

    def _create_position_analysis(
        self,
        move_number: int,
        node: GameNode,
        analysis_data: Dict[str, Any],
        board_size: int
    ) -> PositionAnalysis:
        """Create PositionAnalysis from raw analysis data.

        Args:
            move_number: Move number
            node: Game node
            analysis_data: Raw analysis from engine
            board_size: Board size

        Returns:
            PositionAnalysis object
        """
        # Parse top moves
        top_moves = self._parse_move_candidates(analysis_data, board_size)

        # Debug: Show what we parsed
        if move_number < 3:
            print(f"DEBUG: Move {move_number} - Parsed {len(top_moves)} candidates")
            for i, m in enumerate(top_moves[:3]):
                print(f"  {i+1}. Move={m.move}, Score={m.score_lead:.2f}, Order={m.order}")

        # Find the played move in the analysis
        played_move_analysis = None
        for move_analysis in top_moves:
            if node.is_pass and move_analysis.is_pass:
                played_move_analysis = move_analysis
                break
            elif node.move == move_analysis.move:
                played_move_analysis = move_analysis
                break

        # Debug: Did we find the played move?
        if move_number < 3:
            if played_move_analysis:
                print(f"DEBUG: Found played move in candidates at order={played_move_analysis.order}")
            else:
                print(f"DEBUG: WARNING - Played move NOT found in candidates! Node move={node.move}, is_pass={node.is_pass}")

        # Calculate point loss
        point_loss = 0.0
        is_error = False

        if played_move_analysis and top_moves:
            best_move = top_moves[0]

            # Calculate point loss directly from score difference
            score_diff = abs(best_move.score_lead - played_move_analysis.score_lead)
            point_loss = score_diff

            # Debug output for first few moves AND any significant differences
            if move_number < 3 or score_diff > 1.0:
                print(f"DEBUG Move {move_number}: Best={best_move.move} Score={best_move.score_lead:.1f}, Played={played_move_analysis.move if not played_move_analysis.is_pass else 'pass'} Score={played_move_analysis.score_lead:.1f}")
                print(f"  Point loss={point_loss:.1f}, Threshold={self.error_threshold}, Is Error={point_loss >= self.error_threshold}")

            if point_loss >= self.error_threshold:
                is_error = True
        elif move_number < 3:
            print(f"DEBUG: Cannot calculate point loss - played_move_analysis={played_move_analysis is not None}, top_moves={len(top_moves) if top_moves else 0}")

        # Create position analysis
        return PositionAnalysis(
            move_number=move_number,
            played_move=node.move,
            played_move_analysis=played_move_analysis,
            top_moves=top_moves[:5],  # Keep top 5
            is_error=is_error,
            point_loss=point_loss
        )

    def analyze_position(
        self,
        game_tree: GameTree,
        move_number: int,
        max_visits: int = 200
    ) -> Optional[PositionAnalysis]:
        """Analyze a specific position.

        Args:
            game_tree: Game tree
            move_number: Move number to analyze
            max_visits: Maximum visits

        Returns:
            Position analysis or None
        """
        # Set up board to the position
        board_size = game_tree.board_size
        self.primary_engine.set_board_size(board_size)
        self.primary_engine.clear_board()

        # Play moves up to the position
        game_tree.go_to_root()
        for _ in range(move_number):
            if not game_tree.go_to_next():
                return None

            node = game_tree.current

            if node.is_pass:
                color = 'B' if node.color == Stone.BLACK else 'W'
                self.primary_engine.play_move(color, 'pass')
            elif node.move:
                color = 'B' if node.color == Stone.BLACK else 'W'
                gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1], board_size)
                self.primary_engine.play_move(color, gtp_move)

        # Analyze position
        analysis_data = self.primary_engine.analyze_position(max_visits)

        if analysis_data is None:
            return None

        # Parse top moves
        top_moves = self._parse_move_candidates(analysis_data, board_size)

        # Get current node
        node = game_tree.current

        # Find played move
        played_move_analysis = None
        if game_tree.has_next():
            game_tree.go_to_next()
            next_node = game_tree.current

            for move_analysis in top_moves:
                if next_node.is_pass and move_analysis.is_pass:
                    played_move_analysis = move_analysis
                    break
                elif next_node.move == move_analysis.move:
                    played_move_analysis = move_analysis
                    break

            game_tree.go_to_previous()

        # Create analysis
        pos_analysis = PositionAnalysis(
            move_number=move_number,
            played_move=node.move if node else None,
            played_move_analysis=played_move_analysis,
            top_moves=top_moves[:5],
            is_error=False,
            point_loss=0.0
        )

        return pos_analysis

    def _parse_move_candidates(self, analysis_data: Dict[str, Any], board_size: int) -> List[MoveAnalysis]:
        """Parse move candidates from KataGo analysis.

        Args:
            analysis_data: Raw analysis data from KataGo
            board_size: Board size

        Returns:
            List of move analyses, sorted by rank
        """
        move_analyses = []

        # KataGo returns moveInfos array
        if 'moveInfos' not in analysis_data:
            return move_analyses

        for i, move_info in enumerate(analysis_data['moveInfos']):
            move_str = move_info.get('move', '')

            # Parse move
            is_pass = move_str.lower() == 'pass'
            move = None

            if not is_pass:
                try:
                    move = KataGoEngine.gtp_to_coords(move_str, board_size)
                except:
                    continue

            # Extract stats
            win_rate = move_info.get('winrate', 0.0)
            score_lead = move_info.get('scoreLead', 0.0)
            visits = move_info.get('visits', 0)
            order = move_info.get('order', i)

            move_analysis = MoveAnalysis(
                move=move,
                is_pass=is_pass,
                win_rate=win_rate,
                score_lead=score_lead,
                visits=visits,
                order=order
            )

            move_analyses.append(move_analysis)

        # Deduplicate moves - keep the one with most visits for each position
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
        move_analyses = list(seen_moves.values())

        # Sort by score_lead (descending - higher score is better for current player)
        move_analyses.sort(key=lambda x: x.score_lead, reverse=True)

        return move_analyses

    def get_error_moves(self, analyses: List[PositionAnalysis]) -> List[Tuple[int, Tuple[int, int]]]:
        """Extract error moves from analyses.

        Args:
            analyses: List of position analyses

        Returns:
            List of (move_number, (row, col)) for errors
        """
        errors = []

        for analysis in analyses:
            if analysis.is_error and analysis.played_move:
                errors.append((analysis.move_number, analysis.played_move))

        return errors
