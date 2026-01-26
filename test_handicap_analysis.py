#!/usr/bin/env python3
"""Test script to analyze the handicap game and debug the issue."""

from sgf.parser import SGFParser
from katago.engine import KataGoEngine
from katago.analysis import GameAnalyzer
from utils.config import Config

def main():
    # Load the problem SGF file
    sgf_path = "/Users/calvino/Downloads/game_2257_Nai_Starling_vs_Princess_Joy_2026-01-23.sgf"
    print(f"Loading SGF: {sgf_path}")

    game_tree = SGFParser.parse_file(sgf_path)
    print(f"Board size: {game_tree.board_size}")
    print(f"Komi: {game_tree.get_komi()}")

    # Get main line
    main_line = game_tree.get_main_line()
    total_moves = sum(1 for n in main_line if n.move is not None or n.is_pass)
    print(f"Total moves: {total_moves}")

    # Initialize KataGo
    config = Config()
    if not config.is_katago_configured():
        print("ERROR: KataGo is not configured")
        return

    print("\nInitializing KataGo...")
    engine = KataGoEngine(
        config.get_katago_executable(),
        config.get_katago_config(),
        config.get_katago_model(),
        config.get_analysis_timeout()
    )

    if not engine.start():
        print("ERROR: Failed to start KataGo")
        return

    print("KataGo started successfully")

    # Create analyzer
    analyzer = GameAnalyzer(engine, config.get_error_threshold(), 1)

    # Run analysis
    print(f"\nStarting analysis (max_visits={config.get_max_visits()})...\n")

    try:
        results = analyzer.analyze_game(
            game_tree,
            config.get_max_visits(),
            progress_callback=lambda current, total: print(f"Progress: {current}/{total}"),
            katago_path=config.get_katago_executable(),
            config_path=config.get_katago_config(),
            model_path=config.get_katago_model(),
            analysis_timeout=config.get_analysis_timeout()
        )

        print(f"\n\nAnalysis complete! Analyzed {len(results)} positions.")

        # Show errors
        errors = [(a.move_number, a.played_move, a.point_loss) for a in results if a.is_error]
        print(f"Found {len(errors)} errors:")
        for move_num, pos, loss in errors:
            print(f"  Move {move_num}: {pos}, loss = {loss:.1f} points")

    except Exception as e:
        import traceback
        print(f"\nERROR during analysis: {e}")
        traceback.print_exc()
    finally:
        engine.stop()

if __name__ == "__main__":
    main()
