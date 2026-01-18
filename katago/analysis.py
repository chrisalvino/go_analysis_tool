"""KataGo analysis for move evaluation and error detection."""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from game.game_tree import GameTree, GameNode
from game.board import Stone
from katago.engine import KataGoEngine


@dataclass
class MoveAnalysis:
    """Analysis data for a single move."""
    move: Optional[Tuple[int, int]]  # None for pass
    is_pass: bool
    win_rate: float
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

    def __init__(self, engine: KataGoEngine, error_threshold: float = 3.0):
        """Initialize game analyzer.

        Args:
            engine: KataGo engine instance
            error_threshold: Point loss threshold for errors
        """
        self.engine = engine
        self.error_threshold = error_threshold

    def analyze_game(
        self,
        game_tree: GameTree,
        max_visits: int = 200,
        progress_callback: Optional[callable] = None
    ) -> List[PositionAnalysis]:
        """Analyze all moves in a game.

        Args:
            game_tree: Game tree to analyze
            max_visits: Maximum visits per position
            progress_callback: Optional callback(move_num, total) for progress

        Returns:
            List of position analyses
        """
        results = []

        # Get main line moves
        main_line = game_tree.get_main_line()

        if not main_line:
            return results

        # Set up board
        board_size = game_tree.board_size
        self.engine.set_board_size(board_size)
        self.engine.clear_board()

        # Analyze each move
        for i, node in enumerate(main_line):
            if progress_callback:
                progress_callback(i + 1, len(main_line))

            # Skip root
            if node.move is None and not node.is_pass:
                continue

            # Get analysis before the move
            analysis_data = self.engine.analyze_position(max_visits)

            if analysis_data is None:
                continue

            # Parse top moves
            top_moves = self._parse_move_candidates(analysis_data, board_size)

            # Find the played move in the analysis
            played_move_analysis = None
            for move_analysis in top_moves:
                if node.is_pass and move_analysis.is_pass:
                    played_move_analysis = move_analysis
                    break
                elif node.move == move_analysis.move:
                    played_move_analysis = move_analysis
                    break

            # Calculate point loss
            point_loss = 0.0
            is_error = False

            if played_move_analysis and top_moves:
                best_move = top_moves[0]
                point_loss = abs(best_move.score_lead - played_move_analysis.score_lead)

                if point_loss >= self.error_threshold:
                    is_error = True

            # Create position analysis
            pos_analysis = PositionAnalysis(
                move_number=i,
                played_move=node.move,
                played_move_analysis=played_move_analysis,
                top_moves=top_moves[:5],  # Keep top 5
                is_error=is_error,
                point_loss=point_loss
            )

            results.append(pos_analysis)

            # Play the move on the engine's board
            if node.is_pass:
                color = 'B' if node.color == Stone.BLACK else 'W'
                self.engine.play_move(color, 'pass')
            elif node.move:
                color = 'B' if node.color == Stone.BLACK else 'W'
                gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1])
                self.engine.play_move(color, gtp_move)

        return results

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
        self.engine.set_board_size(board_size)
        self.engine.clear_board()

        # Play moves up to the position
        game_tree.go_to_root()
        for _ in range(move_number):
            if not game_tree.go_to_next():
                return None

            node = game_tree.current

            if node.is_pass:
                color = 'B' if node.color == Stone.BLACK else 'W'
                self.engine.play_move(color, 'pass')
            elif node.move:
                color = 'B' if node.color == Stone.BLACK else 'W'
                gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1])
                self.engine.play_move(color, gtp_move)

        # Analyze position
        analysis_data = self.engine.analyze_position(max_visits)

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

        # Sort by order (KataGo already ranks them)
        move_analyses.sort(key=lambda x: x.order)

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
