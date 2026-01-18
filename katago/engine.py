"""KataGo engine interface using GTP protocol."""

import subprocess
import threading
import json
from typing import Optional, List, Dict, Any
from queue import Queue, Empty


class KataGoEngine:
    """Interface to KataGo engine via GTP."""

    def __init__(self, katago_path: str, config_path: str, model_path: str):
        """Initialize KataGo engine.

        Args:
            katago_path: Path to KataGo executable
            config_path: Path to KataGo config file
            model_path: Path to neural network model
        """
        self.katago_path = katago_path
        self.config_path = config_path
        self.model_path = model_path
        self.process: Optional[subprocess.Popen] = None
        self.output_queue: Queue = Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False

    def start(self) -> bool:
        """Start the KataGo engine.

        Returns:
            True if started successfully
        """
        try:
            self.process = subprocess.Popen(
                [
                    self.katago_path,
                    'gtp',
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

            # Start reader thread
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()

            # Send initial commands
            self.send_command('name')
            self.send_command('version')

            return True

        except Exception as e:
            print(f"Failed to start KataGo: {e}")
            return False

    def stop(self) -> None:
        """Stop the KataGo engine."""
        if self.process:
            self.send_command('quit')
            self.process.stdin.close()
            self.process.wait(timeout=5)
            self.running = False
            self.process = None

    def send_command(self, command: str) -> None:
        """Send a GTP command to KataGo.

        Args:
            command: GTP command to send
        """
        if self.process and self.process.stdin:
            self.process.stdin.write(command + '\n')
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
                print(f"Error reading KataGo output: {e}")
                break

    def get_response(self, timeout: float = 10.0) -> Optional[str]:
        """Get a response from KataGo.

        Args:
            timeout: Maximum time to wait for response

        Returns:
            Response string or None if timeout
        """
        response_lines = []

        try:
            while True:
                line = self.output_queue.get(timeout=timeout)

                if not line:
                    continue

                response_lines.append(line)

                # GTP responses end with an empty line or start with = or ?
                if line.startswith('=') or line.startswith('?'):
                    # Read until empty line
                    while True:
                        try:
                            line = self.output_queue.get(timeout=1.0)
                            if not line:
                                break
                            response_lines.append(line)
                        except Empty:
                            break
                    break

        except Empty:
            return None

        return '\n'.join(response_lines)

    def set_board_size(self, size: int) -> bool:
        """Set the board size.

        Args:
            size: Board size (9, 13, or 19)

        Returns:
            True if successful
        """
        self.send_command(f'boardsize {size}')
        response = self.get_response()
        return response is not None and response.startswith('=')

    def clear_board(self) -> bool:
        """Clear the board.

        Returns:
            True if successful
        """
        self.send_command('clear_board')
        response = self.get_response()
        return response is not None and response.startswith('=')

    def play_move(self, color: str, move: str) -> bool:
        """Play a move on the engine's board.

        Args:
            color: 'B' or 'W'
            move: Move in GTP format (e.g., 'D4', 'pass')

        Returns:
            True if successful
        """
        self.send_command(f'play {color} {move}')
        response = self.get_response()
        return response is not None and response.startswith('=')

    def analyze_position(self, max_visits: int = 200) -> Optional[Dict[str, Any]]:
        """Analyze the current position using kata-analyze.

        Args:
            max_visits: Maximum number of visits for analysis

        Returns:
            Analysis results as dict, or None if failed
        """
        # Use kata-analyze command
        command = f'kata-analyze interval 1000 maxVisits {max_visits}'
        self.send_command(command)

        # Wait for analysis result
        try:
            response_lines = []
            while True:
                line = self.output_queue.get(timeout=30.0)

                if not line:
                    continue

                # kata-analyze returns JSON on info lines
                if line.startswith('info'):
                    # Extract JSON from info line
                    json_start = line.find('info move')
                    if json_start != -1:
                        json_str = line[json_start + 10:].strip()
                        try:
                            data = json.loads(json_str)
                            # Stop analysis
                            self.send_command('kata-analyze-stop')
                            return data
                        except json.JSONDecodeError:
                            continue

        except Empty:
            return None

        return None

    @staticmethod
    def coords_to_gtp(row: int, col: int) -> str:
        """Convert board coordinates to GTP format.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            GTP move string (e.g., 'D4')
        """
        # Column: A-H, J-T (skip I)
        col_letter = chr(ord('A') + col if col < 8 else ord('A') + col + 1)
        # Row: 1-19 (from bottom)
        # Note: We need to know board size to convert properly
        # For now, assume standard conversion
        row_num = 19 - row  # Assuming 19x19, need to adjust based on actual size
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
