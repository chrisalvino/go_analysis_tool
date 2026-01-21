# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

Dependencies are minimal (sgfmill for SGF parsing, Pillow for screenshots). Python 3.8+ required with tkinter.

### Virtual Environment
```bash
# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

## Architecture Overview

### Core Design Pattern: MVC with Tkinter

The application follows a Model-View-Controller pattern adapted for Tkinter:

- **Model**: `game/` modules manage game state (board, rules, game tree)
- **View**: `ui/` modules handle rendering and user interaction
- **Controller**: `ui/main_window.py` coordinates between UI, game logic, and KataGo engine

### Key Architectural Components

#### 1. Game State Management (game/)

- **Board** (`game/board.py`): Immutable board representation with stone positions, captures, and group analysis (liberties, connected stones)
- **GoRules** (`game/rules.py`): Rules engine that validates moves (ko, suicide, captures) and maintains ko state
- **GameTree** (`game/game_tree.py`): Tree structure for move history and variations. Supports SGF-style branching with parent/child navigation

**Critical**: Board state is NOT automatically synchronized with GameTree. When navigating moves, you must:
1. Reconstruct board state by replaying moves from root to current node
2. Update rules engine ko state accordingly
3. This pattern is implemented in `main_window.py:_navigate_to_node()`

#### 2. KataGo Integration (katago/)

- **KataGoEngine** (`katago/engine.py`): Manages subprocess communication with KataGo via JSON analysis protocol (NOT GTP). Handles stdin/stdout/stderr threads and query/response matching
- **GameAnalyzer** (`katago/analysis.py`): Orchestrates parallel game analysis using thread pool of KataGo engines

**Parallel Analysis Architecture**:
- Primary engine is always running (started in `main_window.py`)
- For batch analysis, `GameAnalyzer` spawns N-1 additional engines
- Work is distributed via ThreadPoolExecutor
- Each engine analyzes different positions independently
- Results are collected and sorted by move number

**Configuration**: Analysis timeout (`analysis_timeout`) is critical - increase if positions are complex or `max_visits` is high (200+).

#### 3. SGF File Format (sgf/)

- **SGFParser** (`sgf/parser.py`): Parses SGF files into GameTree structure. Handles variations and standard properties (SZ, B, W, AB, AW, etc.)
- **SGFWriter** (`sgf/writer.py`): Serializes GameTree back to SGF format

The parser reconstructs the tree structure from SGF, preserving variations as child nodes.

#### 4. UI Components (ui/)

- **MainWindow** (`ui/main_window.py`): Central coordinator. Manages mode switching (Play vs Analysis), KataGo lifecycle, and file operations
- **BoardCanvas** (`ui/board_canvas.py`): Custom Tkinter Canvas that renders board, stones, move markers, error indicators, and top move candidates
- **ControlPanel** (`ui/control_panel.py`): Game navigation controls (first/prev/next/last, pass, clear)
- **AnalysisPanel** (`ui/analysis_panel.py`): Displays analysis results - top 5 moves with win rate/score, error list with point loss

**Mode System**: Play mode enables stone placement; Analysis mode disables placement and shows analysis UI.

#### 5. Configuration (utils/)

- **Config** (`utils/config.py`): JSON-based configuration stored in `config.json`. Key settings:
  - `katago.executable_path`, `config_path`, `model_path`: KataGo setup
  - `katago.max_visits`: Analysis depth (default: 200)
  - `katago.analysis_timeout`: Timeout in seconds (default: 180)
  - `analysis.error_threshold`: Point loss to flag errors (default: 7.0)
  - `analysis.analysis_threads`: Parallel analysis threads (default: 1, max: 8)

- **KataGoSetup** (`utils/katago_setup.py`): Automated KataGo installation. Detects system KataGo (Homebrew, system PATH) or downloads binaries and neural networks.

### Critical Implementation Details

#### Move Navigation and Board Reconstruction

When navigating to a game node:
1. Get full move path from root to target node via `node.get_main_line()`
2. Create fresh Board instance
3. Replay ALL moves in sequence
4. Update GoRules ko state
5. Update BoardCanvas

See `main_window.py:_navigate_to_node()` for reference implementation.

#### Thread Safety with KataGo

- Each KataGo engine runs in a separate subprocess
- Engine communication uses thread-safe Queue for responses
- Multiple engines can analyze different positions concurrently
- Engines must be properly stopped on cleanup (`analyzer._cleanup_engine_pool()`)

#### Error Detection Logic

Errors are detected by comparing:
1. Expected score of best move (from analysis at position N)
2. Actual score after played move (from analysis at position N+1)
3. If point loss > `error_threshold`, mark as error

Implementation in `GameAnalyzer.analyze_game()`.

## Common Patterns

### Adding a New UI Feature

1. Add UI components in relevant `ui/*.py` file
2. Wire callbacks to `main_window.py` methods
3. Update board/game state as needed
4. Call `self.board_canvas.redraw()` to refresh display

### Modifying Analysis Behavior

1. Analysis logic lives in `katago/analysis.py`
2. KataGo query format: JSON with `id`, `moves`, `rules`, `komi`, `boardXSize`, `boardYSize`, `analyzeTurns`, `maxVisits`
3. Response format: JSON with `id`, `turnNumber`, `moveInfos` array
4. See `GameAnalyzer.analyze_position()` for query construction

### Working with SGF Files

1. SGF coordinates are letters (a-s), not numbers
2. Use `SGFParser.coords_to_pos()` / `pos_to_coords()` for conversion
3. Root node contains game properties (board size, rules, player names)
4. Move nodes contain B (black) or W (white) properties

## KataGo Setup

The app supports three KataGo setup methods:

1. **Homebrew/System Package**: Auto-detected via `shutil.which('katago')`
2. **Auto-download**: Downloads binaries + neural network to `katago_data/`
3. **Manual**: User provides paths via Settings dialog

System detection happens in `KataGoSetup.check_system_katago()`. If found, the app uses system KataGo and installed neural networks (common locations: `/opt/homebrew/Cellar/katago/`, `/usr/share/katago/`).

## Testing Notes

No automated test suite currently exists. Testing is manual:

1. Test new features with various board sizes (9x9, 13x13, 19x19)
2. Test with real SGF files from different sources
3. Verify KataGo analysis doesn't timeout or crash
4. Check thread pool cleanup (no zombie processes after analysis)

## File Operations

- SGF files are loaded via `File > Open SGF`
- Saved via `File > Save SGF`
- Screenshots captured via `File > Screenshot` (saves to same directory as SGF with `.png` extension)
- Current file path stored in `main_window.current_sgf_path`
