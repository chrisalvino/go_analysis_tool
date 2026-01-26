#!/usr/bin/env python3
"""Quick S16 test."""
from sgf.parser import SGFParser
from katago.engine import KataGoEngine
from utils.config import Config

sgf = SGFParser.parse_file("/Users/calvino/Downloads/game_2257_Nai_Starling_vs_Princess_Joy_2026-01-23.sgf")
main_line = sgf.get_main_line()

# Get handicap
initial_stones = []
for stone_pos in main_line[1].properties['AB']:
    row, col = ord(stone_pos[1]) - ord('a'), ord(stone_pos[0]) - ord('a')
    initial_stones.append(["B", KataGoEngine.coords_to_gtp(row, col, 19)])

# Build moves up to and including S16 (node 239)
moves_gtp = []
for j in range(239):
    node = main_line[j]
    if node.is_pass:
        moves_gtp.append('pass')
    elif node.move:
        moves_gtp.append(KataGoEngine.coords_to_gtp(node.move[0], node.move[1], 19))

# Add S16
moves_gtp.append('S16')

print(f"Testing with {len(moves_gtp)} moves, handicap: {initial_stones}")

# Determine initialPlayer - White plays first in Black handicap games
if initial_stones and all(stone[0] == 'B' for stone in initial_stones):
    initial_player = 'W'
else:
    initial_player = 'B'

print(f"initial_player: {initial_player}")

config = Config()
engine = KataGoEngine(config.get_katago_executable(), config.get_katago_config(),
                     config.get_katago_model(), 60)
engine.start()

result = engine.analyze_position(moves_gtp, 19, 6.5, initial_player, 100, initial_stones)
print(f"Result: {result is not None}")

engine.stop()
