# Go Analysis Tool

A Python-based Go game analysis tool with Tkinter UI, featuring full gameplay support, SGF file handling, and AI-powered analysis using KataGo.

## Features

- **Full Go Gameplay**: Play games with complete rule enforcement (captures, ko detection, etc.)
- **Multiple Board Sizes**: Support for 9x9, 13x13, and 19x19 boards
- **SGF Support**: Read and write SGF (Smart Game Format) files with variation support
- **KataGo Integration**: AI analysis with top move recommendations
- **Parallel Analysis**: Multi-threaded game analysis (up to 8x faster with 8 threads)
- **Automated KataGo Setup**: One-click download and configuration, or use system-installed KataGo
- **Error Detection**: Automatically identify significant mistakes based on point loss
- **Interactive UI**: Tkinter-based interface with visual board, game navigation, and analysis display

## Requirements

- Python 3.8 or higher
- tkinter (usually included with Python)
- Internet connection (for automatic KataGo setup, if not using system installation)

## Installation

1. Clone or download this repository

2. Ensure Python 3.8+ is installed:
```bash
python --version
```

3. (Optional) Install sgfmill for enhanced SGF parsing:
```bash
pip install -r requirements.txt
```

## Quick Start

1. Run the application:
```bash
python main.py
```

2. Set up KataGo using **one of these methods**:

### Method 1: Use Homebrew KataGo (Recommended for macOS)

If you have Homebrew, install KataGo:
```bash
brew install katago
```

