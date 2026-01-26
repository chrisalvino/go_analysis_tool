#!/usr/bin/env python3
"""Test analyzing specifically node 239 (S16, move 238)."""

from sgf.parser import SGFParser
from katago.engine import KataGoEngine
from utils.config import Config

def main():
    sgf_path = "/Users/calvino/Downloads/game_2257_Nai_Starling_vs_Princess_Joy_2026-01-23.sgf"
    game_tree = SGFParser.parse_file(sgf_path)
    main_line = game_tree.get_main_line()
    board_size = 19
    komi = game_tree.get_komi()

    # Extract handicap stones
    initial_stones = []
    if main_line[1].properties and 'AB' in main_line[1].properties:
        for stone_pos in main_line[1].properties['AB']:
            row = ord(stone_pos[1]) - ord('a')
            col = ord(stone_pos[0]) - ord('a')
            gtp_move = KataGoEngine.coords_to_gtp(row, col, board_size)
            initial_stones.append(["B", gtp_move])

    print(f"Handicap stones: {initial_stones}\n")

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

    # Simulate what happens when analyzing node 239
    i = 239  # Node index
    move_index = i

    # Build moves up to (but not including) this node
    moves_gtp = []
    for j in range(i):
        prev_node = main_line[j]
        if prev_node.is_pass:
            moves_gtp.append('pass')
        elif prev_node.move:
            gtp_move = KataGoEngine.coords_to_gtp(prev_node.move[0], prev_node.move[1], board_size)
            moves_gtp.append(gtp_move)

    print(f"Analyzing position before node {i} (move {main_line[i].get_move_number()}):")
    print(f"  Total moves before this: {len(moves_gtp)}")
    print(f"  Last 10 moves: {moves_gtp[-10:]}\n")

    # Get top 5 moves at this position
    print("Getting top 5 moves...")
    analysis_data = engine.analyze_position(
        moves=moves_gtp,
        board_size=board_size,
        komi=komi,
        initial_player='B',
        max_visits=100,
        initial_stones=initial_stones
    )

    if analysis_data and 'moveInfos' in analysis_data:
        print(f"Got {len(analysis_data['moveInfos'])} candidates")
        for idx, move_info in enumerate(analysis_data['moveInfos'][:5]):
            print(f"  {idx+1}. {move_info.get('move')} - score: {move_info.get('scoreLead', 0):.1f}")

        # Check if S16 is in candidates
        node_239 = main_line[239]
        gtp_239 = KataGoEngine.coords_to_gtp(node_239.move[0], node_239.move[1], board_size)
        print(f"\nActual played move at node 239: {gtp_239} at {node_239.move}")

        s16_in_top5 = any(m.get('move', '').upper() == gtp_239.upper()
                          for m in analysis_data['moveInfos'][:5])

        if not s16_in_top5:
            print("  ✗ S16 NOT in top 5 - will need secondary analysis")

            # Now try to analyze WITH S16 played (this is where the error occurs)
            print(f"\nNow analyzing WITH S16 included...")
            moves_with_played = []
            for j in range(move_index):  # 0 to 238
                prev_node = main_line[j]
                if prev_node.is_pass:
                    moves_with_played.append('pass')
                elif prev_node.move:
                    gtp_move = KataGoEngine.coords_to_gtp(prev_node.move[0], prev_node.move[1], board_size)
                    moves_with_played.append(gtp_move)

            # Add S16
            moves_with_played.append(gtp_239)

            print(f"Total moves: {len(moves_with_played)}")
            print(f"Last 10 moves: {moves_with_played[-10:]}")
            print(f"Move at index 237 (0-based): {moves_with_played[237] if len(moves_with_played) > 237 else 'N/A'}")

            try:
                result = engine.analyze_position(
                    moves=moves_with_played,
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
            print("  ✓ S16 IS in top 5")
    else:
        print("ERROR: No analysis data")

    engine.stop()

if __name__ == "__main__":
    main()
