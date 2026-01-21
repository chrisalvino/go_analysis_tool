"""KataGo engine interface using GTP protocol."""

import subprocess
import threading
import json
from typing import Optional, List, Dict, Any
from queue import Queue, Empty


class KataGoEngine:
    """Interface to KataGo engine via GTP."""

    def __init__(self, katago_path: str, config_path: str, model_path: str, analysis_timeout: int = 120):
        """Initialize KataGo engine.

        Args:
            katago_path: Path to KataGo executable
            config_path: Path to KataGo config file
            model_path: Path to neural network model
            analysis_timeout: Timeout in seconds for analysis operations (default: 120)
        """
        self.katago_path = katago_path
        self.config_path = config_path
        self.model_path = model_path
        self.process: Optional[subprocess.Popen] = None
        self.output_queue: Queue = Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False
        self.analysis_timeout = analysis_timeout  # Configurable timeout
        self.query_counter = 0  # For unique query IDs

    def start(self) -> bool:
        """Start the KataGo engine in analysis mode.

        Returns:
            True if started successfully
        """
        try:
            self.process = subprocess.Popen(
                [
                    self.katago_path,
                    'analysis',
                    '-config', self.config_path,
                    '-model', self.model_path
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            self.running = True

            # Start reader threads
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()

            # Start stderr reader to catch errors
            self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            self.stderr_thread.start()

            print("KataGo started in analysis mode")

            # Give KataGo a moment to start up
            import time
            time.sleep(0.5)

            # Check if process is still alive
            if self.process.poll() is not None:
                print(f"ERROR: KataGo process terminated immediately with code {self.process.poll()}")
                return False

            return True

        except Exception as e:
            print(f"Failed to start KataGo: {e}")
            return False

    def stop(self) -> None:
        """Stop the KataGo engine."""
        if self.process:
            self.running = False
            self.process.stdin.close()
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None

    def send_query(self, query: dict) -> None:
        """Send a JSON query to KataGo.

        Args:
            query: JSON query dict
        """
        if self.process and self.process.stdin:
            # Check if process is still alive
            if self.process.poll() is not None:
                raise RuntimeError(f"KataGo process has terminated with code {self.process.poll()}")

            query_json = json.dumps(query)
            self.process.stdin.write(query_json + '\n')
            self.process.stdin.flush()

    def _read_output(self) -> None:
        """Read output from KataGo (runs in separate thread)."""
        if not self.process or not self.process.stdout:
            return

        while self.running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.output_queue.put(line.strip())
            except Exception as e:
                if self.running:
                    print(f"Error reading KataGo output: {e}")
                break

    def _read_stderr(self) -> None:
        """Read stderr from KataGo to catch errors."""
        if not self.process or not self.process.stderr:
            return

        while self.running:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                # Print stderr to console for debugging
                print(f"KataGo stderr: {line.strip()}")
            except Exception as e:
                if self.running:
                    print(f"Error reading KataGo stderr: {e}")
                break

    def analyze_position(self, moves: List[str], board_size: int = 19, komi: float = 7.5,
                        initial_player: str = 'B', max_visits: int = 200) -> Optional[Dict[str, Any]]:
        """Analyze a position using kata-analyze.

        Args:
            moves: List of moves in GTP format (e.g., ["D4", "Q16", "D16"])
            board_size: Board size (9, 13, or 19)
            komi: Komi value
            initial_player: Who plays first ('B' or 'W')
            max_visits: Maximum number of visits for analysis

        Returns:
            Analysis results as dict, or None if failed
        """
        # Convert moves to kata-analyze format: [["b", "D4"], ["w", "Q16"], ...]
        formatted_moves = []
        current_player = initial_player.upper()
        for move in moves:
            formatted_moves.append([current_player, move])
            # Alternate player
            current_player = 'W' if current_player == 'B' else 'B'

        # Build query
        self.query_counter += 1
        query = {
            "id": f"query_{self.query_counter}",
            "moves": formatted_moves,
            "rules": "chinese",
            "komi": komi,
            "boardXSize": board_size,
            "boardYSize": board_size,
            "initialPlayer": initial_player,
            "analyzeTurns": [len(moves)],  # Analyze after all moves
            "maxVisits": max_visits,
            "includeOwnership": False,
            "includePolicy": False
        }

        # Send query
        self.send_query(query)

        # Wait for response
        try:
            while True:
                line = self.output_queue.get(timeout=self.analysis_timeout)

                if not line:
                    continue

                # Parse JSON response
                try:
                    result = json.loads(line)

                    # Check if this is our response
                    if result.get('id') == query['id']:
                        # Extract move info for the position we analyzed
                        if 'turnNumber' in result and result['turnNumber'] == len(moves):
                            if 'moveInfos' in result:
                                move_infos = []
                                for move_info in result['moveInfos']:
                                    # kata-analyze provides REAL scoreLead always!
                                    data = {
                                        'move': move_info.get('move', ''),
                                        'visits': move_info.get('visits', 0),
                                        'winrate': move_info.get('winrate', 0.5),
                                        'scoreLead': move_info.get('scoreLead', 0.0),
                                        'order': move_info.get('order', 0)
                                    }
                                    move_infos.append(data)

                                return {'moveInfos': move_infos}

                except (json.JSONDecodeError, ValueError):
                    # Not JSON or bad format, skip
                    continue

        except Empty:
            print(f"Warning: Timeout waiting for KataGo analysis response (timeout: {self.analysis_timeout}s)")
            return None

        return None

    # Stub methods for compatibility - no longer needed in analysis mode
    def set_board_size(self, size: int) -> bool:
        """Stub - not used in analysis mode."""
        return True

    def clear_board(self) -> bool:
        """Stub - not used in analysis mode."""
        return True

    def play_move(self, color: str, move: str) -> bool:
        """Stub - not used in analysis mode."""
        return True

    @staticmethod
    def coords_to_gtp(row: int, col: int, board_size: int = 19) -> str:
        """Convert board coordinates to GTP format.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)
            board_size: Board size (9, 13, or 19)

        Returns:
            GTP move string (e.g., 'D4')
        """
        # Column: A-H, J-T (skip I)
        col_letter = chr(ord('A') + col if col < 8 else ord('A') + col + 1)
        # Row: 1-board_size (from bottom)
        row_num = board_size - row
        return f'{col_letter}{row_num}'

    @staticmethod
    def gtp_to_coords(gtp_move: str, board_size: int = 19) -> tuple:
        """Convert GTP format to board coordinates.

        Args:
            gtp_move: GTP move string (e.g., 'D4')
            board_size: Size of the board

        Returns:
            (row, col) tuple
        """
        if gtp_move.lower() == 'pass':
            return None

        col_letter = gtp_move[0].upper()
        row_num = int(gtp_move[1:])

        # Convert column
        if col_letter < 'I':
            col = ord(col_letter) - ord('A')
        else:
            col = ord(col_letter) - ord('A') - 1

        # Convert row
        row = board_size - row_num

        return row, col
