#!/usr/bin/env python3
"""Quick test to analyze just move 238."""

from sgf.parser import SGFParser
from katago.engine import KataGoEngine
from katago.analysis import GameAnalyzer
from utils.config import Config

def main():
    # Load the problem SGF file
    sgf_path = "/Users/calvino/Downloads/game_2257_Nai_Starling_vs_Princess_Joy_2026-01-23.sgf"
    print(f"Loading SGF: {sgf_path}\n")

    game_tree = SGFParser.parse_file(sgf_path)

    # Get main line
    main_line = game_tree.get_main_line()

    # Initialize KataGo
    config = Config()
    engine = KataGoEngine(
        config.get_katago_executable(),
        config.get_katago_config(),
        config.get_katago_model(),
        config.get_analysis_timeout()
    )

    if not engine.start():
        print("ERROR: Failed to start KataGo")
        return

    print("KataGo started\n")

    # Build move list up to move 237 (to analyze position before move 238)
    board_size = game_tree.board_size
    komi = game_tree.get_komi()

    # Extract handicap stones
    initial_stones = []
    root_props = None
    if main_line and len(main_line) > 0 and main_line[0].properties:
        root_props = main_line[0].properties

    if not root_props or ('AB' not in root_props and 'AW' not in root_props):
        if len(main_line) > 1 and main_line[1].properties:
            root_props = main_line[1].properties

    if root_props and 'AB' in root_props:
        ab_values = root_props['AB']
        if isinstance(ab_values, list):
            for stone_pos in ab_values:
                if stone_pos and len(stone_pos) == 2:
                    row = ord(stone_pos[1]) - ord('a')
                    col = ord(stone_pos[0]) - ord('a')
                    gtp_move = KataGoEngine.coords_to_gtp(row, col, board_size)
                    initial_stones.append(["B", gtp_move])

    print(f"Handicap stones: {initial_stones}\n")

    # Build moves up to move 237
    moves_gtp = []
    for i in range(238):  # 0-237 (moves before move 238)
        node = main_line[i]
        if node.is_pass:
            moves_gtp.append('pass')
        elif node.move:
            gtp_move = KataGoEngine.coords_to_gtp(node.move[0], node.move[1], board_size)
            moves_gtp.append(gtp_move)

    print(f"Total moves before 238: {len(moves_gtp)}")
    print(f"Last 10 moves: {moves_gtp[-10:]}\n")

    # Now analyze the position (this should give us top 5 moves at position 237)
    print("Analyzing position before move 238...")
    analysis_data = engine.analyze_position(
        moves=moves_gtp,
        board_size=board_size,
        komi=komi,
        initial_player='B',
        max_visits=100,
        initial_stones=initial_stones
    )

    if analysis_data and 'moveInfos' in analysis_data:
        print(f"\nGot {len(analysis_data['moveInfos'])} candidate moves")
        for i, move_info in enumerate(analysis_data['moveInfos'][:10]):
            print(f"  {i+1}. {move_info.get('move')} - score: {move_info.get('scoreLead', 0):.1f}")

        # Check if S16 is in the candidates
        move_238_node = main_line[238]
        gtp_238 = KataGoEngine.coords_to_gtp(move_238_node.move[0], move_238_node.move[1], board_size)
        print(f"\nActual move 238: {gtp_238} at {move_238_node.move}")

        s16_found = False
        for move_info in analysis_data['moveInfos']:
            if move_info.get('move', '').upper() == gtp_238.upper():
                print(f"  ✓ Move IS in candidates (score: {move_info.get('scoreLead', 0):.1f})")
                s16_found = True
                break

        if not s16_found:
            print(f"  ✗ Move NOT in top candidates - will need secondary analysis")

            # Try to analyze WITH the move played (simulating what the code does)
            print(f"\nNow analyzing WITH move 238 included...")
            moves_with_238 = moves_gtp + [gtp_238]

            print(f"Total moves: {len(moves_with_238)}")
            print(f"Last 10 moves: {moves_with_238[-10:]}")
            print(f"Handicap stones: {initial_stones}")

            # Check for duplicates
            from collections import Counter
            move_counts = Counter(moves_with_238)
            duplicates = {move: count for move, count in move_counts.items() if count > 1}
            if duplicates:
                print(f"DUPLICATES FOUND: {duplicates}")
            else:
                print("No duplicates found in move sequence")

            # Try the analysis
            try:
                result = engine.analyze_position(
                    moves=moves_with_238,
                    board_size=board_size,
                    komi=komi,
                    initial_player='B',
                    max_visits=100,
                    initial_stones=initial_stones
                )
                if result:
                    print("✓ Secondary analysis succeeded!")
                else:
                    print("✗ Secondary analysis returned None")
            except Exception as e:
                print(f"✗ Secondary analysis failed: {e}")
    else:
        print("ERROR: No analysis data returned")

    engine.stop()

if __name__ == "__main__":
    main()
