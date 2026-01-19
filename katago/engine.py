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
        self.next_player = 'B'  # Track whose turn it is
        self.analysis_timeout = analysis_timeout  # Configurable timeout

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
        self.next_player = 'B'  # Reset to black after clearing
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
        # Use longer timeout for play commands (they can be slow if engine is busy)
        response = self.get_response(timeout=30.0)
        # Switch player
        if response is not None and response.startswith('='):
            self.next_player = 'W' if color == 'B' else 'B'
            return True
        return False

    def analyze_position(self, max_visits: int = 200) -> Optional[Dict[str, Any]]:
        """Analyze the current position using lz-genmove_analyze.

        Args:
            max_visits: Maximum number of visits for analysis

        Returns:
            Analysis results as dict, or None if failed
        """
        # Use lz-genmove_analyze command: lz-genmove_analyze PLAYER maxVisits
        command = f'lz-genmove_analyze {self.next_player} {max_visits}'
        self.send_command(command)

        # Wait for analysis result
        try:
            move_infos = []
            line_count = 0
            while True:
                line = self.output_queue.get(timeout=self.analysis_timeout)

                if not line:
                    continue

                line_count += 1

                # Check for final result line starting with "play"
                if line.startswith('play '):
                    # Debug: show what we collected
                    if line_count < 10:
                        print(f"DEBUG: Got {len(move_infos)} move_infos from {line_count} lines")
                    # Return collected move data
                    return {'moveInfos': move_infos}

                # Parse info lines
                if line.startswith('info move '):
                    # Debug first few
                    if len(move_infos) < 3:
                        print(f"DEBUG RAW: {line[:200]}")

                    # IMPORTANT: Each line may contain MULTIPLE "info move" sections!
                    # Split the line by " info move " to get all candidates
                    # Example: "info move Q16 visits 100 ... info move D4 visits 50 ..."
                    segments = line.split(' info move ')

                    for i, segment in enumerate(segments):
                        if not segment.strip():
                            continue

                        # Add "info move " prefix back
                        if i == 0:
                            # First segment starts with "info move "
                            parse_line = segment
                        else:
                            # Subsequent segments need "info move " added back
                            parse_line = 'info move ' + segment

                        move_data = self._parse_info_line(parse_line)
                        if move_data:
                            move_infos.append(move_data)

        except Empty:
            print(f"Warning: Timeout waiting for KataGo analysis response (timeout: {self.analysis_timeout}s)")
            return None

        return None

    def _parse_info_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse an info line from lz-genmove_analyze.

        Args:
            line: Info line like "info move Q16 visits 166 winrate 6310 ..."

        Returns:
            Dictionary with move data or None if parse fails
        """
        try:
            parts = line.split()
            if len(parts) < 4 or parts[0] != 'info' or parts[1] != 'move':
                return None

            move_str = parts[2]
            data = {'move': move_str}

            # Parse key-value pairs
            i = 3
            while i < len(parts):
                key = parts[i]
                if i + 1 < len(parts):
                    value_str = parts[i + 1]

                    # Handle special keys
                    if key == 'pv':
                        # PV is the rest of the line
                        data['pv'] = ' '.join(parts[i + 1:])
                        break
                    elif key in ['visits', 'order']:
                        data[key] = int(value_str)
                    elif key in ['winrate', 'prior', 'lcb']:
                        # These are in units of 0.0001 (10000 = 1.0 = 100%)
                        data[key] = float(value_str) / 10000.0
                    else:
                        data[key] = value_str

                    i += 2
                else:
                    i += 1

            # Calculate scoreLead from KataGo's evaluation metric (rough approximation)
            # KataGo's evaluation is percentage-like (0.0-1.0 scale)
            if 'winrate' in data:
                # Simple approximation: 0.60 = ~10 point lead
                wr = data['winrate']
                # Convert evaluation (0.5 = even) to approximate score
                data['scoreLead'] = (wr - 0.5) * 40.0  # Rough approximation

            return data

        except Exception as e:
            print(f"Warning: Error parsing KataGo info line: {e}")
            return None

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