Then in the application:
1. Go to **Settings > Auto Setup KataGo**
2. The tool will automatically detect your brew installation
3. Click "Yes" to generate configuration
4. Done! (No downloads needed - uses brew's KataGo and neural networks)

### Method 2: Automatic Download

1. Go to **Settings > Auto Setup KataGo**
2. Click "Yes" to confirm the download (~100-200 MB)
3. Wait for the automatic download and configuration
4. Done! You're ready to analyze games

### Method 3: Manual Setup

See the detailed manual setup instructions below.

## KataGo Setup

### Automatic Setup (Recommended)

The easiest way to get started:

**If you have KataGo installed via Homebrew or system package manager:**
1. Launch the application: `python main.py`
2. Click **Settings > Auto Setup KataGo**
3. The tool will automatically detect your system KataGo installation
4. It will use the pre-installed neural networks (no download needed!)
5. A configuration file will be generated instantly

**If you don't have KataGo installed:**
1. Launch the application: `python main.py`
2. Click **Settings > Auto Setup KataGo**
3. Confirm the download (approximately 100-200 MB)
4. The tool will:
   - Download KataGo for your platform (macOS/Linux/Windows)
   - Download a neural network (b18c384nbt - 18-block network)
   - Generate an optimized configuration file
   - Save everything to `./katago_data/`

Once complete, you can immediately start using the analysis features!

**Supported Installation Methods:**
- Homebrew (macOS): `brew install katago` ✓ Auto-detected
- System package managers (Linux) ✓ Auto-detected
- Manual download ✓ Supported

### Manual Setup (Advanced)

If you prefer to manually configure KataGo or the automatic setup doesn't work:

#### 1. Download KataGo

Visit the [KataGo releases page](https://github.com/lightvector/KataGo/releases) and download the appropriate version for your operating system:

- **macOS**: `katago-vX.X.X-macos-*.tar.gz`
- **Linux**: `katago-vX.X.X-linux-*.tar.gz`
- **Windows**: `katago-vX.X.X-windows-*.zip`

Extract the archive to a location of your choice.

### 2. Download a Neural Network

KataGo requires a neural network file. Download from the [KataGo networks](https://github.com/lightvector/KataGo/releases) section:

- **Recommended for most users**: `b18c384nbt` (18-block network, good balance)
- **For stronger play**: `b40c256` (40-block network, slower but stronger)
- **For faster analysis**: `b10c128` (10-block network, faster but weaker)

Download a `.bin.gz` file and extract it.

### 3. Generate KataGo Configuration

Open a terminal and navigate to the KataGo directory, then run:

```bash
./katago genconfig auto -model /path/to/your/network.bin.gz -output katago_config.cfg
```

This will create a `katago_config.cfg` file optimized for your system.

#### Optional: Adjust Configuration

Edit `katago_config.cfg` to customize settings:

- **numSearchThreads**: Number of CPU threads (default: auto)
- **maxVisits**: Maximum analysis visits (higher = slower but more accurate)
- **nnMaxBatchSize**: Batch size for GPU (if using GPU)

### 4. Configure in the Application

1. Run the Go Analysis Tool:
```bash
python main.py
```

2. Go to **Settings > Configure KataGo**

3. Set the following paths:
   - **KataGo Executable**: Path to the `katago` binary
   - **Config File**: Path to your `katago_config.cfg`
   - **Model File**: Path to your neural network `.bin.gz` file

4. Click **Save**

The application will automatically start KataGo and verify the connection.

## Usage

### Starting the Application

```bash
python main.py
```

### Playing a Game

1. Click **File > New Game** to start a new game
2. Select board size (9, 13, or 19)
3. Click on the board to place stones
4. Click **Pass** to pass a turn
5. Save your game with **File > Save SGF**

### Loading a Game

1. Click **File > Open SGF**
2. Select an SGF file
3. Use the navigation buttons to move through the game:
   - **|<**: Jump to start
   - **<**: Previous move
   - **>**: Next move
   - **>|**: Jump to end

### Analyzing a Game

1. Load or play a game
2. Switch to **Analysis** mode
3. Click **Analyze Game** to analyze all moves
   - The tool will show a progress bar
   - Errors will be highlighted on the board
   - Error list will show moves with significant point loss
4. Click on an error in the list to jump to that position
5. Use **Analyze Position** to analyze a specific position

### Understanding Analysis Results

#### Top 5 Moves Panel
Shows the best moves for the current position:
- **Move**: Board position (e.g., D4)
- **WR**: Win rate percentage
- **Score**: Estimated score lead
- **>>>**: Indicates the move that was actually played

#### Error Detection
Moves are flagged as errors when they lose more than the configured threshold (default: 3 points). Errors appear:
- As red X marks on the board
- In the error list with move number and point loss

### Customizing Error Threshold and Analysis Settings

Edit `config.json` (created after first run):

```json
{
  "katago": {
    "max_visits": 200,
    "analysis_timeout": 120
  },
  "analysis": {
    "error_threshold": 3.0,
    "analysis_threads": 3
  }
}
```

**Configuration Options:**
- `error_threshold`: Point loss to flag as error (default: 3.0)
  - Lower values = more sensitive error detection
- `analysis_threads`: Number of parallel analysis threads (default: 3, max: 8)
  - Higher values = faster analysis (recommended: 2-4)
  - Each thread runs a separate KataGo instance
  - **Performance:** 3 threads ≈ 3x faster analysis!
- `analysis_timeout`: Timeout in seconds for each position analysis (default: 120)
  - Increase if you get timeout warnings during analysis
  - Higher values allow KataGo more time to think
  - Recommended: 120-300 seconds for thorough analysis

## Project Structure

```
go_analysis_tool/
├── main.py                 # Application entry point
├── config.json             # Configuration file (auto-generated)
├── katago_data/            # KataGo installation (auto-generated)
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── game/                  # Game logic
│   ├── board.py           # Board state
│   ├── rules.py           # Go rules engine
│   └── game_tree.py       # Move history and variations
├── sgf/                   # SGF file support
│   ├── parser.py          # SGF reader
│   └── writer.py          # SGF writer
├── katago/               # KataGo integration
│   ├── engine.py         # GTP communication
│   └── analysis.py       # Move analysis
├── ui/                   # User interface
│   ├── main_window.py    # Main application window
│   ├── board_canvas.py   # Board rendering
│   ├── control_panel.py  # Game controls
│   └── analysis_panel.py # Analysis display
└── utils/                # Utilities
    ├── config.py         # Configuration management
    └── katago_setup.py   # Automated KataGo setup
```

## Keyboard Shortcuts

- **Ctrl+N**: New game
- **Ctrl+O**: Open SGF
- **Ctrl+S**: Save SGF
- **Left Arrow**: Previous move
- **Right Arrow**: Next move
- **Home**: Jump to start
- **End**: Jump to end

## Troubleshooting

### KataGo Won't Start

**For macOS users with Homebrew:**
```bash
brew install katago
```
Then go to **Settings > Auto Setup KataGo** in the application.

**Try Automatic Setup First:**
1. Go to **Settings > Auto Setup KataGo**
2. This will download and configure everything automatically

**If automatic setup fails:**
1. Verify paths in Settings > Configure KataGo
2. Check that KataGo executable has execute permissions:
   ```bash
   chmod +x /path/to/katago
   ```
3. Test KataGo manually:
   ```bash
   ./katago gtp -config katago_config.cfg -model network.bin.gz
   ```
4. Check firewall/antivirus isn't blocking downloads

### Automatic Setup Download Failed

If automatic download doesn't work:
1. Check your internet connection
2. Verify you have write permissions to the current directory
3. Try manual setup (see Manual Setup section above)
4. Check if you're behind a proxy or firewall

### Analysis Takes Too Long

Reduce the number of visits in `config.json`:

```json
{
  "katago": {
    "max_visits": 100
  }
}
```

Lower values = faster but less accurate analysis.

### Getting Timeout Warnings During Analysis

If you see "Warning: Timeout waiting for KataGo analysis response", increase the timeout:

```json
{
  "katago": {
    "analysis_timeout": 180
  }
}
```

**Common causes:**
- High `max_visits` value (200+) requires more time
- Slower hardware (CPU vs GPU)
- Complex board positions with many variations

**Solutions:**
- Increase `analysis_timeout` to 180-300 seconds
- Or reduce `max_visits` to 100-150 for faster analysis
- GPU acceleration (if available) significantly speeds up analysis

### SGF File Won't Load

- Ensure the file is valid SGF format
- Check for special characters or encoding issues
- Try opening in another SGF viewer to verify

## Tips for Game Analysis

1. **Start with full game analysis** to get an overview of mistakes
2. **Click through errors** in the error list to review each one
3. **Compare top moves** to understand what you should have played
4. **Use position analysis** to explore alternative moves in detail
5. **Adjust error threshold** based on your skill level:
   - Beginners: 5-10 points
   - Intermediate: 3-5 points
   - Advanced: 1-3 points

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- [KataGo](https://github.com/lightvector/KataGo) by David J Wu - the amazing Go AI engine
- SGF format specification from [Red Bean](https://www.red-bean.com/sgf/)

## Support

For issues, questions, or suggestions, please open an issue on the project repository.
